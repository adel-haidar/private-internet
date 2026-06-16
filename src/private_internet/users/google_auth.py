"""Google sign-in (OAuth 2.0 authorization-code flow) for the dashboard.

This is a SOCIAL identity provider login that issues a platform JWT, mirroring
the email/password login (users/routes.py). It is entirely separate from the
app's own OAuth 2.1/PKCE server in auth/ (which claude.ai MCP depends on).

Inert until GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are set, so deploying
without credentials changes nothing. The browser flow:

  /api/auth/google/login  → 302 to Google consent (state in an httponly cookie)
  Google → /api/auth/google/callback?code&state
        → exchange code for an id_token (TLS + client_secret authenticate it)
        → find-or-create the user by verified email, issue a platform JWT
        → 302 to the SPA at /google-callback#token=<jwt> (fragment, never logged)
"""

import base64
import json
import logging
import secrets
import urllib.parse
import urllib.request

from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import RedirectResponse

from private_internet.config import get_settings
from private_internet.users.provisioning import provision_user
from private_internet.users.service import (
    count_users,
    create_user,
    get_user_by_email,
    update_user,
)
from private_internet.users.tokens import create_user_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth/google", tags=["auth"])

_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_STATE_COOKIE = "pi_g_state"


def _redirect_uri(settings) -> str:
    return f"{settings.base_url}/api/auth/google/callback"


def _login_error(settings, reason: str) -> RedirectResponse:
    return RedirectResponse(f"{settings.base_url}/login?error={reason}", status_code=302)


def _decode_id_token(id_token: str) -> dict:
    """Decode the id_token JWT payload. The token came directly from Google's
    token endpoint over TLS authenticated with our client_secret, so the payload
    is trustworthy without re-verifying the signature."""
    payload_b64 = id_token.split(".")[1]
    payload_b64 += "=" * (-len(payload_b64) % 4)  # restore base64 padding
    return json.loads(base64.urlsafe_b64decode(payload_b64))


@router.get("/login")
async def google_login():
    s = get_settings()
    if not (s.google_client_id and s.google_client_secret):
        return _login_error(s, "google_not_configured")
    state = secrets.token_urlsafe(24)
    query = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": s.google_client_id,
        "redirect_uri": _redirect_uri(s),
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    })
    resp = RedirectResponse(f"{_AUTHORIZE_URL}?{query}", status_code=302)
    resp.set_cookie(
        _STATE_COOKIE, state, max_age=600,
        httponly=True, secure=True, samesite="lax",
    )
    return resp


@router.get("/callback")
async def google_callback(
    request: Request,
    background: BackgroundTasks,
    code: str = "",
    state: str = "",
    error: str = "",
):
    s = get_settings()
    if error or not code:
        return _login_error(s, "google_failed")
    if not state or state != request.cookies.get(_STATE_COOKIE):
        logger.warning("Google callback state mismatch — possible CSRF")
        return _login_error(s, "google_failed")
    if not (s.google_client_id and s.google_client_secret):
        return _login_error(s, "google_not_configured")

    try:
        body = urllib.parse.urlencode({
            "code": code,
            "client_id": s.google_client_id,
            "client_secret": s.google_client_secret,
            "redirect_uri": _redirect_uri(s),
            "grant_type": "authorization_code",
        }).encode()
        req = urllib.request.Request(
            _TOKEN_URL, data=body, method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            token_resp = json.loads(r.read())
        claims = _decode_id_token(token_resp["id_token"])
    except Exception as exc:  # noqa: BLE001 - any failure → graceful login error
        logger.warning("Google token exchange failed: %s", exc)
        return _login_error(s, "google_failed")

    email = (claims.get("email") or "").strip().lower()
    if not email or not claims.get("email_verified"):
        logger.warning("Google login rejected: missing or unverified email")
        return _login_error(s, "google_failed")

    user = get_user_by_email(email)
    if user is None:
        # New account via Google — apply the same registration gating as /register.
        if not s.registration_open:
            return _login_error(s, "registration_closed")
        if s.max_users and count_users() >= s.max_users:
            return _login_error(s, "registration_closed")
        display_name = claims.get("name") or email.split("@")[0]
        ip = request.client.host if request.client else None
        user = create_user(
            email=email, display_name=display_name,
            password_hash=None, registration_ip=ip,
        )
        update_user(user["id"], email_verified=True)
        background.add_task(provision_user, dict(user))
        logger.info("[user:%s] created via Google sign-in: %s", user["id"][:8], email)
    else:
        logger.info("[user:%s] logged in via Google", user["id"][:8])

    token = create_user_token(user)
    resp = RedirectResponse(f"{s.base_url}/google-callback#token={token}", status_code=302)
    resp.delete_cookie(_STATE_COOKIE)
    return resp
