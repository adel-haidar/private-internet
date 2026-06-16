#!/usr/bin/env python3
"""
Private Internet — API Credit Dashboard (local tool)

A self-contained dashboard to see, at a glance, which third-party APIs the project
depends on, WHY each is needed, and HOW MUCH CREDIT is left — so you know when to top up.

  $ python3 check_credits.py
  -> open http://localhost:8765

Design notes:
- stdlib only. No pip install, no framework.
- Reads keys from ../stripe_secret.properties (gitignored). Secret keys NEVER leave
  this machine — all provider calls happen server-side in this process; the browser
  only ever sees the resulting balances, never the keys.
- Live credit is fetched for the providers that expose a balance API (ElevenLabs,
  Suno, fal.ai). Replicate has no balance API (postpaid) -> dashboard link. Stripe's
  balance is "money received", not spend-credit, and this is a TEST key -> shown for
  reference only. The remaining APIs from docs/EXTERNAL_APIS.md (AWS, Gemini, etc.)
  bill via AWS or are free, so they're listed for context with no credit to poll.
"""

import base64
import json
import os
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PORT = int(os.environ.get("CREDIT_DASHBOARD_PORT", "8765"))
HTTP_TIMEOUT = 15  # seconds per provider call

# "Top up soon" thresholds. Tune to taste.
ELEVENLABS_LOW_PCT = 20.0      # warn when < 20% of monthly characters remain
FAL_LOW_USD = 10.0            # warn when fal.ai balance < $10
SUNO_LOW_CREDITS = 50.0       # warn when Suno credits < 50

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_KEYS_PATH = os.path.join(SCRIPT_DIR, "..", "stripe_secret.properties")
KEYS_PATH = os.environ.get("STRIPE_SECRET_PROPERTIES", DEFAULT_KEYS_PATH)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_keys(path):
    """Parse a simple KEY=VALUE .properties file."""
    keys = {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                keys[k.strip()] = v.strip()
    except FileNotFoundError:
        print(f"!! keys file not found: {path}", file=sys.stderr)
    return keys


def http_json(url, headers=None, timeout=HTTP_TIMEOUT):
    """GET url and return parsed JSON. Raises urllib errors on failure."""
    # Some providers (Suno, Replicate) sit behind Cloudflare and reject requests
    # with no/blank User-Agent (HTTP 403 "error code: 1010"). Send a real one.
    hdrs = {"User-Agent": "Mozilla/5.0 (credit-dashboard)", "Accept": "application/json"}
    hdrs.update(headers or {})
    req = urllib.request.Request(url, headers=hdrs, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def card(name, why, status, value, detail="", pct=None, link=None,
         billing="live", category=""):
    """Build a uniform card dict for the frontend."""
    return {
        "name": name,
        "category": category,
        "why": why,
        "status": status,        # ok | low | error | info
        "value": value,          # headline string
        "detail": detail,        # secondary string
        "pct": pct,              # 0-100 for a bar, or None
        "link": link,            # external dashboard URL
        "billing": billing,      # live | aws | free | scrape | info
    }


def err_detail(exc):
    if isinstance(exc, urllib.error.HTTPError):
        body = ""
        try:
            body = exc.read().decode("utf-8")[:200]
        except Exception:
            pass
        return f"HTTP {exc.code}: {body or exc.reason}"
    if isinstance(exc, urllib.error.URLError):
        return f"network error: {exc.reason}"
    return str(exc)


# ---------------------------------------------------------------------------
# Provider fetchers — each returns a card dict
# ---------------------------------------------------------------------------

def fetch_elevenlabs(key):
    why = "Voice/TTS narration + music generation (ARIA, SIGNAL voiceover)"
    if not key:
        return card("ElevenLabs", why, "info", "no key found",
                    billing="live", category="Content & Media")
    try:
        data = http_json(
            "https://api.elevenlabs.io/v1/user/subscription",
            headers={"xi-api-key": key},
        )
        used = int(data.get("character_count", 0))
        limit = int(data.get("character_limit", 0)) or 1
        remaining = max(limit - used, 0)
        pct = remaining / limit * 100
        tier = data.get("tier", "")
        status = "low" if pct < ELEVENLABS_LOW_PCT else "ok"
        return card(
            "ElevenLabs", why, status,
            f"{remaining:,} chars left",
            detail=f"{used:,} / {limit:,} used  ·  tier: {tier or 'n/a'}",
            pct=round(pct, 1),
            link="https://elevenlabs.io/app/usage",
            category="Content & Media",
        )
    except Exception as exc:
        return card("ElevenLabs", why, "error", "fetch failed",
                    detail=err_detail(exc),
                    link="https://elevenlabs.io/app/usage",
                    category="Content & Media")


def fetch_suno(key):
    why = "AI music generation for ARIA"
    if not key:
        return card("Suno (sunoapi.org)", why, "info", "no key found",
                    category="Content & Media")
    try:
        data = http_json(
            "https://api.sunoapi.org/api/v1/generate/credit",
            headers={"Authorization": f"Bearer {key}"},
        )
        # API wraps payload as {code,msg,data}; data is the credit number.
        raw = data.get("data", data)
        if isinstance(raw, dict):
            raw = raw.get("credits", raw.get("credit", 0))
        credits = float(raw)
        status = "low" if credits < SUNO_LOW_CREDITS else "ok"
        return card(
            "Suno (sunoapi.org)", why, status,
            f"{credits:,.0f} credits",
            detail="threshold for top-up: "
                   f"{SUNO_LOW_CREDITS:,.0f}",
            link="https://sunoapi.org/dashboard",
            category="Content & Media",
        )
    except Exception as exc:
        return card("Suno (sunoapi.org)", why, "error", "fetch failed",
                    detail=err_detail(exc),
                    link="https://sunoapi.org/dashboard",
                    category="Content & Media")


def fetch_fal(key):
    why = "Image generation (FLUX — PULSE images, SIGNAL slides) + Kling video (STORIES)"
    if not key:
        return card("fal.ai", why, "info", "no key found",
                    category="Content & Media")
    try:
        data = http_json(
            "https://api.fal.ai/v1/account/billing?expand=credits",
            headers={"Authorization": f"Key {key}"},
        )
        credits = data.get("credits") or {}
        bal = float(credits.get("current_balance", 0))
        cur = (credits.get("currency") or "usd").upper()
        sym = "$" if cur == "USD" else ""
        status = "low" if (cur == "USD" and bal < FAL_LOW_USD) else "ok"
        return card(
            "fal.ai", why, status,
            f"{sym}{bal:,.2f} {cur if not sym else ''}".strip(),
            detail=f"top-up threshold: ${FAL_LOW_USD:.0f}" if cur == "USD" else "",
            link="https://fal.ai/dashboard/billing",
            category="Content & Media",
        )
    except Exception as exc:
        return card("fal.ai", why, "error", "fetch failed",
                    detail=err_detail(exc),
                    link="https://fal.ai/dashboard/billing",
                    category="Content & Media")


def fetch_replicate(key):
    why = "Wan2.1 video clip generation (SIGNAL + PULSE, high-volume)"
    link = "https://replicate.com/account/billing"
    if not key:
        return card("Replicate", why, "info", "no key found", link=link,
                    billing="scrape", category="Content & Media")
    try:
        # No balance API (postpaid). Verify the key is valid via /v1/account.
        acct = http_json(
            "https://api.replicate.com/v1/account",
            headers={"Authorization": f"Bearer {key}"},
        )
        who = acct.get("username") or acct.get("name") or "account ok"
        return card(
            "Replicate", why, "info", "no balance API",
            detail=f"key valid ({who}) · postpaid — check dashboard",
            link=link, billing="scrape", category="Content & Media",
        )
    except Exception as exc:
        return card("Replicate", why, "error", "key check failed",
                    detail=err_detail(exc), link=link,
                    billing="scrape", category="Content & Media")


def fetch_stripe(key):
    why = "Payments / subscription billing"
    link = "https://dashboard.stripe.com/test/balance"
    is_test = key.startswith("sk_test_") if key else False
    if not key:
        return card("Stripe", why, "info", "no key found", link=link,
                    category="Auth & Payments")
    try:
        auth = base64.b64encode(f"{key}:".encode()).decode()
        data = http_json(
            "https://api.stripe.com/v1/balance",
            headers={"Authorization": f"Basic {auth}"},
        )
        avail = data.get("available", [])
        parts = [f"{a['amount']/100:,.2f} {a['currency'].upper()}" for a in avail] or ["0.00"]
        mode = "TEST mode" if is_test else "LIVE mode"
        return card(
            "Stripe", why, "info",
            "  ·  ".join(parts) + " available",
            detail=f"{mode} — this is revenue received, not spend-credit",
            link=link, category="Auth & Payments",
        )
    except Exception as exc:
        return card("Stripe", why, "error", "fetch failed",
                    detail=err_detail(exc), link=link,
                    category="Auth & Payments")


# Static context entries (no key in the file; here for the full dependency map).
def static_cards():
    aws = "https://eu-central-1.console.aws.amazon.com/billing/home#/bills"
    return [
        card("AWS Bedrock", "Core LLM + Titan Embed v2 embeddings (memory, all reasoning)",
             "info", "billed via AWS", detail="pay-as-you-go — no prepaid credit",
             link=aws, billing="aws", category="AWS"),
        card("AWS Polly", "Text-to-speech narration for SIGNAL videos",
             "info", "billed via AWS", link=aws, billing="aws", category="AWS"),
        card("AWS S3", "Storage for generated images, audio, video",
             "info", "billed via AWS", link=aws, billing="aws", category="AWS"),
        card("AWS SES", "Transactional email (password reset, verification)",
             "info", "billed via AWS", link=aws, billing="aws", category="AWS"),
        card("Google Gemini", "Topic extraction from memory, research, video-job content",
             "info", "billed via Google", detail="check Google AI Studio / GCP billing",
             link="https://aistudio.google.com/app/apikey", billing="aws",
             category="Content & Media"),
        card("RapidAPI / JSearch", "Job listings for the job-hunter agent",
             "info", "quota plan", detail="check RapidAPI dashboard for monthly quota",
             link="https://rapidapi.com/developer/billing", billing="info",
             category="Agents"),
        card("Yahoo Finance", "Market data quotes for the trading agent",
             "info", "free / unofficial", link="https://finance.yahoo.com",
             billing="free", category="Agents"),
        card("Google OAuth", "Google sign-in for user authentication",
             "info", "free", link="https://console.cloud.google.com/apis/credentials",
             billing="free", category="Auth & Payments"),
    ]


def gather():
    keys = load_keys(KEYS_PATH)
    cards = [
        fetch_elevenlabs(keys.get("ELEVEN_LABS_API_KEY")),
        fetch_suno(keys.get("SUNO_API_KEY")),
        # fal's billing endpoint needs an *admin* key; fall back to the regular
        # key (will 403 with a clear message until an admin key is added).
        fetch_fal(keys.get("FAL_AI_ADMIN_KEY") or keys.get("FAL_AI_API_KEY")),
        fetch_replicate(keys.get("REPLICATE_API_KEY")),
        fetch_stripe(keys.get("SECRET_KEY")),
    ]
    cards.extend(static_cards())
    return {
        "keys_path": os.path.normpath(KEYS_PATH),
        "keys_loaded": len(keys) > 0,
        "cards": cards,
    }


# ---------------------------------------------------------------------------
# HTTP server
# ---------------------------------------------------------------------------

INDEX_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>API Credits — Private Internet</title>
<style>
  :root {
    --bg: #0f1115; --panel: #171a21; --panel2: #1d212b; --border: #2a2f3a;
    --text: #e7e9ee; --muted: #9aa3b2; --accent: #7c83ff; --amber: #f5a623;
    --ok: #36c08b; --low: #f5a623; --error: #ef5d6b; --info: #6b7280;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--text);
    font-family: -apple-system, "Plus Jakarta Sans", "Inter", system-ui, sans-serif;
    padding: 32px 24px 64px;
  }
  header { max-width: 1100px; margin: 0 auto 24px; }
  h1 { font-size: 22px; margin: 0 0 4px; letter-spacing: .2px; }
  .sub { color: var(--muted); font-size: 13px; }
  .bar { display: flex; align-items: center; gap: 12px; margin-top: 16px; }
  button {
    background: var(--accent); color: white; border: 0; border-radius: 8px;
    padding: 9px 16px; font-size: 13px; font-weight: 600; cursor: pointer;
  }
  button:disabled { opacity: .5; cursor: default; }
  .meta { color: var(--muted); font-size: 12px; }
  main { max-width: 1100px; margin: 0 auto; }
  .group-title {
    color: var(--muted); font-size: 12px; text-transform: uppercase;
    letter-spacing: 1px; margin: 28px 0 10px;
  }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 12px; }
  .card {
    background: var(--panel); border: 1px solid var(--border); border-radius: 12px;
    padding: 16px; display: flex; flex-direction: column; gap: 8px;
  }
  .card.low { border-color: rgba(245,166,35,.5); }
  .card.error { border-color: rgba(239,93,107,.5); }
  .card-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }
  .name { font-weight: 700; font-size: 15px; }
  .pill {
    font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .5px;
    padding: 3px 8px; border-radius: 999px; white-space: nowrap;
  }
  .pill.ok { background: rgba(54,192,139,.15); color: var(--ok); }
  .pill.low { background: rgba(245,166,35,.18); color: var(--low); }
  .pill.error { background: rgba(239,93,107,.18); color: var(--error); }
  .pill.info { background: rgba(155,163,178,.15); color: var(--muted); }
  .value { font-size: 20px; font-weight: 700; font-variant-numeric: tabular-nums; }
  .value.error { color: var(--error); font-size: 15px; }
  .why { color: var(--muted); font-size: 12.5px; line-height: 1.45; }
  .detail { color: var(--muted); font-size: 11.5px; font-family: "JetBrains Mono", monospace; }
  .track { height: 6px; background: var(--panel2); border-radius: 4px; overflow: hidden; }
  .fill { height: 100%; border-radius: 4px; background: var(--ok); }
  .fill.low { background: var(--low); }
  a.link { color: var(--accent); font-size: 12px; text-decoration: none; margin-top: 2px; }
  a.link:hover { text-decoration: underline; }
  .warnbox {
    background: rgba(245,166,35,.1); border: 1px solid rgba(245,166,35,.4);
    color: var(--amber); border-radius: 10px; padding: 12px 14px; font-size: 13px;
    margin-bottom: 8px;
  }
  .empty { color: var(--muted); padding: 40px; text-align: center; }
