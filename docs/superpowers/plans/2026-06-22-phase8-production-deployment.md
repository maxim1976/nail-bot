# Phase 8: Production Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make nail-bot deployable from zero on Railway with a single Docker image that includes both the Python backend and the built LIFF React frontend.

**Architecture:** A two-stage Dockerfile adds a `node:20-slim` builder that compiles the LIFF app (baking `LIFF_ID` into the bundle), then copies the `dist/` into the Python runtime image. `railway.toml` tells Railway to use this Dockerfile and forward `LIFF_ID` as a build arg. `.env.example` and `docs/deploy-checklist.md` document the zero-to-live path for new studio deployments.

**Tech Stack:** Docker multi-stage build, Node 20 + Vite, Python 3.12 + FastAPI, Railway, LINE Developers Console, bcrypt (for admin password hash generation)

## Global Constraints

- `LIFF_ID` is the single variable for the LIFF app ID — no separate `VITE_LIFF_ID` for the user; the Dockerfile maps it internally with `ARG LIFF_ID` → `ENV VITE_LIFF_ID=$LIFF_ID`
- No new Python dependencies
- No changes to `app/main.py` — the conditional `StaticFiles` mount at `/liff` is already correct
- Commits go to master directly

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `Dockerfile` | Modify | Add Node 20 build stage; copy dist into Python runtime |
| `tests/test_liff_ui.py` | Create | Verify `/liff/index.html` is served (mirrors `test_admin_ui.py` pattern) |
| `railway.toml` | Create | Builder = DOCKERFILE, forward LIFF_ID as build arg, health check |
| `.env.example` | Create | All env vars with one-line comments |
| `docs/deploy-checklist.md` | Create | Step-by-step first-deploy guide |

---

### Task 1: Dockerfile multi-stage build + LIFF serving test

**Files:**
- Modify: `Dockerfile`
- Create: `tests/test_liff_ui.py`

**Interfaces:**
- Produces: Docker image with `/liff` served from the built React app; `GET /liff/index.html` returns 200 HTML

- [ ] **Step 1: Write the failing test**

Create `tests/test_liff_ui.py`:

```python
import os

os.environ.setdefault("ADMIN_JWT_SECRET", "test-secret-key-for-testing-only-32ch")

from fastapi.testclient import TestClient

from app.main import app


def test_liff_serves_html():
    client = TestClient(app)
    res = client.get("/liff/index.html")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]


def test_liff_root_serves_html():
    client = TestClient(app)
    res = client.get("/liff/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
```

- [ ] **Step 2: Run tests to verify current state**

```
pytest tests/test_liff_ui.py -v
```

Expected: both tests PASS — `frontend/liff/dist/` is already committed to the repo and `main.py`'s conditional mount picks it up.

(If they fail with 404, the dist is missing — run `cd frontend/liff && npm ci && npm run build` first, then re-run.)

- [ ] **Step 3: Update the Dockerfile**

Replace the full contents of `Dockerfile` with:

```dockerfile
# syntax=docker/dockerfile:1.7

# ── Stage 1: build LIFF frontend ─────────────────────────────────────────────
FROM node:20-slim AS node-builder
WORKDIR /app/frontend/liff
COPY frontend/liff/package*.json ./
RUN npm ci
COPY frontend/liff/ ./
ARG LIFF_ID
ENV VITE_LIFF_ID=$LIFF_ID
RUN npm run build

# ── Stage 2: Python runtime ───────────────────────────────────────────────────
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir -U pip
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY --from=node-builder /app/frontend/liff/dist ./frontend/liff/dist

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

- [ ] **Step 4: Verify the Docker build (if Docker is available locally)**

```bash
docker build --build-arg LIFF_ID=test-liff-id -t nail-bot-test .
```

Expected: build completes without errors; Stage 1 produces a `dist/` directory and Stage 2 copies it in.

If Docker is not available locally, skip this step — Railway will validate the build on first deploy.

- [ ] **Step 5: Run full test suite to confirm no regressions**

```
pytest --tb=short -q
```

Expected: all prior tests pass (137 total + 2 new = 139).

- [ ] **Step 6: Commit**

```bash
git add Dockerfile tests/test_liff_ui.py
git commit -m "feat(p8/t1): multi-stage Dockerfile with Node LIFF build stage"
```

---

### Task 2: `railway.toml`

**Files:**
- Create: `railway.toml` (repo root)

**Interfaces:**
- Produces: Railway reads this file to know to use the Dockerfile builder, forward `LIFF_ID` as a build arg, and health-check `/health`

- [ ] **Step 1: Create `railway.toml`**

Create `railway.toml` at the repo root:

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

- [ ] **Step 2: Verify the TOML is valid**

```bash
python3 -c "import tomllib; tomllib.loads(open('railway.toml').read()); print('valid')"
```

Expected: `valid`

- [ ] **Step 3: Commit**

```bash
git add railway.toml
git commit -m "feat(p8/t2): add railway.toml with Dockerfile builder and health check"
```

---

### Task 3: `.env.example` and deploy checklist

**Files:**
- Create: `.env.example` (repo root)
- Create: `docs/deploy-checklist.md`

**Interfaces:**
- Produces: documentation for zero-to-live Railway deployment; `.env.example` covers every field in `app/config.py`

- [ ] **Step 1: Create `.env.example`**

Create `.env.example` at the repo root:

```
# ── LINE ─────────────────────────────────────────────────────────────────────
LINE_CHANNEL_ACCESS_TOKEN=   # LINE Developers → Messaging API → Channel access token
LINE_CHANNEL_SECRET=         # LINE Developers → Messaging API → Channel secret
LIFF_ID=                     # LINE Developers → LIFF → App ID (also used as Docker build arg)
RICH_MENU_ID=                # LINE Developers → Messaging API → Rich menus

# ── Anthropic ─────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY=           # console.anthropic.com
ANTHROPIC_MODEL=claude-sonnet-4-6

# ── Database ─────────────────────────────────────────────────────────────────
DATABASE_URL=                # Set automatically by Railway PostgreSQL plugin

# ── Admin dashboard ───────────────────────────────────────────────────────────
ADMIN_JWT_SECRET=            # Random 32+ char string: openssl rand -hex 32
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=         # bcrypt hash: python3 -c "import bcrypt; print(bcrypt.hashpw(b'yourpassword', bcrypt.gensalt()).decode())"
ADMIN_BASE_URL=              # Your Railway domain, e.g. https://nail-bot.up.railway.app

# ── App config ────────────────────────────────────────────────────────────────
OWNER_LINE_USER_ID=          # Your LINE user ID — receives daily summary + rate-limit alerts
SELLER_LINE_ID=              # Your LINE ID shown to sales_agent prospects (e.g. @yourid)
RATE_LIMIT_HOUR=10
RATE_LIMIT_DAY=30
HISTORY_TURNS=20
DAILY_COST_CEILING_USD=5.00
TZ=Asia/Taipei
```

- [ ] **Step 2: Verify `.env.example` covers every required field in `app/config.py`**

Run this and confirm each required field (those with no default) appears in `.env.example`:

```bash
python3 -c "
required = ['line_channel_secret', 'line_channel_access_token', 'anthropic_api_key', 'admin_jwt_secret', 'database_url']
example = open('.env.example').read().lower()
for f in required:
    key = f.upper()
    status = 'OK' if key.lower() in example else 'MISSING'
    print(f'{status}: {key}')
"
```

Expected: all five print `OK`.

- [ ] **Step 3: Create `docs/deploy-checklist.md`**

Create `docs/deploy-checklist.md`:

```markdown
# Nail Bot — Deployment Checklist

A step-by-step guide to deploy a new nail-bot instance from zero. Follow in order.

---

## 1. Prerequisites

- LINE Developer account: https://developers.line.biz
- Anthropic account: https://console.anthropic.com
- Railway account: https://railway.app
- Git access to the nail-bot repository
- Node 20 and Python 3.12 installed locally (for local verification only)

---

## 2. LINE Setup

### 2a. Create a Messaging API channel

1. Go to LINE Developers Console → **Create a new provider** (or use an existing one)
2. Create a **Messaging API** channel
3. Note down:
   - **Channel secret** → `LINE_CHANNEL_SECRET`
   - **Channel access token** (long-lived) → `LINE_CHANNEL_ACCESS_TOKEN`

### 2b. Create a LIFF app

1. In the same channel, go to the **LIFF** tab → **Add**
2. Set:
   - Size: **Full**
   - Endpoint URL: `https://<your-railway-domain>/liff/` _(fill in after step 3)_
