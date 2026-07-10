# 民宿 / Lodging demo — implementation plan

Goal: add a **whole-house / room B&B (民宿 / 包棟) booking demo** on top of this
codebase, to show prospects in the lodging niche. This is the missing "hotel demo"
for outreach. Keep it a **separate booking domain** — do NOT break the existing
nail-studio flow (`Service` / `Appointment` / `slots.py` stay as they are).

The core difference from the nail flow:
- Nail booking = a **time slot inside one day** (`scheduled_at` + `duration_min`).
- Lodging booking = a **date range** (check-in → check-out, N nights) for a **room
  type with limited inventory**, priced by **day-type** (weekday / peak / holiday)
  and guest count.

Two-step product framing (build step 1 fully; stub step 2):
- **Step 1 (MVP, build this):** AI answers FAQ + **instant price quote** for
  "N people, dates X–Y" and checks availability.
- **Step 2 (later):** full booking with confirmation + owner notification. Wire the
  tool but a simple confirmed `Booking` row + LINE push is enough for the demo.

---

## 1. New data models (`app/models.py`)

Add alongside the existing models (new tables, no changes to nail tables):

### `RoomType`  (analog of `Service`)
- `id: UUID pk`
- `name: str` (e.g. "四人房", "包棟-6人")
- `name_en: str = ""`
- `description: str = ""`
- `capacity: int` — base guests included
- `max_capacity: int` — with extra beds
- `quantity: int = 1` — **inventory**: how many identical units exist (包棟 = 1)
- `price_weekday: int` — 平日
- `price_peak: int` — 旺日 (Fri, Sun, day before/after a run of holidays)
- `price_holiday: int` — 連續假日 (Sat, national holidays)
- `extra_bed_price: int = 800`
- `max_extra_beds: int = 0`
- `is_available: bool = True`
- `sort_order: int = 0`
- timestamps like `Service`

### `Booking`  (analog of `Appointment`)
- `id: UUID pk`
- `line_user_id: FK users.line_user_id`
- `room_type_id: FK room_types.id`
- `check_in: Date`  (first night)
- `check_out: Date` (checkout morning; nights = check_out - check_in)
- `guests: int`
- `extra_beds: int = 0`
- `total_price: int`
- `status: str = "confirmed"`  (confirmed | cancelled | completed)
- `customer_name: str = ""`
- `notes: str | None`
- `reminder_sent: bool = False`
- timestamps

### `HolidayDate`  (drives day-type classification)
- `date: Date pk`
- `day_type: str`  — one of `"peak"` | `"holiday"` (only store overrides; everything
  else is classified by weekday rule below)

Then: `alembic revision -m "add lodging models" --autogenerate && alembic upgrade head`.

---

## 2. Day-type + pricing (`app/lodging_pricing.py`, new)