</style>
</head>
<body>
<header>
  <h1>🔋 API Credits &amp; Dependencies</h1>
  <div class="sub">Private Internet — local view. Keys read from <code id="keypath">…</code>, never sent to the browser.</div>
  <div class="bar">
    <button id="refresh">Refresh</button>
    <span class="meta" id="status">loading…</span>
  </div>
</header>
<main id="root"><div class="empty">Loading…</div></main>

<script>
const STATUS_ORDER = { low: 0, error: 1, ok: 2, info: 3 };
const PILL_TEXT = { ok: "ok", low: "top up", error: "error", info: "info" };

async function load() {
  const btn = document.getElementById("refresh");
  const status = document.getElementById("status");
  btn.disabled = true; status.textContent = "fetching balances…";
  try {
    const res = await fetch("/api/credits");
    const data = await res.json();
    render(data);
    status.textContent = "updated " + new Date().toLocaleTimeString();
  } catch (e) {
    status.textContent = "failed: " + e;
  } finally {
    btn.disabled = false;
  }
}

function render(data) {
  document.getElementById("keypath").textContent = data.keys_path;
  const root = document.getElementById("root");
  root.innerHTML = "";

  if (!data.keys_loaded) {
    const w = document.createElement("div");
    w.className = "warnbox";
    w.textContent = "No keys loaded — check that stripe_secret.properties exists at the path above.";
    root.appendChild(w);
  }

  const lows = data.cards.filter(c => c.status === "low");
  if (lows.length) {
    const w = document.createElement("div");
    w.className = "warnbox";
    w.textContent = "⚠️ Top up soon: " + lows.map(c => c.name).join(", ");
    root.appendChild(w);
  }

  const groups = {};
  for (const c of data.cards) (groups[c.category] = groups[c.category] || []).push(c);

  for (const [cat, cards] of Object.entries(groups)) {
    cards.sort((a, b) => STATUS_ORDER[a.status] - STATUS_ORDER[b.status]);
    const t = document.createElement("div");
    t.className = "group-title"; t.textContent = cat;
    root.appendChild(t);
    const grid = document.createElement("div");
    grid.className = "grid";
    for (const c of cards) grid.appendChild(cardEl(c));
    root.appendChild(grid);
  }
}

