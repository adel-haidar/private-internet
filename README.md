# personal-intelligence

Self-hosted personal AI platform. Two independent services share a single repository and a single `.env` file.

## Architecture

```
                  nginx (HTTPS)
                       │
        ┌──────────────┼──────────────────────┐
        │              │                      │
  /.well-known/   /oauth/*   /api/*   /mcp/*
        │              │         │       │
        └──────────────┴─────────┴───────┘
                        │
              Service A — personal-intelligence-api
                   (port 8000, public)
                        │
              ┌─────────┴──────────┐
         FastMCP server         FastAPI app
         /mcp (Streamable-HTTP)  /oauth/*, /.well-known/*
         Tools: save/search/fetch  /api/memory/text, GET /api/memory
         Auth: PostgresTokenVerifier  /api/file (file upload)
              │
              │  ← http://localhost:8000 →
              │
        Service B — personal-intelligence-agents
             (port 8001, internal only)
             │
        ┌────┴─────────────────┐
     Email agent          Banking agent   Job agent
     (MS Graph OAuth,     (Bedrock LLM)   (multi-scraper,
      Bedrock triage,                      RapidAPI,
      Outlook drafts,                      asyncpg DB)
      cron: */15 min)
```

### Service A — `personal-intelligence-api`

Source: `src/personal_intelligence/`

Consolidates the old `mcp-memory` (port 8000) and `mcp-file-upload` (port 8002) services into one FastAPI process. The FastMCP ASGI app is mounted at `/mcp` so existing Claude Desktop and Claude.ai connections require no reconfiguration.

**Modules:**
- `config.py` — Pydantic `Settings` reading from `.env`
- `database.py` — shared `psycopg2` connection factory
- `auth/oauth.py` — full OAuth 2.1 with PKCE (no external deps, pure stdlib)
- `auth/routes.py` — `/.well-known/*` and `/oauth/*` endpoints
- `memory/service.py` — `save_memory()`, `search_memories()`, `fetch_memory()`, `list_memories()`; vector embeddings via AWS Bedrock Titan
- `memory/mcp_server.py` — FastMCP instance exposing `save`, `search`, `fetch` tools
- `memory/routes.py` — REST: `POST /api/memory/text`, `GET /api/memory`, `POST /api/file`
- `api.py` — FastAPI app factory; mounts all routers and the MCP sub-app

**Entry point:**
```
uvicorn personal_intelligence.api:app --host 127.0.0.1 --port 8000
```

### Service B — `personal-intelligence-agents`

Source: `agents/`

Migrated as-is from `adel-agent`. Multi-agent platform that runs on port 8001 (internal only, never exposed through nginx). Connects to Service A for MCP memory and OAuth token refresh.

**Agents:**
- **Email agent** — Microsoft Graph OAuth, delta sync, Bedrock triage, Outlook draft creation. Triggered by cron every 15 minutes via `GET /email/sync`.
- **Bank adviser agent** — Pulls bank statements from MCP memory, runs multi-month financial analysis via Bedrock.
- **Job agent** — Scrapes jobs.ch, StepStone, LinkedIn (via RapidAPI); scores matches with Bedrock; stores results in PostgreSQL.

**Entry point:**
```
uvicorn main:app --host 127.0.0.1 --port 8001
```
(run from the `agents/` directory)

## Local Development

```bash
# Service A
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env  # fill in real values
uvicorn personal_intelligence.api:app --port 8000 --reload

# Service B (separate terminal)
cd agents
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --port 8001 --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev  # proxies /api, /oauth, /mcp to https://adel-intelligence.com
```

## Deployment

See [MIGRATION.md](MIGRATION.md) for the full step-by-step runbook.

**Quick reference:**
```bash
# Install
sudo cp systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now personal-intelligence-api personal-intelligence-agents

# Nginx
sudo cp nginx/personal-intelligence.conf /etc/nginx/conf.d/
sudo nginx -t && sudo systemctl reload nginx
```

## Cron

The email sync cron job is unchanged from the old `adel-agent`:
```
*/15 * * * * curl -s http://localhost:8001/email/sync
```

## Database

Both services share the same AWS RDS PostgreSQL instance. Tables:
- `memories` — vector store (pgvector, 1024-dim Titan embeddings)
- `oauth_clients` / `oauth_codes` / `oauth_tokens` — OAuth 2.1 state
- `job_matches` — job hunt results (created by the job agent on first run)

Schema for `memories` and OAuth tables is auto-created by Service A on startup.
The `job_matches` schema is auto-created by the job agent on first run.
