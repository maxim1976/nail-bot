# Nail Bot — Hualienvibe Design Spec
_2026-06-20_

## What We're Building

A LINE-based appointment booking system for a home-visit nail technician, targeting migrant workers in Taiwan. Customers book in their native language (zh/en/tl/id/vi) via LINE. The nail tech manages her schedule, services, and portfolio via a web admin dashboard.

Sold as a done-for-you product on PRO360/Tasker at NT$18,000+ per studio. Each customer gets a cloned, single-tenant deployment on Railway.

The bot ships with a built-in **sales agent** persona that demos the product to prospective buyers. When sold, the sales persona is removed and the bot is redeployed as a live booking assistant.

---

## Stack

| Layer | Tech |
|---|---|
| Backend | FastAPI + Python 3.12 + PostgreSQL + SQLAlchemy + Alembic |
| AI | Claude `claude-sonnet-4-6` via Anthropic SDK |
| Messaging | LINE Messaging API + LIFF |
| Frontend LIFF | React 19 + TypeScript + Tailwind v4 + Vite |
| Frontend Admin | Plain HTML + Alpine.js |
| Hosting | Railway (auto-deploy on push to master) |

Mirrors bento-bot architecture exactly. Follow all bento-bot conventions: `app/api/` for REST endpoints, TDD (failing test first), commits to master, Alembic for all migrations.

---

## Data Models

### Carried over from bento-bot (with modifications)
- **`User`** — `line_user_id` (PK), `display_name`, `current_agent_key` (booking_assistant / sales_agent), `preferred_language` (zh/en/tl/id/vi, default zh), `followed_at`, `last_seen_at`, `is_blocked`
- **`Conversation`**, **`Message`** — identical to bento-bot (conversation history per user/agent pair)
- **`UsageCounter`**, **`DailyCost`** — identical to bento-bot (rate limiting + cost kill switch)

### New models

**`StudioProfile`** — single-row config table
- `studio_name`, `owner_name`
- `address`, `phone`, `instagram`
- `cancellation_policy` (text)
- `aftercare_notes` (text)
- `ai_persona_notes` (text — free-form instructions for the booking_assistant tone/behaviour)
- `owner_line_user_id` (for push notifications to nail tech)

**`Service`** — nail services offered
- `id` (UUID PK), `name`, `name_en`, `name_tl`, `name_id`, `name_vi`
- `description` (zh, AI handles translation in chat)
- `agent_notes` (internal context for AI, not shown to customers)
- `duration_min` (Integer), `price` (Integer, NTD)
- `image_url`, `category`, `is_available`, `in_carousel`, `sort_order`
- `created_at`, `updated_at`

**`WeeklyTemplate`** — recurring availability, one row per active day
- `dow` (Integer, 0=Mon … 6=Sun), `start_time` (Time), `end_time` (Time)
- `slot_duration_min` (Integer, e.g. 90)
- `is_active` (Boolean)

**`DateOverride`** — exceptions to the weekly template
- `date` (Date PK), `is_blocked` (Boolean)
- `custom_start` (Time, nullable), `custom_end` (Time, nullable)
- If `is_blocked=true`: no slots that day. If false + custom times set: use those instead of weekly template.

**`Appointment`** — a booked slot
- `id` (UUID PK), `line_user_id` (FK), `service_id` (FK)
- `scheduled_at` (DateTime with tz), `duration_min`
- `status` (confirmed / cancelled / completed) — auto-set to confirmed on booking; nail tech updates to completed/cancelled via admin
- `customer_name`, `notes`
- `reminder_sent` (Boolean, default false — tracks 24h reminder)
- `created_at`, `updated_at`

**`PortfolioItem`** — gallery photos
- `id` (UUID PK), `title`, `image_url`
- `service_id` (FK, nullable — optional link to a service)
- `sort_order`, `is_visible`
- `created_at`

---

## LINE Bot Flow

### New user follows bot
1. Welcome message in Chinese (default) with two quick-reply buttons:
   - 💅 我要預約（I want to book）
   - 🏪 了解此服務（Learn about this service）
2. Choice saves `current_agent_key` = `booking_assistant` or `sales_agent`

### Existing user sends a message
1. Claude infers language from message content → responds in that language, saves `preferred_language` (no separate detection library)
2. Language switch detected naturally by Claude ("English please", "改中文", "Tagalog po") → saves new `preferred_language`
3. Portfolio keywords (作品 / gallery / nail art etc.) → send Flex Message carousel (top `in_carousel` PortfolioItems) + "see all" button linking to LIFF gallery
4. Otherwise → route to `booking_assistant` or `sales_agent` per `current_agent_key`

### Booking flow (LIFF `/liff/book`)
1. Service picker — cards with photo, multilingual name, duration, price
2. Date picker — calendar showing only days with available slots
3. Time slot picker — available slots for selected date (booked slots hidden)
4. Confirm screen — summary + customer name/notes → "Confirm Booking"
5. On submit: POST to backend → create `Appointment` (status=pending) → push confirmation to customer + push notification to nail tech

