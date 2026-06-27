# Agent Trading Desk — Build Contract (single source of truth)

This is the shared contract for the **Agent Trading Desk** feature (Finances →
Trading). All subagents MUST build against the names/shapes below so the pieces
integrate. The coordinator (main session) owns final integration; **subagents
must NOT `git commit`/`git push`** — leave that to the coordinator.

Design reference (full UI copy, states, agent graph, tokens):
`design_handoffs/design_handoff_trading_desk/` (read its `README.md`).

## Where everything lives
- **Service B** (`agents/`, port 8001, async, **asyncpg**). nginx already routes
  `/api/trading/*` → 8001. The whole feature is Service B + frontend.
- Auth: `from assistant.shared.auth import require_user` →
  `{"token","user_id","is_admin","internal"}`. `user_id` is the platform JWT
  `sub` (str UUID) or `None` for admin/internal/legacy-OAuth (seed admin).
- LLM workers follow `assistant/trading/day_trader.py`: subclass
  `assistant.shared.base_llm_service.BaseLLMService`, call
  `assistant.shared.bedrock_retry.invoke_with_tool_retry(...)` with a tool spec.
  Bedrock client + model from `Settings` (`get_settings`, `settings.aws_region`,
  `settings.bedrock_model_id`).
- User context: `assistant.shared.memory_client.MemoryClient` +
  `assistant.shared.user_profile.build_user_profile(memory_client, domain=...)`
  and `memory_client.fetch_investing_strategy()`.
- Keep the EXISTING `/api/trading/analyse` and `/api/trading/latest` (the old
  analyst) working — do not break them.

## Strategy → guardrail defaults (from handoff)
| Strategy | max_trade_pct | day_loss_pct | crypto_pct | default_stop_pct |
|---|---|---|---|---|
| conservative | 8 | 1.5 | 0 | 6 |
| moderate (default) | 18 | 4 | 10 | 6 |
| aggressive | 35 | 9 | 25 | 6 |

Reserve floor default €5,000. Paper starting balance €100,000.

## Funding modes (IMPORTANT)
- **paper** = fully internal simulation. NO broker key required (anyone can try).
  Fills simulated at the latest snapshot price; positions + cash tracked in our
  own tables. This is the "plan mode for trading".
- **live** = real execution via the **user's own Trading 212 key** (see broker
  research below). App is a user-operated tool + disclaimers (no discretionary
  management). Even in Auto mode, show disclaimers; guardrails always apply.

## Trading 212 reality (from broker research, 2026-06-27)
- Base URLs by env: demo `https://demo.trading212.com/api/v0`, live
  `https://live.trading212.com/api/v0`. Same endpoints; only host differs.
  (We use Demo only as an optional advanced "live-practice"; default paper is
  our internal sim.)
- Auth in flux: primary `Authorization: Basic base64(API_KEY:API_SECRET)`;
  fallback `Authorization: <API_KEY>`. Make auth a single swappable function.
- Orders: `POST /equity/orders/market` body
  `{"ticker":"AAPL_US_EQ","quantity":0.1,"extendedHours":false}` (qty>0 buy,
  <0 sell); `POST /equity/orders/limit` adds `"limitPrice"`,`"timeValidity":"DAY"`.
  `GET /equity/orders/{id}`, `GET /equity/orders`, `DELETE /equity/orders/{id}`.
- **Live executes MARKET orders reliably during beta**; prefer market on live.
- **POSTs are NOT idempotent** → per-intent lock + persist returned `id` before
  any retry; reconcile against `GET /equity/orders`.
- **No instrument search** → cache `GET /equity/metadata/instruments` and resolve
  `AAPL` → `AAPL_US_EQ` client-side (match shortName/name/isin), per env.
- Read: `GET /equity/account/cash`, `GET /equity/positions`. Fills are POLL-only.
- Rate limits: read `x-ratelimit-*` headers and back off.

---

## Data layer — owned by `agents/assistant/trading/db.py` (database-agent)
asyncpg, bootstrapped with `CREATE TABLE IF NOT EXISTS` DDL run at import/startup
(mirror `assistant/job/db.py`). Mirror the DDL into
`migrations/00NN_trading_desk.sql` (use the next free number; check existing).
Every user-data table carries `user_id UUID` and is scoped by it
(`# MUST SCOPE BY USER`). Stored broker secrets are CIPHERTEXT (encryption done
in the service layer; db.py just stores/returns the encrypted strings).

Tables:
- `trading_config(user_id UUID, account TEXT, strategy TEXT, mode TEXT,
  allocation NUMERIC, reserve_floor NUMERIC, universe JSONB, guardrails JSONB,
  updated_at TIMESTAMPTZ)` — unique on `user_id` (one config per user;
  `user_id IS NULL` row = seed-admin/owner).
