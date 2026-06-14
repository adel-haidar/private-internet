import logging
from typing import Optional

import boto3
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel

from assistant.job import agent as job_agent
from assistant.job.db import init_pool, list_matches, list_unknown_companies, set_status, update_company
from assistant.job.models import RunReport
from assistant.job.report import format_report
from assistant.shared.auth import require_user
from assistant.shared.settings import Settings, get_settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["jobs"])

# Last run report per user (in-memory). Internal/legacy callers key off the seed admin.
_latest_reports: dict[str, RunReport] = {}
_seed_admin_id: Optional[str] = None


class StatusUpdate(BaseModel):
    status: str


async def _resolve_user_id(ident: dict, pool) -> str:
    """The caller's user_id, or the seed admin for internal/legacy callers.
    # MUST SCOPE BY USER"""
    if ident.get("user_id"):
        return ident["user_id"]
    global _seed_admin_id
    if _seed_admin_id is None:
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT id FROM users WHERE is_admin = true LIMIT 1")
        if not row:
            raise HTTPException(503, "No admin user to attribute internal job data to")
        _seed_admin_id = str(row["id"])
    return _seed_admin_id


@router.get("/run")
async def trigger_run(
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
    ident: dict = Depends(require_user),
):
    # Per-user: matches scrape into the caller's own pool (scoped by user_id).
    # Search criteria are still the shared defaults — per-user criteria is a follow-up.
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    pool = await init_pool(settings.database_url)
    user_id = await _resolve_user_id(ident, pool)
    background_tasks.add_task(_run_job_agent, settings, user_id, ident["token"])
    return {
        "status": "started",
        "message": "Job hunt agent running in background. Poll GET /api/jobs/report for results.",
    }


@router.get("/matches")
async def get_matches(
    tier: Optional[str] = Query(None, description="STRONG_MATCH | GOOD_MATCH"),
    country: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    settings: Settings = Depends(get_settings),
    ident: dict = Depends(require_user),
):
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    pool = await init_pool(settings.database_url)
    user_id = await _resolve_user_id(ident, pool)
    matches = await list_matches(pool, tier=tier, country=country, status=status, user_id=user_id)
    return {"count": len(matches), "matches": matches}


@router.post("/matches/{match_id}/status")
async def update_status(
    match_id: int,
    body: StatusUpdate,
    settings: Settings = Depends(get_settings),
    ident: dict = Depends(require_user),
):
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    pool = await init_pool(settings.database_url)
    user_id = await _resolve_user_id(ident, pool)
    ok = await set_status(pool, match_id, body.status, user_id=user_id)
    if not ok:
        raise HTTPException(
            400,
            f"Invalid status '{body.status}' or match #{match_id} not found. "
            "Valid: new | reviewing | applied | interviewing | rejected | withdrawn | expired",
        )
    return {"id": match_id, "status": body.status}


@router.get("/fix-companies")
async def fix_companies(settings: Settings = Depends(get_settings), ident: dict = Depends(require_user)):
    """One-time migration: re-fetch company names for rows with 'Explore companies' or 'Unknown'."""
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    pool = await init_pool(settings.database_url)
    user_id = await _resolve_user_id(ident, pool)
    rows = await list_unknown_companies(pool, user_id=user_id)
    if not rows:
        return {"message": "No rows to fix", "updated": 0}

    from assistant.job.scrapers.jobs_ch import extract_company_from_url

    updated = 0
    skipped = 0
    for row in rows:
        url: str = row["job_url"]
        platform: str = row["platform"]
        if platform != "jobs.ch":
            skipped += 1
            continue
        company = await extract_company_from_url(url)
        if company:
            ok = await update_company(pool, url, company, user_id=user_id)
            if ok:
                updated += 1
                logger.info("fix-companies: updated %s → %r", url, company)
        else:
            logger.warning("fix-companies: could not extract company for %s", url)

    return {
        "message": f"Updated {updated} rows ({skipped} non-jobs.ch skipped)",
        "updated": updated,
        "skipped": skipped,
    }


@router.get("/report")
async def get_report(settings: Settings = Depends(get_settings), ident: dict = Depends(require_user)):
    pool = await init_pool(settings.database_url) if settings.database_url else None
    user_id = await _resolve_user_id(ident, pool) if pool else (ident.get("user_id") or "")
    report = _latest_reports.get(user_id)
    if report is None:
        raise HTTPException(
            404, "No completed run yet — call GET /api/jobs/run to start one."
        )
    return {"report": format_report(report), "data": report}


async def _run_job_agent(settings: Settings, user_id: str, token: Optional[str] = None) -> None:
    bedrock_client = boto3.client("bedrock-runtime", region_name=settings.aws_region)
    memory_client = None
    graph_client = None

    if settings.mcp_memory_url:
        from assistant.shared.memory_client import MemoryClient

        # Forward the caller's bearer token so the run summary is saved to that
        # user's own brain. Internal/timer callers forward the INTERNAL_SECRET
        # (→ seed admin); fall back to it if no token was supplied.
        memory_client = MemoryClient(
            bedrock_client=bedrock_client,
            model_id=settings.bedrock_model_id,
            server_url=settings.mcp_memory_url,
            token=token or _get_mcp_token(settings),
        )

    try:
        from assistant.email.auth_service import get_token_store
        from assistant.shared.graph_client import GraphClient

        token_store = get_token_store()
        if token_store.is_connected:
            graph_client = GraphClient(token_store=token_store)
    except Exception:
        logger.warning("Microsoft auth not available — email notifications disabled")

    try:
        report = await job_agent.run_agent(
            database_url=settings.database_url,
            bedrock_client=bedrock_client,
            model_id=settings.bedrock_model_id,
            rapidapi_key=settings.rapidapi_key,
            rapidapi_host=settings.rapidapi_host,
            memory_client=memory_client,
            graph_client=graph_client,
            notification_email=settings.notification_email,
            delay_seconds=settings.scraper_delay_seconds,
            max_per_query=settings.scraper_max_results_per_query,
            user_id=user_id,
        )
        _latest_reports[user_id] = report
    except Exception:
        logger.exception("Job hunt agent run failed")


def _get_mcp_token(settings: Settings) -> Optional[str]:
    # Same-host auth to the memory API uses the shared INTERNAL_SECRET, which
    # Service A resolves to the seed admin. Stable — no OAuth token to refresh.
    return settings.internal_secret or None
