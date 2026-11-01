import os
from pathlib import Path

os.environ.setdefault("ADMIN_JWT_SECRET", "test-secret-key-for-testing-only-32ch")

import pytest
from fastapi.testclient import TestClient

from app.main import app

LIFF_DIST = Path(__file__).parent.parent / "frontend" / "liff" / "dist"


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


@pytest.mark.parametrize("path", ["/liff/", "/liff/index.html"])
def test_liff_html_is_revalidated_on_every_load(path):
    res = TestClient(app).get(path)
    assert res.headers["cache-control"] == "no-cache"


def test_liff_html_not_modified_keeps_no_cache():
    client = TestClient(app)
    etag = client.get("/liff/").headers["etag"]
    res = client.get("/liff/", headers={"If-None-Match": etag})
    assert res.status_code == 304
    assert res.headers["cache-control"] == "no-cache"


def test_liff_hashed_assets_are_cached_long_term():
    bundle = next((LIFF_DIST / "assets").glob("*.js"))
    res = TestClient(app).get(f"/liff/assets/{bundle.name}")
    assert res.status_code == 200
    assert res.headers["cache-control"] == "public, max-age=31536000, immutable"
