import logging
import os
import tempfile
from datetime import date, datetime

import boto3
import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from functools import lru_cache

from assistant.health.compute import compute_daily_summary
from assistant.health.db import bulk_insert, fetch_trends, get_pool, init_pool
from assistant.health.ingest import parse_apple_health_export
from assistant.health.models import (
    DailyHealthSummary,
    HealthInsightResponse,
    ManualEntryRequest,
    HealthMetric,
    SOURCE,
)
from assistant.health.workflow import fetch_from_mcp_memory, run_daily_health_workflow
from assistant.shared.auth import require_auth
from assistant.shared.settings import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])

TREND_METRICS = ["weight_kg", "resting_hr", "sleep_duration_min", "steps",
                 "hrv_ms", "active_energy_kcal", "body_fat_percent"]


def _get_fresh_token() -> str:
    response = httpx.post(
        "http://localhost:8000/api/oauth/token",
        data={
            "grant_type":    "refresh_token",
            "refresh_token": os.environ["MCP_MEMORY_REFRESH_TOKEN"],
            "client_id":     os.environ["MCP_MEMORY_CLIENT_ID"],
        },
    )
    return response.json()["access_token"]


@lru_cache
def _bedrock(region: str):
    return boto3.client("bedrock-runtime", region_name=region)


async def _pool():
    settings = get_settings()
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL not configured")
    return await init_pool(settings.database_url)


# ── Import ────────────────────────────────────────────────────────────────────

@router.post("/health/import/apple-health")
async def import_apple_health(
    file: UploadFile = File(...),
    _: str = Depends(require_auth),
):
    """Accept export.xml (potentially large). Stream to /tmp, parse, bulk-insert new rows."""
    pool = await _pool()

    # Stream to temp file to avoid loading 100MB+ into memory
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xml") as tmp:
        tmp_path = tmp.name
        chunk_size = 64 * 1024
        while chunk := await file.read(chunk_size):
            tmp.write(chunk)

    try:
        with open(tmp_path, "rb") as f:
            xml_bytes = f.read()
    finally:
        os.unlink(tmp_path)

    metrics = parse_apple_health_export(xml_bytes)
    if not metrics:
        return {"inserted": 0, "date_range": [None, None]}

    inserted = await bulk_insert(pool, metrics)

    dates = [m.recorded_at.date().isoformat() for m in metrics]
    date_range = [min(dates), max(dates)]

    return {"inserted": inserted, "date_range": date_range}


# ── Manual entry ──────────────────────────────────────────────────────────────

@router.post("/health/manual-entry")
async def manual_entry(
    body: ManualEntryRequest,
    _: str = Depends(require_auth),
):
    """Insert a single metric with source='manual'. For days when the export is stale."""
    pool = await _pool()
    from assistant.health.db import insert_one

    metric = HealthMetric(
        recorded_at=body.recorded_at,
        metric_type=body.metric_type,
        value=body.value,
        unit=body.unit,
        source="manual",
    )
    saved = await insert_one(pool, metric)
    return {"saved": saved}


# ── Workflow trigger ──────────────────────────────────────────────────────────

@router.post("/health/run-daily/{target_date}", response_model=HealthInsightResponse)
async def run_daily(
    target_date: date,
    _: str = Depends(require_auth),
):
    """Trigger the full workflow for a specific date (used by cron / manual trigger)."""
    settings = get_settings()
    pool = await _pool()
    bedrock_client = _bedrock(settings.aws_region)

    mcp_url = settings.mcp_memory_url
    mcp_token = None
    if mcp_url:
        try:
            mcp_token = _get_fresh_token()
        except Exception:
            logger.warning("Could not get MCP token — memory save will be skipped", exc_info=True)

    return await run_daily_health_workflow(
        target_date=target_date,
        pool=pool,
        bedrock_client=bedrock_client,
        model_id=settings.bedrock_model_id,
        mcp_url=mcp_url,
        mcp_token=mcp_token,
    )


# ── Fetch previous run ────────────────────────────────────────────────────────

@router.get("/health/daily/{target_date}", response_model=HealthInsightResponse)
async def get_daily(
    target_date: date,
    _: str = Depends(require_auth),
):
    """Return a previously computed daily summary from MCP memory (no LLM re-run)."""
    settings = get_settings()
    if not settings.mcp_memory_url:
        raise HTTPException(503, "MCP_MEMORY_URL not configured")

    try:
        token = _get_fresh_token()
    except Exception as exc:
        raise HTTPException(503, f"Could not obtain MCP auth token: {exc}") from exc

    result = await fetch_from_mcp_memory(target_date, settings.mcp_memory_url, token)
    if not result:
        # Do NOT raise 404 here: CloudFront rewrites 403/404 responses to the
        # SPA's index.html (status 200), so the frontend would receive HTML
        # instead of this error. Return a structured "not run" payload instead.
        return HealthInsightResponse(
            date=target_date,
            status="not_run",
            summary=DailyHealthSummary(date=target_date),
            flags=[],
            coach_insight="",
            reasoning=(
                f"No stored health summary for {target_date.isoformat()} — "
                "the daily workflow has not run for this date yet."
            ),
        )
    return result


# ── Trends ───────────────────────────────────────────────────────────────────

@router.get("/health/trends")
async def get_trends(
    days: int = Query(default=30, ge=1, le=365),
    _: str = Depends(require_auth),
):
    """Return daily time series for charting: weight, resting_hr, sleep, steps, etc."""
    pool = await _pool()
    series = await fetch_trends(pool, TREND_METRICS, days)
    return {"days": days, "series": series}


# ── Summary (no LLM) ─────────────────────────────────────────────────────────

@router.get("/health/summary/{target_date}", response_model=DailyHealthSummary)
async def get_summary(
    target_date: date,
    _: str = Depends(require_auth),
):
    """Compute and return a daily summary on-demand (no LLM call, no insight)."""
    pool = await _pool()
    return await compute_daily_summary(pool, target_date)
