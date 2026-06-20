from __future__ import annotations

from app.db import session_scope
from app.models import PortfolioItem, Service
from app.portfolio_carousel import build_portfolio_carousel


def _add_item(title: str, *, is_visible: bool = True, sort_order: int = 0) -> None:
    with session_scope() as s:
        s.add(PortfolioItem(
            title=title,
            image_url=f"https://cdn.example.com/{title}.jpg",
            service_id=None,
            is_visible=is_visible,
            sort_order=sort_order,
        ))


def test_returns_none_when_no_items():
    result = build_portfolio_carousel()
    assert result is None


def test_returns_flex_message_with_carousel():
    _add_item("Work A")
    _add_item("Work B")

    result = build_portfolio_carousel()
    assert result is not None
    assert result.payload["type"] == "flex"
    assert result.payload["contents"]["type"] == "carousel"
    bubbles = result.payload["contents"]["contents"]
    assert len(bubbles) == 2


def test_excludes_invisible_items():
    _add_item("Hidden", is_visible=False)
    _add_item("Visible", is_visible=True)

    result = build_portfolio_carousel()
    assert result is not None
    bubbles = result.payload["contents"]["contents"]
    titles = [b["body"]["contents"][0]["text"] for b in bubbles]
    assert "Visible" in titles
    assert "Hidden" not in titles


def test_caps_at_12_bubbles():
    for i in range(15):
        _add_item(f"Work {i}", sort_order=i)

    result = build_portfolio_carousel()
    assert result is not None
    bubbles = result.payload["contents"]["contents"]
    assert len(bubbles) == 12


def test_bubble_includes_service_name():
    import uuid
    svc_id = uuid.uuid4()
    with session_scope() as s:
        s.add(Service(
            id=svc_id, name="凝膠美甲", name_en="Gel",
            name_tl="", name_id="", name_vi="",
            duration_min=60, price=500,
        ))
        s.flush()
        s.add(PortfolioItem(
            title="Gel work",
            image_url="https://cdn.example.com/gel.jpg",
            service_id=svc_id,
            is_visible=True,
        ))

    result = build_portfolio_carousel()
    assert result is not None
    bubble = result.payload["contents"]["contents"][0]
    body_texts = [c["text"] for c in bubble["body"]["contents"]]
    assert "凝膠美甲" in body_texts