3. Note down the **LIFF ID** → `LIFF_ID`

### 2c. Create a Rich Menu

1. In LINE Developers Console → Messaging API → **Rich menu** → **Create**
2. Design the menu (at minimum: a "Book" button linking to your LIFF URL)
3. Set as default menu and publish
4. Note down the **Rich menu ID** → `RICH_MENU_ID`

### 2d. Set webhook URL _(after Railway deploy in step 4)_

1. Messaging API → **Webhook URL**: `https://<your-railway-domain>/webhook`
2. Enable **Use webhook**
3. Click **Verify** — expect a 200 response

---

## 3. Railway Project Setup

1. Go to https://railway.app → **New Project** → **Deploy from GitHub repo**
2. Select the nail-bot repository
3. Railway detects `railway.toml` and uses the Dockerfile builder automatically

### 3a. Add PostgreSQL

1. In the Railway project → **New** → **Database** → **PostgreSQL**
2. Railway automatically sets `DATABASE_URL` in your service's environment

### 3b. Set environment variables

In your Railway web service → **Variables**, add every variable from `.env.example`.

**Generate the values you need:**

```bash
# Admin JWT secret (run locally)
openssl rand -hex 32

# Admin password hash (run locally, replace 'yourpassword')
python3 -c "import bcrypt; print(bcrypt.hashpw(b'yourpassword', bcrypt.gensalt()).decode())"
```

**Important:** `LIFF_ID` must be set here as a regular service variable. `railway.toml`'s `buildArgs = ["LIFF_ID"]` automatically forwards it into the Docker build so Vite can bake it into the JavaScript bundle — no separate build-variable setup required.

---

## 4. First Deploy

1. Push to `master` — Railway triggers an automatic deploy
2. Watch the build logs: Stage 1 (Node) compiles the LIFF, Stage 2 (Python) installs dependencies
3. After deploy, Railway runs `alembic upgrade head` then starts uvicorn
4. Verify the service is live:

```bash
curl https://<your-railway-domain>/health
# Expected: {"status": "ok"}
```

### 4a. Update LIFF endpoint URL

Now that your Railway domain is known:
1. LINE Developers → LIFF → edit your app
2. Set Endpoint URL to `https://<your-railway-domain>/liff/`

---

## 5. End-to-End Verification

- [ ] Add the LINE bot (scan the QR code in LINE Developers Console)
- [ ] Send a message — bot should respond (follow event sends welcome + quick replies)
- [ ] Tap "我要預約" — LIFF booking flow opens at `/liff/`
- [ ] Admin dashboard loads at `https://<your-railway-domain>/dashboard/`
- [ ] Log in with `ADMIN_USERNAME` / your chosen password

---

## 6. Cloning for a New Studio

To deploy a second studio instance:

1. Clone or fork the nail-bot repository
2. Create a new Railway project pointing to the new repo
3. Create a **new LINE channel** for the studio (separate from any existing bot)
4. Repeat steps 2–5 above with the new channel's credentials
5. Populate all env vars for the new studio (different `LINE_CHANNEL_ACCESS_TOKEN`, `LINE_CHANNEL_SECRET`, `LIFF_ID`, `RICH_MENU_ID`)

Each studio is fully isolated — separate Railway project, separate PostgreSQL database, separate LINE channel.
```

- [ ] **Step 4: Run full test suite to confirm no regressions**

```
pytest --tb=short -q
```

Expected: 139 tests pass.

- [ ] **Step 5: Commit**

```bash
git add .env.example docs/deploy-checklist.md
git commit -m "feat(p8/t3): add .env.example and deploy checklist"
```

---

## Self-Review

**Spec coverage:**
- ✅ Dockerfile multi-stage build (Task 1)
- ✅ `railway.toml` with builder, build args, health check, restart policy (Task 2)
- ✅ `.env.example` covering all fields in `config.py` (Task 3)
- ✅ Deploy checklist: prerequisites, LINE setup, Railway project, first deploy, E2E verification, cloning for new studio (Task 3)
- ✅ Single `LIFF_ID` variable — no `VITE_LIFF_ID` for users (enforced in Dockerfile and `.env.example`)
- ✅ `admin_password_hash` generation command documented (missed in original design, caught here)
- ✅ `admin_base_url` documented (needed for admin dashboard to function)

**No placeholders, no TBDs.**