function cardEl(c) {
  const el = document.createElement("div");
  el.className = "card " + c.status;
  el.innerHTML = `
    <div class="card-top">
      <span class="name">${esc(c.name)}</span>
      <span class="pill ${c.status}">${PILL_TEXT[c.status] || c.status}</span>
    </div>
    <div class="value ${c.status === "error" ? "error" : ""}">${esc(c.value)}</div>
    ${c.pct != null ? `<div class="track"><div class="fill ${c.status}" style="width:${c.pct}%"></div></div>` : ""}
    <div class="why">${esc(c.why)}</div>
    ${c.detail ? `<div class="detail">${esc(c.detail)}</div>` : ""}
    ${c.link ? `<a class="link" href="${esc(c.link)}" target="_blank" rel="noopener">open dashboard ↗</a>` : ""}
  `;
  return el;
}

function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"]/g, m =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[m]));
}

document.getElementById("refresh").addEventListener("click", load);
load();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, content_type):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/api/credits"):
            payload = json.dumps(gather()).encode("utf-8")
            self._send(200, payload, "application/json")
        elif self.path in ("/", "/index.html"):
            self._send(200, INDEX_HTML.encode("utf-8"), "text/html; charset=utf-8")
        else:
            self._send(404, b"not found", "text/plain")

    def log_message(self, *args):
        pass  # quiet


def main():
    keys = load_keys(KEYS_PATH)
    print(f"API Credit Dashboard")
    print(f"  keys file : {os.path.normpath(KEYS_PATH)} "
          f"({len(keys)} keys loaded)")
    print(f"  open      : http://localhost:{PORT}")
    print(f"  stop      : Ctrl+C")
    try:
        ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
