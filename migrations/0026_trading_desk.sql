-- 0026_trading_desk.sql
-- Agent Trading Desk persistence tables.
-- Mirrors agents/assistant/trading/db.py::_DDL which runs this idempotently
-- at service startup.
--
-- Multi-tenancy: every user-data table has user_id UUID.  # MUST SCOPE BY USER
-- Broker secret columns store CIPHERTEXT (encryption done in the service layer).
-- Paper starting balance: €100,000.

-- One config row per user (NULL user_id = seed-admin / owner).
CREATE TABLE IF NOT EXISTS trading_config (
    user_id         UUID,
    account         TEXT,
    strategy        TEXT,
    mode            TEXT,
    allocation      NUMERIC,
    reserve_floor   NUMERIC,
    universe        JSONB,
    guardrails      JSONB,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id)
);

-- Stored broker credentials (ciphertext); unique per (user, provider).
CREATE TABLE IF NOT EXISTS trading_broker_connection (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID NOT NULL,
    provider         TEXT NOT NULL DEFAULT 'trading212',
    environment      TEXT,
    api_key_enc      TEXT,
    api_secret_enc   TEXT,
    status           TEXT,
    label            TEXT,
    connected_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_verified_at TIMESTAMPTZ,
    UNIQUE (user_id, provider)
);
CREATE INDEX IF NOT EXISTS idx_trading_broker_user
    ON trading_broker_connection (user_id);

-- A single orchestrated trading run.
-- status ∈ researching|drafting|evaluating|awaiting_approval|executing|done|denied|cancelled|failed
CREATE TABLE IF NOT EXISTS trading_run (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL,
    account      TEXT,
    strategy     TEXT,
    mode         TEXT,
    allocation   NUMERIC,
    reserve      NUMERIC,
    status       TEXT NOT NULL DEFAULT 'researching',
    market_read  TEXT,
    notional     NUMERIC,
    error        TEXT,
    started_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at  TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_trading_run_user
    ON trading_run (user_id, started_at DESC);

-- Append-only event log for a run.
-- stage ∈ research|coordinate|strategy|evaluate|execute
-- agent ∈ coordinator|web_scout|analyst|strategist|risk_officer|broker
-- type  ∈ work|report|think|spawn|gate|done
CREATE TABLE IF NOT EXISTS trading_run_event (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id     UUID NOT NULL,
    user_id    UUID NOT NULL,
    stage      TEXT,
    agent      TEXT,
    type       TEXT,
    message    TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_trading_run_event_run
    ON trading_run_event (run_id, created_at);
CREATE INDEX IF NOT EXISTS idx_trading_run_event_user
    ON trading_run_event (user_id);

-- Individual trades proposed / executed within a run.
-- side         ∈ buy|trim|sell
-- risk_verdict ∈ cleared|adjusted|protected|rejected
-- status       ∈ pending|placed|skipped|rejected
CREATE TABLE IF NOT EXISTS trading_trade (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id             UUID NOT NULL,
    user_id            UUID NOT NULL,
    ticker             TEXT,
    name               TEXT,
    side               TEXT,
    amount             NUMERIC,
    pct_of_allocation  NUMERIC,
    headline           TEXT,
    reasoning          TEXT,
    evidence           JSONB,
    risk_verdict       TEXT,
    risk_note          TEXT,
    kept               BOOLEAN NOT NULL DEFAULT TRUE,
    status             TEXT    NOT NULL DEFAULT 'pending',
    order_type         TEXT,
    limit_price        NUMERIC,
    broker_order_id    TEXT,
    filled_qty         NUMERIC,
    filled_price       NUMERIC,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_trading_trade_run
    ON trading_trade (run_id);
CREATE INDEX IF NOT EXISTS idx_trading_trade_user
    ON trading_trade (user_id);

-- Paper (and optionally cached live) holdings.
CREATE TABLE IF NOT EXISTS trading_position (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL,
    account     TEXT NOT NULL,
    ticker      TEXT NOT NULL,
    name        TEXT,
    qty         NUMERIC,
    avg_price   NUMERIC,
    asset_class TEXT,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, account, ticker)
);
CREATE INDEX IF NOT EXISTS idx_trading_position_user
    ON trading_position (user_id, account);

-- Paper simulation cash account; one row per user, seeded at €100,000.
CREATE TABLE IF NOT EXISTS trading_paper_account (
    user_id          UUID PRIMARY KEY,
    cash             NUMERIC NOT NULL DEFAULT 100000,
    starting_balance NUMERIC NOT NULL DEFAULT 100000,
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- rollback:
-- DROP TABLE IF EXISTS trading_paper_account;
-- DROP TABLE IF EXISTS trading_position;
-- DROP TABLE IF EXISTS trading_trade;
-- DROP TABLE IF EXISTS trading_run_event;
-- DROP TABLE IF EXISTS trading_run;
-- DROP TABLE IF EXISTS trading_broker_connection;
-- DROP TABLE IF EXISTS trading_config;
