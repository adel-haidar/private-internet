"""Email/password user authentication for the multi-tenant platform.

Adjacent to — and deliberately independent of — the OAuth 2.1 server in
``auth/``. Issues platform JWTs (``users/tokens.py``) that ``RequestContext``
resolves to the calling user. Error responses use ``{"error": <message>}`` with
clear, human messages (never a generic "invalid credentials").
"""

import logging
import re

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from private_internet.config import get_settings
from private_internet.core.request_context import RequestContext, get_request_context
from private_internet.memory.service import save_memory
from private_internet.users.passwords import (
    MIN_PASSWORD_LENGTH,
    hash_password,
    verify_password,
)
from private_internet.users.service import (
    count_users,
    create_user,
    get_user_by_email,
    touch_last_active,
    update_user,
)
from private_internet.users.tokens import create_user_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _error(status: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": message})


class RegisterRequest(BaseModel):
    email: str
    display_name: str
    password: str
    referral_source: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class OnboardingRequest(BaseModel):
    onboarding_step: int | None = None
    onboarding_completed: bool | None = None


def _write_welcome_memory(user_id: str, display_name: str, email: str, referral: str | None) -> None:
    """Seed the new user's brain with a first memory. Non-fatal: a Bedrock
    embedding hiccup must never block registration."""
    content = f"User registered. Display name: {display_name}. Email: {email}."
    if referral:
        content += f"\nHow they heard about Private Internet: {referral}"
    try:
        save_memory(
            title="Account created",
            content=content,
            tags=["introduction", "onboarding", "profile"],
            user_id=user_id,
        )
    except Exception as e:  # pragma: no cover - external embedding call
        logger.warning(f"[user:{user_id[:8]}] welcome memory not saved: {e}")


@router.post("/register", status_code=201)
async def register(body: RegisterRequest):
    settings = get_settings()

    if not settings.registration_open:
        return _error(403, "Registration is invite-only. Contact the administrator for an account.")
    if settings.max_users and count_users() >= settings.max_users:
        return _error(403, "User limit reached. Contact the administrator for an account.")

    email = body.email.strip().lower()
    display_name = body.display_name.strip()
    if not _EMAIL_RE.match(email):
        return _error(422, "Please enter a valid email address.")
    if not display_name:
        return _error(422, "Display name is required.")
    if len(body.password) < MIN_PASSWORD_LENGTH:
        return _error(422, f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")

    if get_user_by_email(email) is not None:
        return _error(409, "An account with this email already exists.")

    user = create_user(
        email=email,
        display_name=display_name,
        password_hash=hash_password(body.password),
    )
    _write_welcome_memory(user["id"], display_name, email, (body.referral_source or "").strip() or None)

    logger.info(f"[user:{user['id'][:8]}] registered: {email}")
    return {"token": create_user_token(user), "user": user}


@router.post("/login")
async def login(body: LoginRequest):
    email = body.email.strip().lower()
    user = get_user_by_email(email, include_password_hash=True)
    if user is None:
        return _error(404, "No account found with this email.")
    if not verify_password(body.password, user.get("password_hash")):
        return _error(401, "Incorrect password.")

    user.pop("password_hash", None)  # never leaves this layer
    touch_last_active(user["id"])
    logger.info(f"[user:{user['id'][:8]}] logged in")
    return {"token": create_user_token(user), "user": user}


@router.get("/me")
async def me(ctx: RequestContext = Depends(get_request_context)):
    from private_internet.users.service import get_user_by_id

    user = get_user_by_id(ctx.user_id)
    if user is None:
        return _error(404, "User not found.")
    return {"user": user}


@router.patch("/onboarding")
async def update_onboarding(
    body: OnboardingRequest,
    ctx: RequestContext = Depends(get_request_context),
):
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if not fields:
        return _error(422, "Nothing to update.")
    user = update_user(ctx.user_id, **fields)
    if user is None:
        return _error(404, "User not found.")
    return {"user": user}
