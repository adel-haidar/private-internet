"""Auth for the agents service (banking / health / jobs / trading / email).

These modules still operate on the OWNER's data (seed admin) — sourced from MCP
memory with the shared INTERNAL_SECRET. They are not per-user yet. So this
dependency:

  - accepts the INTERNAL_SECRET (cron timers, sibling services)         -> allow
  - accepts a platform JWT whose `is_admin` claim is true (the owner)   -> allow
  - accepts a legacy OAuth access token (claude.ai / old dashboard)     -> allow
  - accepts a platform JWT for a NON-admin user                         -> 401
  - anything else                                                       -> 401

The NON-admin case returns 401 (not 403) with a friendly detail so it tells the
dashboard "not available for your account yet" WITHOUT clearing the session, and
without exposing the owner's financial/health data to another tenant. We must use
401 (and NOT 403) because CloudFront is configured SPA-style to rewrite 403/404
responses into index.html — a 403 would reach the browser as HTML and break the
dashboard's JSON parsing, whereas 401 passes through as JSON untouched. The
frontend only refreshes/logs-out on 401 when a refresh token exists, so this
friendly 401 does not cause a logout. Making these modules truly multi-tenant is
a separate project.
"""

import base64
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone
from typing import Optional

import asyncpg
from fastapi import HTTPException, Request

from assistant.shared.settings import get_settings

_auth_pool: Optional[asyncpg.Pool] = None

_NOT_FOR_YOU = "This module isn’t available for your account yet."


async def _get_pool() -> asyncpg.Pool:
    global _auth_pool
    if _auth_pool is None:
        database_url = get_settings().database_url
        if not database_url:
            raise HTTPException(status_code=503, detail="Database not configured")
        _auth_pool = await asyncpg.create_pool(database_url, min_size=1, max_size=3)
    return _auth_pool


def _b64url_decode(seg: str) -> bytes:
    return base64.urlsafe_b64decode(seg + "=" * (-len(seg) % 4))


def _verify_jwt(token: str, secret: str) -> Optional[dict]:
    """Verify an HS256 platform JWT (stdlib only). Returns claims or None."""
    if not secret:
        return None
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
        header = json.loads(_b64url_decode(header_b64))
        if header.get("alg") != "HS256":
            return None  # reject alg-confusion / 'none'
        signing_input = f"{header_b64}.{payload_b64}".encode()
        expected = base64.urlsafe_b64encode(
            hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
        ).rstrip(b"=").decode()
        if not hmac.compare_digest(expected, sig_b64):
            return None
        claims = json.loads(_b64url_decode(payload_b64))
        exp = claims.get("exp")
        if exp is not None and time.time() > float(exp):
            return None
        return claims
    except Exception:
        return None


async def require_auth(request: Request) -> str:
    """Authenticate the caller and require owner/admin (see module docstring)."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing token")
    token = auth[7:]

    settings = get_settings()

    # 1. Same-host callers (cron timers, sibling agents).
    internal_secret = getattr(settings, "internal_secret", None) or os.getenv("INTERNAL_SECRET")
    if internal_secret and hmac.compare_digest(token, internal_secret):
        return "internal-service"

    # 2. Platform JWT (dashboard login). Only the owner (is_admin) may use the
    #    owner-scoped agent modules; other tenants get a clean 401 (NOT 403 —
    #    CloudFront rewrites 403/404 into the SPA index.html, which would reach
    #    the browser as HTML and break JSON parsing; 401 passes through as JSON).
    secret = getattr(settings, "secret_key", "") or os.getenv("SECRET_KEY", "")
    claims = _verify_jwt(token, secret)
    if claims is not None:
        if claims.get("is_admin"):
            return str(claims.get("sub") or "admin")
        raise HTTPException(status_code=401, detail=_NOT_FOR_YOU)

    # 3. Legacy OAuth access token -> seed admin (back-compat).
    pool = await _get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT client_id, expires_at FROM oauth_tokens"
            " WHERE token = $1 AND token_type = 'access'",
            token,
        )
    if row and datetime.now(timezone.utc) <= row["expires_at"]:
        return row["client_id"]

    raise HTTPException(status_code=401, detail="invalid or expired token")


async def require_user(request: Request) -> dict:
    """Authenticate ANY valid caller for the per-user (multi-tenant) modules.

    Unlike `require_auth` (which owner-gates), this allows non-admin platform
    users through — each caller's own bearer token is returned so it can be
    forwarded verbatim to Service A's per-user memory REST API, which resolves
    the token to the right tenant (platform JWT → that user; INTERNAL_SECRET /
    legacy OAuth → seed admin). Used by finance (banking) and job-hunt.

    Returns a dict:
      {"token": <raw bearer token to forward>,
       "user_id": <str | None>,   # platform user id, else None (admin paths)
       "is_admin": <bool>,
       "internal": <bool>}        # True only for the INTERNAL_SECRET path

    Raises 401 for missing/invalid tokens (never 403 — CloudFront rewrites
    403/404 to the SPA index.html and would break JSON parsing).
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing token")
    token = auth[7:]

    settings = get_settings()

    # 1. Same-host callers (cron timers, sibling agents) → forward the internal
    #    secret, which Service A resolves to the seed admin (unchanged behaviour).
    internal_secret = getattr(settings, "internal_secret", None) or os.getenv("INTERNAL_SECRET")
    if internal_secret and hmac.compare_digest(token, internal_secret):
        return {"token": token, "user_id": None, "is_admin": True, "internal": True}

    # 2. Platform JWT — ANY user (admin or not) is allowed; forward their JWT so
    #    Service A scopes memory to that tenant.
    secret = getattr(settings, "secret_key", "") or os.getenv("SECRET_KEY", "")
    claims = _verify_jwt(token, secret)
    if claims is not None:
        return {
            "token": token,
            "user_id": str(claims.get("sub")) if claims.get("sub") is not None else None,
            "is_admin": bool(claims.get("is_admin")),
            "internal": False,
        }

    # 3. Legacy OAuth access token → seed admin (back-compat).
    pool = await _get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT client_id, expires_at FROM oauth_tokens"
            " WHERE token = $1 AND token_type = 'access'",
            token,
        )
    if row and datetime.now(timezone.utc) <= row["expires_at"]:
        return {"token": token, "user_id": None, "is_admin": True, "internal": False}

    raise HTTPException(status_code=401, detail="invalid or expired token")
