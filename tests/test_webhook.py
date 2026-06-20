from __future__ import annotations

import base64
import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


def _sig(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_health(client: TestClient):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_webhook_invalid_signature(client: TestClient):
    body = json.dumps({"events": []}).encode()
    r = client.post("/webhook", content=body, headers={"x-line-signature": "bad"})
    assert r.status_code == 401


def test_webhook_valid_signature(client: TestClient):
    import os
    secret = os.environ["LINE_CHANNEL_SECRET"]
    body = json.dumps({"events": []}).encode()
    sig = _sig(secret, body)
    r = client.post("/webhook", content=body, headers={"x-line-signature": sig})
    assert r.status_code == 200
    assert r.json() == {"ok": True}
