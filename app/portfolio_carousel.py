from __future__ import annotations

from sqlalchemy import select

from app.db import session_scope
from app.line_client import ReplyMessage
from app.models import PortfolioItem, Service


def build_portfolio_carousel() -> ReplyMessage | None:
    with session_scope() as s:
        rows = (
            s.execute(
                select(PortfolioItem, Service.name.label("svc_name"))
                .outerjoin(Service, PortfolioItem.service_id == Service.id)
                .where(PortfolioItem.is_visible == True)  # noqa: E712
                .order_by(PortfolioItem.sort_order)
                .limit(12)
            )
            .all()
        )

    if not rows:
        return None

    bubbles = []
    for item, svc_name in rows:
        body_contents: list[dict] = [
            {"type": "text", "text": item.title, "weight": "bold", "size": "sm", "wrap": True}
        ]
        if svc_name:
            body_contents.append(
                {"type": "text", "text": svc_name, "size": "xs", "color": "#888888"}
            )

        bubbles.append({
            "type": "bubble",
            "hero": {
                "type": "image",
                "url": item.image_url,
                "size": "full",
                "aspectRatio": "1:1",
                "aspectMode": "cover",
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "xs",
                "contents": body_contents,
            },
        })

    return ReplyMessage.flex(
        alt_text="作品集",
        contents={"type": "carousel", "contents": bubbles},
    )
