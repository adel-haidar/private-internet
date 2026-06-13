import hmac
import os
from datetime import datetime, timezone
from typing import Optional

import asyncpg
from fastapi import HTTPException, Request

from assistant.shared.settings import get_settings

_auth_pool: Optional[asyncpg.Pool] = None


async def _get_pool() -> asyncpg.Pool:
    global _auth_pool
    if _auth_pool is None:
        database_url = get_settings().database_url
        if not database_url:
            raise HTTPException(status_code=503, detail="Database not configured")
        _auth_pool = await asyncpg.create_pool(database_url, min_size=1, max_size=3)
    return _auth_pool


async def require_auth(request: Request) -> str:
    """FastAPI dependency — validates Bearer token against the oauth_tokens table."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing token")
    token = auth[7:]

    # Same-host callers (cron timers, sibling agents) authenticate with the
    # stable INTERNAL_SECRET instead of an expiring OAuth access token.
    internal_secret = getattr(get_settings(), "internal_secret", None) or os.getenv("INTERNAL_SECRET")
    if internal_secret and hmac.compare_digest(token, internal_secret):
        return "internal-service"

    pool = await _get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT client_id, expires_at FROM oauth_tokens"
            " WHERE token = $1 AND token_type = 'access'",
            token,
        )

    if not row or datetime.now(timezone.utc) > row["expires_at"]:
        raise HTTPException(status_code=401, detail="invalid or expired token")

    return row["client_id"]
