# Services Carousel — Design Spec
_Date: 2026-07-01_

## Goal

When a user taps "本月優惠" in the rich menu, the bot replies with a Flex Message carousel
showing services flagged `in_carousel=True` in the admin dashboard.

## Changes

### 1. `app/services_carousel.py` (new)

Mirrors `portfolio_carousel.py`. Queries `Service` where `in_carousel=True AND is_available=True`,
ordered by `sort_order`, up to 10 rows.

Each bubble:
- **Hero image** — included only if `image_url` is set (`aspectRatio: 20:13`, `aspectMode: cover`)
- **Body** — service `name` (bold, xl), price as `NT$X,XXX` (pink accent), duration as `XX 分鐘` (grey, xs)
- **No footer button** — keeps cards clean; booking is via the 預約 rich menu button

Returns `ReplyMessage.flex(alt_text="本月優惠", contents=carousel)` or `None` if no rows.

### 2. `app/replies.py`

Add: `SERVICES_TRIGGER = "本月優惠"`

### 3. `app/event_router.py`

Import `SERVICES_TRIGGER` and `build_services_carousel`. Add handler before the agent call
(same pattern as `PORTFOLIO_TRIGGER`):

```python
if text == SERVICES_TRIGGER:
    carousel = build_services_carousel()
    if carousel:
        line_client.reply(reply_token=reply_token, messages=[carousel])
    else:
        line_client.reply(reply_token=reply_token, messages=[ReplyMessage.text("目前尚無本月優惠，敬請期待！")])
    return
```

This handler fires regardless of `current_agent` — no persona selection required to see offers.

### 4. `app/line_client.py`

Change rich menu area 2 action text from `"作品集"` → `"本月優惠"`:

```python
{"type": "message", "label": "本月優惠", "text": "本月優惠"}
```

The rich menu must be re-created after this change (run `scripts/setup_rich_menu.py`).

## Out of scope

- No booking button on cards (user books via 預約 rich menu button)
- No follow-event auto-send (carousel is on-demand via rich menu tap)
- No image upload flow (images added later via admin dashboard)
