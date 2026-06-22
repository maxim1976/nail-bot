# Phase 8: Production Deployment
_2026-06-22_

## Goal

Make nail-bot deployable from zero on Railway — one Docker image that includes both the Python backend and the built LIFF frontend, with all configuration documented and a step-by-step first-deploy checklist.

---

## Scope

| Deliverable | Description |
|---|---|
| `Dockerfile` | Updated with Node 20 build stage for the LIFF frontend |
| `railway.toml` | Railway build + deploy config (builder, build args, health check) |
| `.env.example` | All required env vars with comments |
| `docs/deploy-checklist.md` | Step-by-step first-deploy guide from zero to live |

---

## Dockerfile

Two-stage build replacing the current single-stage placeholder.

**Stage 1 — `node-builder`:** `node:20-slim`, copies `frontend/liff/`, runs `npm ci` then `npm run build`. Accepts `ARG LIFF_ID` and sets `ENV VITE_LIFF_ID=$LIFF_ID` so Vite bakes the LIFF ID into the JavaScript bundle at build time.

**Stage 2 — `runtime`:** Identical to current Python stage. Adds one `COPY --from=node-builder` line to pull `frontend/liff/dist/` into the image. `main.py`'s existing `StaticFiles` mount at `/liff` picks it up with no changes.

`LIFF_ID` is the single variable — no separate `VITE_LIFF_ID` for the user to manage. The Dockerfile handles the rename internally.

---

## `railway.toml`

```toml
[build]
builder = "DOCKERFILE"
buildArgs = ["LIFF_ID"]

[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

- `buildArgs = ["LIFF_ID"]` tells Railway to forward the `LIFF_ID` service variable into the Docker build as a build arg.
- Health check hits `/health` (already returns `{"status": "ok"}`) so Railway knows the deploy succeeded before cutting over traffic.
- No start command override — the Dockerfile `CMD` handles `alembic upgrade head && uvicorn ...`.

---

## `.env.example`

```
# LINE
LINE_CHANNEL_ACCESS_TOKEN=   # LINE Developers → Messaging API → Channel access token
LINE_CHANNEL_SECRET=         # LINE Developers → Messaging API → Channel secret
LIFF_ID=                     # LINE Developers → LIFF → App ID (also used as Docker build arg)
RICH_MENU_ID=                # LINE Developers → Messaging API → Rich menus

# Anthropic
ANTHROPIC_API_KEY=           # console.anthropic.com

# Database
DATABASE_URL=                # Provided automatically by Railway PostgreSQL plugin

# App config
OWNER_LINE_USER_ID=          # Your LINE user ID — receives daily summary + rate-limit alerts
SELLER_LINE_ID=              # Your LINE ID shown to sales_agent prospects (e.g. @yourid)
RATE_LIMIT_HOUR=10
RATE_LIMIT_DAY=30
HISTORY_TURNS=10
DAILY_COST_KILL_USD=5.00
ADMIN_JWT_SECRET=            # Random 32+ char string: openssl rand -hex 32
TZ=Asia/Taipei
```

---

## Deploy Checklist (`docs/deploy-checklist.md`)

Six sections covering a first deploy from zero:

1. **Prerequisites** — LINE Developer account, Anthropic account, Railway account, Node 20 + Python 3.12 locally
2. **LINE setup** — create Messaging API channel (note token + secret); create LIFF app (Full type, domain = Railway URL once known, note `LIFF_ID`); create rich menu in console (note `RICH_MENU_ID`); set webhook URL to `https://<domain>/webhook`
3. **Railway project** — create project → add PostgreSQL plugin (`DATABASE_URL` auto-set) → add web service from GitHub repo → populate all env vars from `.env.example` as regular service variables; `railway.toml`'s `buildArgs` config automatically forwards `LIFF_ID` into the Docker build — no special build-variable setup needed
4. **First deploy** — push to master; Railway builds image (Node stage then Python stage), runs `alembic upgrade head`, starts uvicorn; verify `GET /health` returns `{"status": "ok"}`
5. **Verify end-to-end** — add the bot on LINE, send a message, confirm LIFF opens at `/liff`, confirm admin dashboard loads at `/dashboard/`
6. **Cloning for a new studio** — clone the repo, create a new Railway project, create a new LINE channel, repeat from step 2

---

## What is NOT in scope

- LINE rich menu creation via API (manual console setup)
- LIFF UI design pass (separate phase)
- Smoke test script
- Monitoring / alerting setup