- `trading_broker_connection(id, user_id UUID, provider TEXT DEFAULT 'trading212',
  environment TEXT, api_key_enc TEXT, api_secret_enc TEXT NULL, status TEXT,
  label TEXT, connected_at, last_verified_at)` — unique(user_id, provider).
- `trading_run(id, user_id UUID, account TEXT, strategy TEXT, mode TEXT,
  allocation NUMERIC, reserve NUMERIC, status TEXT, market_read TEXT,
  notional NUMERIC, error TEXT, started_at, finished_at)`.
  status ∈ researching|drafting|evaluating|awaiting_approval|executing|done|denied|cancelled|failed
- `trading_run_event(id, run_id, user_id, stage TEXT, agent TEXT, type TEXT,
  message TEXT, created_at)`.
  stage ∈ research|coordinate|strategy|evaluate|execute ;
  agent ∈ coordinator|web_scout|analyst|strategist|risk_officer|broker ;
  type ∈ work|report|think|spawn|gate|done
- `trading_trade(id, run_id, user_id, ticker TEXT, name TEXT, side TEXT,
  amount NUMERIC, pct_of_allocation NUMERIC, headline TEXT, reasoning TEXT,
  evidence JSONB, risk_verdict TEXT, risk_note TEXT, kept BOOLEAN DEFAULT true,
  status TEXT DEFAULT 'pending', order_type TEXT, limit_price NUMERIC NULL,
  broker_order_id TEXT NULL, filled_qty NUMERIC NULL, filled_price NUMERIC NULL,
  created_at)`.
  side ∈ buy|trim|sell ; risk_verdict ∈ cleared|adjusted|protected|rejected ;
  status ∈ pending|placed|skipped|rejected
- `trading_position(id, user_id UUID, account TEXT, ticker TEXT, name TEXT,
  qty NUMERIC, avg_price NUMERIC, asset_class TEXT, updated_at)` —
  unique(user_id, account, ticker). (Paper holdings; may also cache live.)
- `trading_paper_account(user_id UUID, cash NUMERIC, starting_balance NUMERIC,
  updated_at)` — unique(user_id).

Async helper functions db.py MUST expose (signatures the service layer calls):
```
async def get_config(user_id) -> dict | None
async def upsert_config(user_id, **fields) -> dict
async def get_broker(user_id, provider="trading212") -> dict | None   # incl *_enc
async def upsert_broker(user_id, provider, environment, api_key_enc,
                        api_secret_enc, status, label) -> dict
async def delete_broker(user_id, provider="trading212") -> None
async def set_broker_verified(user_id, provider="trading212") -> None
async def create_run(user_id, account, strategy, mode, allocation, reserve) -> dict
async def update_run(run_id, **fields) -> None        # status, market_read, notional, error, finished_at
async def get_run(run_id, user_id) -> dict | None     # MUST SCOPE BY USER
async def latest_run(user_id) -> dict | None
async def add_event(run_id, user_id, stage, agent, type, message) -> None
async def list_events(run_id, user_id) -> list[dict]
async def add_trades(run_id, user_id, trades: list[dict]) -> list[dict]  # returns rows w/ ids
async def list_trades(run_id, user_id) -> list[dict]
async def set_trade_kept(trade_id, user_id, kept: bool) -> None
async def update_trade(trade_id, user_id, **fields) -> None  # status, broker_order_id, filled_*
async def get_paper_account(user_id) -> dict          # creates @100000 if missing
async def adjust_paper_cash(user_id, delta) -> None
async def get_positions(user_id, account) -> list[dict]
async def upsert_position(user_id, account, ticker, name, qty, avg_price, asset_class) -> None
```
db.py provides connection/pool via its own asyncpg pool (mirror job/db.py). Run the
DDL once at startup (export an `async def init_db()` the app lifespan can call, or
self-init on first use like job/db.py — match whatever job/db.py does).

---

## Service layer + agent graph — `agents/assistant/trading/desk/` (backend agent)
- `brokers/base.py` — `BrokerAdapter` Protocol/ABC: `get_cash()`, `get_positions()`,
  `resolve_symbol(symbol)->str`, `place_market_order(ticker, quantity, ...)`,
  `place_limit_order(ticker, quantity, limit_price, ...)`, `get_order(id)`,
  `cancel_order(id)`. Returns plain dicts.
- `brokers/trading212.py` — live adapter per the research (httpx, env→base URL,
  swappable auth, instrument cache + resolver, rate-limit backoff, idempotency
  lock, typed `BrokerError`).
