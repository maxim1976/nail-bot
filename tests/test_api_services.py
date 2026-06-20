from __future__ import annotations

import uuid
from fastapi.testclient import TestClient

from app.db import session_scope
from app.main import app
from app.models import Service

client = TestClient(app)


def _add_service(name: str, available: bool = True, sort_order: int = 0) -> uuid.UUID:
    svc_id = uuid.uuid4()
    with session_scope() as s:
        s.add(Service(
            id=svc_id, name=name, name_en=name,
            name_tl="", name_id="", name_vi="",
            duration_min=90, price=800,
            is_available=available, sort_order=sort_order,
        ))
    return svc_id


def test_list_services_empty():
    resp = client.get("/api/services")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_services_returns_available_only():
    _add_service("Hidden", available=False)
    svc_id = _add_service("Visible", available=True)
    resp = client.get("/api/services")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == str(svc_id)


def test_list_services_sort_order():
    id_b = _add_service("B", sort_order=2)
    id_a = _add_service("A", sort_order=1)
    resp = client.get("/api/services")
    assert resp.status_code == 200
    # Filter to only the services this test added
    ids = {str(id_a), str(id_b)}
    names = [d["name"] for d in resp.json() if d["id"] in ids]
    assert names == ["A", "B"]
