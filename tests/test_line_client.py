from __future__ import annotations

import base64
import hashlib
import hmac

import httpx
import pytest
import respx

from app.line_client import LineClient, ReplyMessage, verify_signature


def _make_sig(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def test_verify_signature_valid():
    body = b'{"events":[]}'
    sig = _make_sig("mysecret", body)
    assert verify_signature(secret="mysecret", body=body, header_signature=sig) is True


def test_verify_signature_invalid():
    body = b'{"events":[]}'
    assert verify_signature(secret="mysecret", body=body, header_signature="bad") is False


def test_verify_signature_missing():
    assert verify_signature(secret="s", body=b"b", header_signature=None) is False


def test_reply_message_text_no_quick_replies():
    msg = ReplyMessage.text("hello")
    assert msg.payload == {"type": "text", "text": "hello"}


def test_reply_message_text_with_quick_replies():
    msg = ReplyMessage.text("choose", quick_replies=("A", "B"))
    assert msg.payload["quickReply"]["items"][0]["action"]["label"] == "A"
    assert msg.payload["quickReply"]["items"][1]["action"]["label"] == "B"


def test_reply_message_flex():
    contents = {"type": "bubble"}
    msg = ReplyMessage.flex("alt", contents)
    assert msg.payload == {"type": "flex", "altText": "alt", "contents": contents}


@respx.mock
def test_line_client_reply():
    route = respx.post("https://api.line.me/v2/bot/message/reply").mock(
        return_value=httpx.Response(200, json={})
    )
    client = LineClient(channel_access_token="tok")
    client.reply(reply_token="rt", messages=[ReplyMessage.text("hi")])
    assert route.called


@respx.mock
def test_line_client_push():
    route = respx.post("https://api.line.me/v2/bot/message/push").mock(
        return_value=httpx.Response(200, json={})
    )
    client = LineClient(channel_access_token="tok")
    client.push(line_user_id="U123", messages=[ReplyMessage.text("hi")])
    assert route.called


@respx.mock
def test_line_client_get_display_name_ok():
    respx.get("https://api.line.me/v2/bot/profile/U123").mock(
        return_value=httpx.Response(200, json={"displayName": "Alice"})
    )
    client = LineClient(channel_access_token="tok")
    assert client.get_display_name("U123") == "Alice"


@respx.mock
def test_line_client_get_display_name_404():
    respx.get("https://api.line.me/v2/bot/profile/U999").mock(
        return_value=httpx.Response(404, json={})
    )
    client = LineClient(channel_access_token="tok")
    assert client.get_display_name("U999") is None
