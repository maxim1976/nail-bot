import os
os.environ.setdefault("ADMIN_JWT_SECRET", "test-secret-key-for-testing-only-32ch")

from fastapi.testclient import TestClient
from app.main import app


def test_dashboard_serves_html():
    client = TestClient(app)
    res = client.get("/dashboard/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "adminApp" in res.text


def test_dashboard_contains_tab_ids():
    client = TestClient(app)
    res = client.get("/dashboard/")
    assert res.status_code == 200
    for tab in ["studio", "services", "portfolio", "appointments", "schedule"]:
        assert tab in res.text
