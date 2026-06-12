-- Migration: add health_metrics table
-- Run once: psql $DATABASE_URL -f migrations/001_add_health_metrics.sql
--
-- NOTE: The table is also created automatically by the health module's init_pool()
-- on first startup (CREATE TABLE IF NOT EXISTS). This file exists for reference
-- and for manual pre-creation if needed.

CREATE TABLE IF NOT EXISTS health_metrics (
    id          SERIAL PRIMARY KEY,
    recorded_at TIMESTAMPTZ      NOT NULL,
    metric_type VARCHAR(40)      NOT NULL,
    value       DOUBLE PRECISION NOT NULL,
    unit        VARCHAR(20)      NOT NULL,
    source      VARCHAR(30)      NOT NULL,
    created_at  TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
    UNIQUE (recorded_at, metric_type, source)
);

CREATE INDEX IF NOT EXISTS idx_hm_type_time ON health_metrics (metric_type, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_hm_date      ON health_metrics (date_trunc('day', recorded_at));
