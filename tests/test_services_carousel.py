from __future__ import annotations

import uuid

from app.db import session_scope
from app.models import Service
from app.services_carousel import build_services_carousel

BASE = "https://example.com"


def _add_service(
    name: str,
    *,
    price: int = 1200,
    duration_min: int = 90,
    in_carousel: bool = True,
    is_available: bool = True,
    image_url: str | None = None,
    sort_order: int = 0,
) -> None:
    with session_scope() as s:
        s.add(Service(
            id=uuid.uuid4(),
            name=name,
            name_en="",
            name_tl="",
            name_id="",
            name_vi="",
            duration_min=duration_min,
            price=price,
            image_url=image_url,
            in_carousel=in_carousel,
            is_available=is_available,
            sort_order=sort_order,
        ))


def test_returns_none_when_no_services():
    result = build_services_carousel(BASE)
    assert result is None


def test_returns_flex_carousel():
    _add_service("日式光療凝膠", price=1200)
    _add_service("手繪彩繪設計", price=1800)

    result = build_services_carousel(BASE)
    assert result is not None
    assert result.payload["type"] == "flex"
    assert result.payload["altText"] == "本月優惠"
    assert result.payload["contents"]["type"] == "carousel"
    bubbles = result.payload["contents"]["contents"]
    assert len(bubbles) == 2


def test_excludes_not_in_carousel():
    _add_service("凝膠卸除", in_carousel=False)
    _add_service("日式光療凝膠", in_carousel=True)

    result = build_services_carousel(BASE)
    assert result is not None
    bubbles = result.payload["contents"]["contents"]
    assert len(bubbles) == 1
    assert bubbles[0]["body"]["contents"][0]["text"] == "日式光療凝膠"


def test_excludes_unavailable():
    _add_service("凝膠卸除", in_carousel=True, is_available=False)
    _add_service("日式光療凝膠", in_carousel=True, is_available=True)

    result = build_services_carousel(BASE)
    assert result is not None
    assert len(result.payload["contents"]["contents"]) == 1


def test_caps_at_10_bubbles():
    for i in range(12):
        _add_service(f"Service {i}", sort_order=i)

    result = build_services_carousel(BASE)
    assert result is not None
    assert len(result.payload["contents"]["contents"]) == 10


def test_bubble_body_shows_name_price_duration():
    _add_service("日式光療凝膠", price=1200, duration_min=90)

    result = build_services_carousel(BASE)
    assert result is not None
    bubble = result.payload["contents"]["contents"][0]
    body_texts = [c["text"] for c in bubble["body"]["contents"]]
    assert "日式光療凝膠" in body_texts
    assert "NT$1,200" in body_texts
    assert "90 分鐘" in body_texts


def test_no_hero_when_no_image():
    _add_service("日式光療凝膠", image_url=None)

    result = build_services_carousel(BASE)
    assert result is not None
    bubble = result.payload["contents"]["contents"][0]
    assert "hero" not in bubble


def test_hero_present_with_absolute_image_url():
    _add_service("日式光療凝膠", image_url="https://cdn.example.com/gel.jpg")

    result = build_services_carousel(BASE)
    assert result is not None
    bubble = result.payload["contents"]["contents"][0]
    assert bubble["hero"]["url"] == "https://cdn.example.com/gel.jpg"


def test_relative_image_url_resolved_to_absolute():
    _add_service("日式光療凝膠", image_url="/uploads/services/gel.jpg")

    result = build_services_carousel(BASE)
    assert result is not None
    bubble = result.payload["contents"]["contents"][0]
    assert bubble["hero"]["url"] == "https://example.com/uploads/services/gel.jpg"


def test_ordered_by_sort_order():
    _add_service("Third", sort_order=3)
    _add_service("First", sort_order=1)
    _add_service("Second", sort_order=2)

    result = build_services_carousel(BASE)
    assert result is not None
    bubbles = result.payload["contents"]["contents"]
    names = [b["body"]["contents"][0]["text"] for b in bubbles]
    assert names == ["First", "Second", "Third"]
