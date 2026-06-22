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
