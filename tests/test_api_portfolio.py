from __future__ import annotations

import uuid
from fastapi.testclient import TestClient

from app.db import session_scope
from app.main import app
from app.models import PortfolioItem, Service

client = TestClient(app)


def _add_service(name: str, category: str = "general") -> uuid.UUID:
    svc_id = uuid.uuid4()
    with session_scope() as s:
        s.add(Service(
            id=svc_id, name=name, name_en=name,
            name_tl="", name_id="", name_vi="",
            duration_min=60, price=500,
            category=category, is_available=True,
        ))
    return svc_id


def _add_item(
    title: str,
    *,
    service_id: uuid.UUID | None = None,
    is_visible: bool = True,
    sort_order: int = 0,
) -> uuid.UUID:
    item_id = uuid.uuid4()
    with session_scope() as s:
        s.add(PortfolioItem(
            id=item_id,
            title=title,
            image_url=f"https://cdn.example.com/{title}.jpg",
            service_id=service_id,
            is_visible=is_visible,
            sort_order=sort_order,
        ))
    return item_id


def test_portfolio_empty():
    resp = client.get("/api/portfolio")
    assert resp.status_code == 200
    assert resp.json() == []


def test_portfolio_returns_visible_only():
    svc_id = _add_service("Gel")
    _add_item("Visible", service_id=svc_id, is_visible=True)
    _add_item("Hidden", service_id=svc_id, is_visible=False)

    resp = client.get("/api/portfolio")
    assert resp.status_code == 200
    titles = [i["title"] for i in resp.json()]
    assert "Visible" in titles
    assert "Hidden" not in titles


def test_portfolio_sorted_by_sort_order():
    _add_item("Third", sort_order=3)
    _add_item("First", sort_order=1)
    _add_item("Second", sort_order=2)

    resp = client.get("/api/portfolio")
    titles = [i["title"] for i in resp.json() if i["title"] in ("First", "Second", "Third")]
    assert titles == ["First", "Second", "Third"]


def test_portfolio_includes_service_info():
    svc_id = _add_service("凝膠美甲", category="gel")
    _add_item("My gel work", service_id=svc_id)

    resp = client.get("/api/portfolio")
    assert resp.status_code == 200
    data = next(i for i in resp.json() if i["title"] == "My gel work")
    assert data["service_name"] == "凝膠美甲"
    assert data["service_category"] == "gel"
    assert data["service_id"] is not None


def test_portfolio_item_without_service():
    _add_item("No service item", service_id=None)

    resp = client.get("/api/portfolio")
    assert resp.status_code == 200
    data = next(i for i in resp.json() if i["title"] == "No service item")
    assert data["service_id"] is None
    assert data["service_name"] is None
    assert data["service_category"] is None


def test_portfolio_category_filter():
    gel_id = _add_service("Gel", category="gel")
    art_id = _add_service("Nail Art", category="nail_art")
    _add_item("Gel work", service_id=gel_id)
    _add_item("Art work", service_id=art_id)

    resp = client.get("/api/portfolio?category=gel")
    assert resp.status_code == 200
    titles = [i["title"] for i in resp.json()]
    assert "Gel work" in titles
    assert "Art work" not in titles
