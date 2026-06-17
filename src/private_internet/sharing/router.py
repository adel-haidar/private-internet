"""Sharing API — /api/share.

- POST   /api/share          (auth)   mint a share token for an owned item / card
- GET    /api/share          (auth)   list the caller's shares
- DELETE /api/share/{token}  (auth)   revoke a share
- GET    /api/share/{token}  PUBLIC   render the shared item (HTML by default,
                                      JSON when the client prefers application/json)

The public GET deliberately takes NO RequestContext dependency — it is the only
unauthenticated route in this module and reads solely the denormalised snapshot.
"""

import logging
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from private_internet.config import get_settings
from private_internet.core.request_context import RequestContext, get_request_context
from private_internet.sharing import db
from private_internet.sharing.page import render_share_html, render_unavailable_html
from private_internet.sharing.service import build_snapshot

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/share", tags=["sharing"])


class CreateShareRequest(BaseModel):
    kind: str
    ref_id: Optional[str] = None
    highlight: Optional[dict] = None


def _share_url(token: str) -> str:
    return f"{get_settings().base_url}/api/share/{token}"


@router.post("")
async def create_share(
    body: CreateShareRequest,
    ctx: RequestContext = Depends(get_request_context),
):
    """Mint a public share token for an item the caller owns (or a highlight card)."""
    token = secrets.token_urlsafe(16)
    snapshot = build_snapshot(ctx, body.kind, body.ref_id, body.highlight, token)
    db.create_share(
        token=token,
        user_id=ctx.user_id,
        kind=body.kind,
        ref_id=body.ref_id,
        snapshot=snapshot,
    )
    logger.info("%s shared %s (%s)", ctx.log_prefix, body.kind, token)
    return {"token": token, "share_url": _share_url(token), "snapshot": snapshot}


@router.get("")
async def list_my_shares(ctx: RequestContext = Depends(get_request_context)):
    rows = db.list_shares(ctx.user_id)
    return [
        {
            "token": r["token"],
            "kind": r["kind"],
            "ref_id": r["ref_id"],
            "revoked": r["revoked"],
            "view_count": r["view_count"],
            "share_url": _share_url(r["token"]),
            "title": (r.get("snapshot") or {}).get("title"),
            "created_at": r["created_at"],
        }
        for r in rows
    ]


@router.delete("/{token}")
async def revoke_share(
    token: str, ctx: RequestContext = Depends(get_request_context)
):
    if not db.revoke(token, ctx.user_id):
        raise HTTPException(status_code=404, detail="share not found")
    return {"revoked": True}


@router.get("/{token}")
async def view_share(token: str, request: Request):
    """PUBLIC. Renders the shared item — HTML for browsers/crawlers, JSON when the
    client explicitly prefers application/json. No authentication."""
    accept = request.headers.get("accept", "")
    wants_json = "application/json" in accept and "text/html" not in accept

    row = db.get_share(token)
    if row is None or row["revoked"]:
        if wants_json:
            raise HTTPException(status_code=410, detail="share unavailable")
        return HTMLResponse(render_unavailable_html(), status_code=410)

    snapshot = row["snapshot"] or {}
    db.increment_view(token)

    if wants_json:
        return JSONResponse({"snapshot": snapshot, "share_url": _share_url(token)})
    return HTMLResponse(render_share_html(snapshot, _share_url(token)))