### Appointment management via AI
- "What are my bookings?" → AI calls `get_my_appointments()`, replies in customer's language
- "I want to cancel" → AI confirms which appointment, calls `cancel_appointment(id)`, notifies nail tech

---

## LIFF App

Single Vite + React 19 + Tailwind v4 app, two routes:

**`/liff/book`** — booking flow (5 screens as above)

**`/liff/gallery`** — portfolio gallery
- Photo grid, filterable by service category
- Tap photo → full-screen with service name and price
- "Book this style" → navigate to `/liff/book` with service pre-selected

**Design language:** warm beige `#F4EDE5` background, Bodoni Moda serif headings, `#241914` dark text, `#B86E78` accent rose, `#A6864F` gold. Matches the landing page prototype.

---

## Admin Dashboard

Plain HTML + Alpine.js, five tabs:

**Schedule**
- Weekly template: toggle each day, set start/end time, slot duration
- Date override calendar: block specific dates or set custom hours

**Services**
- CRUD: name (all 5 languages), duration, price, category, image, `agent_notes`
- Toggle `is_available` and `in_carousel`
- Drag-to-reorder

**Portfolio**
- Upload photos, link to service, set sort order, toggle visibility
- Preview of LIFF gallery layout

**Appointments**
- List: date, time, service, customer name, status
- Mark as confirmed / completed / cancelled
- Filter by date range or status

**Studio Profile**
- Studio name, owner name, address, phone, Instagram
- Cancellation policy, aftercare notes, `ai_persona_notes`
- Owner LINE user ID

---

## Notification System

**Booking confirmation** (immediate on booking)
- → Customer: service, date, time, price, cancellation policy — in `preferred_language`
- → Nail tech: customer name, service, date, time, notes

**24h reminder** (cron, runs hourly)
- Find appointments where `scheduled_at` is 23–25h from now and `reminder_sent = false`
- Send reminder to customer in `preferred_language`, set `reminder_sent = true`

**Daily morning summary** (cron, runs 08:00 Asia/Taipei)
- Push to nail tech: today's confirmed appointments (time, service, customer name)
- If none: "You have a free day today 🌸"

Implemented in `app/cron/` using APScheduler (same pattern as bento-bot retention cron).

---

## AI Agent — Personas

### `booking_assistant`

System prompt context (loaded at runtime):
- `StudioProfile` fields
- All active `Service` records with `agent_notes`
- `preferred_language` → "always reply in [language]"

Claude tools:
- `get_my_appointments()` — customer's upcoming bookings
- `cancel_appointment(appointment_id)` — mark cancelled, notify nail tech
- `get_services()` — full service list with prices and durations
- `get_available_slots(date)` — for conversational availability queries

Behaviour: answers FAQ about services/prices/location/aftercare, guides customers to LIFF for booking, handles cancellations conversationally, always responds in detected language.

### `sales_agent`

System prompt contains hardcoded product knowledge:
- What Hualienvibe is, who it's for, full feature list
- Pricing (NT$18,000+), delivery time (3–7 days), what's included
- How booking, portfolio, multilingual AI, and admin dashboard work
- Call to action: contact the seller directly on LINE (ID injected from `SELLER_LINE_ID` env var)

No DB tools — all knowledge is static in the prompt.

Behaviour: answers questions from prospective buyers, sells the product, explains the tech in plain language. Responds in detected language. Removed entirely when bot is sold and deployed for a real studio.

---

## Environment Variables

```
# LINE
LINE_CHANNEL_ACCESS_TOKEN=
LINE_CHANNEL_SECRET=
LIFF_ID=
RICH_MENU_ID=

# Anthropic
ANTHROPIC_API_KEY=

# Database
DATABASE_URL=

# App config
OWNER_LINE_USER_ID=
SELLER_LINE_ID=
RATE_LIMIT_HOUR=10
RATE_LIMIT_DAY=30
HISTORY_TURNS=10
DAILY_COST_KILL_USD=5.00
TZ=Asia/Taipei
```

---

## Project Layout

```
app/
  api/
    admin/          auth, schedule, services, portfolio, appointments, stats
    appointments.py public appointment endpoints (for LIFF)
    services.py     public service list (for LIFF)
    schemas.py
  cron/
    reminders.py    24h customer reminder job
    summary.py      daily morning summary job
  personas/
    booking_assistant.py
    sales_agent.py
    _base.py
  models.py
  agent_service.py
  event_router.py
  line_client.py
  webhook.py
  main.py
  config.py
  db.py

frontend/
  liff/             React booking + gallery app
  admin/            HTML + Alpine.js dashboard
  landing/          Existing prototype (static)

tests/
alembic/
docs/
scripts/
```