- `brokers/paper.py` — internal simulation adapter (same interface): fills at the
  latest snapshot price; updates `trading_position` + `trading_paper_account` via
  db.py. Used when `account == "paper"`.
- `crypto.py` — `encrypt(s)->str` / `decrypt(s)->str` (Fernet from
  `cryptography`); key derived from env `TRADING_SECRET_KEY` (fall back to
  `SECRET_KEY`). Used to store the T212 key/secret. NEVER log plaintext.
- `workers.py` — the LLM workers (subclass BaseLLMService + invoke_with_tool_retry):
  `Analyst.analyse(snapshot, profile, strategy_ctx) -> signals`,
  `Strategist.draft(signals, snapshot, config) -> [candidate trades]`,
  `RiskOfficer.evaluate(candidates, config) -> [trades w/ verdict+sizing+stops]`.
  Reuse `market_data.collect_market_snapshot` for the Web scout.
- `coordinator.py` — `async def run_desk(run_id, user_id, config)` orchestrates:
  research (web_scout+analyst) → coordinate → strategy → evaluate → [Controlled:
  stop at `awaiting_approval`; Auto: continue] → execute. Writes
  `trading_run_event` rows at each step (work/report/think/spawn/gate/done) and
  `trading_trade` rows after evaluate; updates run status + market_read + notional.
  Execution: `async def execute_run(run_id, user_id)` places kept+non-rejected
  trades via the chosen adapter, updates trade status/broker_order_id/fills and
  paper positions/cash.
- The run is launched as a background asyncio task from the POST /runs route; the
  frontend polls run detail. (No SSE.)

---

## HTTP API — added to `agents/main.py` (backend agent), all `Depends(require_user)`
Prefix `/api/trading/desk`. JSON bodies; return JSON (never 403 — use 401/400/502).

- `GET  /config` → config (create defaults if none, seeded from strategy table).
- `PUT  /config` body `{account?,strategy?,mode?,allocation?,reserve_floor?,universe?,guardrails?}` → updated config. Changing `strategy` re-seeds guardrail defaults unless explicitly overridden.
- `GET  /broker` → `{connected: bool, provider, environment, label, status, last_verified_at}` (NEVER return secrets).
- `PUT  /broker` body `{environment:"demo"|"live", api_key, api_secret?}` → verifies via a live `get_cash()` call, stores encrypted, returns `/broker` shape. 400 on bad key.
- `DELETE /broker` → `{connected:false}`.
- `POST /runs` → starts a run (creates `trading_run`, launches background task), returns `{run: <run>, events: [], trades: []}`. 409 if a run is already in progress for this user.
- `GET  /runs/latest` → `{run, events, trades}` or `{run:null}` (used to resume after the user closed the window).
- `GET  /runs/{id}` → `{run, events, trades}` (MUST SCOPE BY USER). Frontend polls this ~1.5s while `run.status` is non-terminal.
- `POST /runs/{id}/approve` → (Controlled) execute kept trades; returns updated `{run, events, trades}`.
- `POST /runs/{id}/deny` → stop run, status=denied; returns updated state.
- `POST /runs/{id}/cancel` → cancel an in-progress run (status=cancelled).
- `POST /trades/{id}/keep` and `POST /trades/{id}/skip` → toggle `kept`; recompute run `notional`; return the trade.
- `GET  /portfolio` → `{account, value, cash, day_change, since_funded, holdings:[{ticker,name,value,pct,day_change,asset_class}]}`. paper: from positions+cash; live: from T212 get_cash/get_positions.

Run/trade/event JSON field names = the DB column names above (snake_case). The
frontend maps these to the handoff's camelCase view-model.

---

## Frontend — `frontend/src/components/finances/` + composable (frontend agent)
- New `TradingDeskPanel.vue` (+ subcomponents) implementing the handoff's Trading
  Desk inside the Finances → Trading tab. Reuse `frontend/src/styles/tokens.css`
  and existing components; match the "Calm Intelligence" design. States: Setup,
  Working (stepper), Cards+Approval (PRIMARY), Monitoring; plus the always-visible
  Mode banner. Cards layout is the production default (skip the alt layouts).
- `composables/useTradingDesk.ts` calls the `/api/trading/desk/*` endpoints above
  (same-origin, `API_BASE=''`; send the auth bearer like other finance calls —
  check how DayTradingPanel/InvestingPanel authenticate). Poll `GET /runs/{id}`
  ~1.5s while running; stop at terminal status. Approve/deny/keep/skip wired.
- Map snake_case API fields → the handoff view-model. All product copy comes from
  the handoff (`td-data.jsx`, README). Disclaimers required on the Live path.
- Must `npm run build` (or typecheck) clean before you report done.