Rule (matches 山里暖陽's stated policy — good realistic default):
- **旺日 / peak:** 週五 (Fri), 週日 (Sun)
- **連續假日 / holiday:** 週六 (Sat), national holidays
- **平日 / weekday:** everything else
- `HolidayDate` overrides the weekday rule for a given date.

```python
def classify_day(d: date, session) -> str:  # "weekday" | "peak" | "holiday"
    override = session.get(HolidayDate, d)
    if override:
        return override.day_type
    dow = d.weekday()          # 0=Mon … 6=Sun
    if dow == 5:               # Sat
        return "holiday"
    if dow in (4, 6):          # Fri, Sun
        return "peak"
    return "weekday"

def price_for_night(room_type, day_type: str) -> int: ...

def quote_stay(room_type, check_in, check_out, guests, extra_beds, session) -> dict:
    # iterate each night in [check_in, check_out), sum price_for_night by classify_day,
    # add extra_beds * room_type.extra_bed_price * nights,
    # return {"nights": n, "per_night": [...], "extra_bed_total": ..., "total": ...}
```

Validation: reject if `guests > max_capacity`, if `check_out <= check_in`, if
`extra_beds > max_extra_beds`, if `guests > capacity` require enough extra beds.

---

## 3. Availability (`app/lodging_slots.py`, new — mirrors `slots.py`)

```python
def available_units(room_type_id, check_in, check_out, session) -> int:
    # count overlapping confirmed Bookings for this room_type where
    #   booking.check_in < check_out AND booking.check_out > check_in
    # return room_type.quantity - overlapping_count  (>=0)

def is_available(room_type_id, check_in, check_out, session) -> bool:
    return available_units(...) > 0
```

Overlap test is the standard half-open interval overlap (same logic as the nail
`overlaps()` in `slots.py`, but on dates, half-open so back-to-back stays don't
collide).

---

## 4. Agent tools (`app/lodging_tools.py`, new — mirrors `agent_tools.py`)

Expose these Claude tools (same `execute_tool(name, tool_input, *, line_user_id)`
dispatch pattern as `agent_tools.py`):

- `get_room_types` → list rooms with capacity + the three prices.
- `quote_stay` → args `room_type_id, check_in (YYYY-MM-DD), check_out, guests,
  extra_beds?` → returns the `quote_stay()` breakdown. **This is the money tool** —
  it answers "多少錢" instantly.
- `check_availability` → args `check_in, check_out, guests?` → which room types are
  free for that range.
- `book_stay` → args `room_type_id, check_in, check_out, guests, customer_name,
  extra_beds?, notes?` → re-check availability, compute total via `quote_stay`,
  insert `Booking(status="confirmed")`, push a LINE confirmation + owner notification
  (reuse the pattern in `_book_appointment` / `app/notifications.py`).
- `get_my_bookings` / `cancel_booking` → analogs of the appointment versions.

---

## 5. Persona (`app/personas/lodging_assistant.py`, new)

Copy `booking_assistant` as the template. `body_prompt` should:
- Introduce as the 民宿 official LINE assistant.
- Know it must **collect: dates (check-in/out), number of guests** before quoting.
- Always call `quote_stay` for price questions rather than guessing numbers.
- State house rules concisely (e.g. 加人加床最多 N 床/每床 800；12 人以下包棟無加床；
  兩歲以下嬰兒不計人數) — put these in `StudioProfile.ai_persona_notes` / room notes.
- Register the persona key in whatever registry `booking_assistant` is registered in,
  and make sure `event_router.py` / `PERSONA_SELECT` can select it (add a quick-reply
  keyword, e.g. 訂房).

Wire `generate_agent_reply` to pass `LODGING_TOOLS` when `agent_key ==
"lodging_assistant"` (parallel to how `booking_assistant` gets `BOOKING_TOOLS`).

---

## 6. Seed data (demo) — `scripts/seed_lodging_demo.py` (new)

Use 山里暖陽's real price table so the demo feels real:

| 適合人數 | 房型 | 平日 | 旺日 | 連續假日 |
|---|---|---|---|---|
| 6  | 四人*1+雙人*1 | 10500 | 18000 | 21000 |
| 8  | 四人*2 | 12000 | 18000 | 21000 |
| 10 | 四人*2+雙人*1 | 13500 | 18000 | 21000 |
| 12 | 四人*3 | 15000 | 18000 | 21000 |
| 16 | 四人*3+雙人*2 | 18000 | 21000 | 24000 |

Rules: 加人加床最多 5 床、每床 800；12 人以下包棟無加床；2 歲以下嬰兒不計人數。
`extra_bed_price=800`, `max_extra_beds=5`. `quantity=1` per 包棟 unit.

---

## 7. Tests (`tests/`, mirror existing style)

testcontainers Postgres like the rest of the suite. Cover:
- `test_lodging_pricing.py` — weekday/peak/holiday classification incl. `HolidayDate`
  override; multi-night mixed quote; extra-bed math; over-capacity rejection.
- `test_lodging_slots.py` — inventory overlap: `quantity=1` blocks overlapping range,
  allows back-to-back (check_out == next check_in), allows non-overlapping.
- `test_lodging_tools.py` — `quote_stay`, `check_availability`, `book_stay`
  happy-path + double-book rejection.

Run: `pytest tests/test_lodging_*.py` (Docker/Colima must be running — see repo
CLAUDE.md).

---

## 8. Out of scope for the demo (note, don't build)
- LIFF booking UI (chat-only quote+book is enough to demo).
- Google Calendar sync for stays (nail flow keeps it; skip for lodging MVP).
- Payments / deposits.

## Definition of done
On LINE, selecting the 訂房 persona, a user can ask "6 個人 8/15 到 8/17 多少錢"
and get a correct itemised quote, ask what's free for those dates, and book — with a
LINE confirmation pushed back. Existing nail tests still green.
