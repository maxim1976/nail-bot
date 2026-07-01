from __future__ import annotations

from sqlalchemy import select

from app.db import session_scope
from app.line_client import ReplyMessage
from app.models import Service


def build_services_carousel(base_url: str) -> ReplyMessage | None:
    with session_scope() as s:
        rows = (
            s.execute(
                select(
                    Service.name,
                    Service.price,
                    Service.duration_min,
                    Service.image_url,
                )
                .where(Service.in_carousel == True)  # noqa: E712
                .where(Service.is_available == True)  # noqa: E712
                .order_by(Service.sort_order)
                .limit(10)
            )
            .all()
        )

    if not rows:
        return None

    bubbles = []
    for name, price, duration_min, image_url in rows:
        bubble: dict = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "xs",
                "contents": [
                    {
                        "type": "text",
                        "text": name,
                        "weight": "bold",
                        "size": "xl",
                        "wrap": True,
                    },
                    {
                        "type": "text",
                        "text": f"NT${price:,}",
                        "size": "md",
                        "color": "#c0748a",
                        "weight": "bold",
                    },
                    {
                        "type": "text",
                        "text": f"{duration_min} 分鐘",
                        "size": "xs",
                        "color": "#888888",
                    },
                ],
            },
        }

        if image_url:
            resolved = (
                f"{base_url.rstrip('/')}{image_url}"
                if image_url.startswith("/")
                else image_url
            )
            bubble["hero"] = {
                "type": "image",
                "url": resolved,
                "size": "full",
                "aspectRatio": "20:13",
                "aspectMode": "cover",
            }

        bubbles.append(bubble)

    return ReplyMessage.flex(
        alt_text="本月優惠",
        contents={"type": "carousel", "contents": bubbles},
    )
