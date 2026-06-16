# API Credit Dashboard (local tool)

A tiny, self-contained dashboard to see **which third-party APIs the project uses,
why each is needed, and how much credit is left** — so you know when to top up.

```bash
python3 credit-dashboard/check_credits.py
# then open http://localhost:8765
```

- **stdlib only** — no `pip install`, no framework.
- Reads keys from `../stripe_secret.properties` (gitignored). **Secret keys never
  leave your machine** — all provider calls happen server-side; the browser only
  sees the resulting balances.
- Not deployed. Run it locally whenever you want to check.

## What it shows

| Provider | Live credit? | Notes |
|----------|--------------|-------|
| ElevenLabs | ✅ chars remaining | key needs the **`user_read`** permission |
| Suno (sunoapi.org) | ✅ credits remaining | warns below `SUNO_LOW_CREDITS` (default 50) |
| fal.ai | ✅ USD balance | needs an **admin** key — add `FAL_AI_ADMIN_KEY=...` to the properties file |
| Replicate | ❌ (no balance API) | postpaid — links to dashboard, verifies key is valid |
| Stripe | ⚠️ balance | "money received", not spend-credit; test key shown for reference |
| AWS / Gemini / RapidAPI / Yahoo / Google OAuth | — | listed for context (billed via AWS / Google, or free) |

## Config (env vars)

| Var | Default | Purpose |
|-----|---------|---------|
| `CREDIT_DASHBOARD_PORT` | `8765` | port to serve on |
| `STRIPE_SECRET_PROPERTIES` | `../stripe_secret.properties` | path to the keys file |

Top-up thresholds (`ELEVENLABS_LOW_PCT`, `FAL_LOW_USD`, `SUNO_LOW_CREDITS`) are
constants near the top of `check_credits.py`.

## Making the two errored providers report live credit

- **ElevenLabs `401 missing_permissions`**: in ElevenLabs → Settings → API Keys,
  enable the **`user_read`** permission on the key (or use a key that has it).
- **fal.ai `403 not permitted`**: the FLUX/generation key can't read billing.
  Create an **admin** key in the fal dashboard and add it as
  `FAL_AI_ADMIN_KEY=...` in `stripe_secret.properties`.
