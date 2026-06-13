"""Per-request user context for multi-tenant data isolation.

Every endpoint that reads or writes user data MUST take
`ctx: RequestContext = Depends(get_request_context)` and scope its queries
with `WHERE user_id = ctx.user_id`.  # MUST SCOPE BY USER

Auth resolves in this order:
- The shared INTERNAL_SECRET (X-Internal-Secret header, or sent as a bearer) →
  the seed admin. Used by same-host services (the agents). Stable — no OAuth
  token to expire/rotate/harvest.
- Platform JWTs (users/tokens.py) → the token's own user.
- Legacy OAuth 2.1 tokens (claude.ai MCP connector and pre-rebrand dashboard
  sessions) → the seed admin user. Per-user MCP access is a future feature.
"""

import hmac
import logging
import os
from dataclasses import dataclass

from fastapi import HTTPException, Request

from private_internet.auth.oauth import validate_token
from private_internet.users.service import get_seed_admin_id, get_user_by_id
from private_internet.users.tokens import decode_user_token

logger = logging.getLogger(__name__)


@dataclass
class RequestContext:
    user_id: str
    user_email: str
    is_admin: bool

    @property
    def log_prefix(self) -> str:
        return f"[user:{self.user_id[:8]}]"


def _bearer_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing token")
    return auth[7:]


def _seed_admin_context() -> RequestContext:
    admin_id = get_seed_admin_id()
    admin = get_user_by_id(admin_id)
    return RequestContext(
        user_id=admin_id,
        user_email=admin["email"] if admin else "",
        is_admin=True,
    )


def _is_internal_secret(request: Request) -> bool:
    """True if the request carries the shared INTERNAL_SECRET, via the
    X-Internal-Secret header or an `Authorization: Bearer <secret>`."""
    expected = os.getenv("INTERNAL_SECRET")
    if not expected:
        return False
    candidates = []
    header = request.headers.get("X-Internal-Secret")
    if header:
        candidates.append(header)
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        candidates.append(auth[7:])
    return any(hmac.compare_digest(c, expected) for c in candidates)


async def get_request_context(request: Request) -> RequestContext:
    # Same-host services authenticate with the shared INTERNAL_SECRET → seed admin.
    if _is_internal_secret(request):
        return _seed_admin_context()

    token = _bearer_token(request)

    # Platform JWT
    claims = decode_user_token(token)
    if claims is not None:
        return RequestContext(
            user_id=str(claims["sub"]),
            user_email=claims.get("email", ""),
            is_admin=bool(claims.get("is_admin")),
        )

    # Legacy OAuth token → seed admin
    client_id = validate_token(token)
    if client_id:
        return _seed_admin_context()

    raise HTTPException(status_code=401, detail="invalid token")


async def get_admin_context(request: Request) -> RequestContext:
    """Like get_request_context, but rejects non-admin users."""
    ctx = await get_request_context(request)
    if not ctx.is_admin:
        raise HTTPException(status_code=403, detail="admin access required")
    return ctx
