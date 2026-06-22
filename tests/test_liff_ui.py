import os

os.environ.setdefault("ADMIN_JWT_SECRET", "test-secret-key-for-testing-only-32ch")

from fastapi.testclient import TestClient

from app.main import app


def test_liff_serves_html():
    client = TestClient(app)
    res = client.get("/liff/index.html")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]


def test_liff_root_serves_html():
    client = TestClient(app)
    res = client.get("/liff/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
