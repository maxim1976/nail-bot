from __future__ import annotations

import base64
import hashlib
import hmac
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

_RICH_MENU_NAME = "Hualienvibe Main Menu"
_RICH_MENU_SIZE = {"width": 2500, "height": 843}


def verify_signature(*, secret: str, body: bytes, header_signature: str | None) -> bool:
    if not header_signature:
        return False
    digest = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode()
    return hmac.compare_digest(expected, header_signature)


@dataclass(frozen=True)
class ReplyMessage:
    payload: dict[str, Any]

    @classmethod
    def text(cls, body: str, *, quick_replies: tuple[str, ...] = ()) -> ReplyMessage:
        msg: dict[str, Any] = {"type": "text", "text": body}
        if quick_replies:
            msg["quickReply"] = {
                "items": [
                    {"type": "action", "action": {"type": "message", "label": qr, "text": qr}}
                    for qr in quick_replies
                ]
            }
        return cls(payload=msg)

    @classmethod
    def flex(cls, alt_text: str, contents: dict[str, Any]) -> ReplyMessage:
        return cls(payload={"type": "flex", "altText": alt_text, "contents": contents})


class LineClient:
    BASE = "https://api.line.me/v2/bot"

    def __init__(self, *, channel_access_token: str, timeout: float = 10.0) -> None:
        self._token = channel_access_token
        self._http = httpx.Client(
            timeout=timeout, headers={"Authorization": f"Bearer {channel_access_token}"}
        )

    def reply(self, *, reply_token: str, messages: list[ReplyMessage]) -> None:
        body = {"replyToken": reply_token, "messages": [m.payload for m in messages]}
        r = self._http.post(f"{self.BASE}/message/reply", json=body)
        r.raise_for_status()

    def push(self, *, line_user_id: str, messages: list[ReplyMessage]) -> None:
        body = {"to": line_user_id, "messages": [m.payload for m in messages]}
        r = self._http.post(f"{self.BASE}/message/push", json=body)
        r.raise_for_status()

    def multicast(self, *, user_ids: list[str], messages: list[ReplyMessage]) -> None:
        for i in range(0, len(user_ids), 500):
            chunk = user_ids[i : i + 500]
            body = {"to": chunk, "messages": [m.payload for m in messages]}
            r = self._http.post(f"{self.BASE}/message/multicast", json=body)
            r.raise_for_status()

    def link_rich_menu_to_user(self, *, line_user_id: str, rich_menu_id: str) -> None:
        r = self._http.post(f"{self.BASE}/user/{line_user_id}/richmenu/{rich_menu_id}")
        r.raise_for_status()

    def get_display_name(self, line_user_id: str) -> str | None:
        try:
            r = self._http.get(f"{self.BASE}/profile/{line_user_id}")
            if r.status_code != 200:
                return None
            return r.json().get("displayName")
        except httpx.HTTPError:
            return None

    def list_rich_menus(self) -> list[dict[str, Any]]:
        r = self._http.get(f"{self.BASE}/richmenu/list")
        r.raise_for_status()
        return r.json().get("richmenus", [])

    def create_rich_menu(self, *, liff_id: str, image_path: Path) -> str:
        body: dict[str, Any] = {
            "size": _RICH_MENU_SIZE,
            "selected": True,
            "name": _RICH_MENU_NAME,
            "chatBarText": "選單",
            "areas": [
                {
                    "bounds": {"x": 0, "y": 0, "width": 833, "height": 843},
                    "action": {
                        "type": "uri",
                        "label": "預約",
                        "uri": f"https://liff.line.me/{liff_id}",
                    },
                },
                {
                    "bounds": {"x": 833, "y": 0, "width": 834, "height": 843},
                    "action": {"type": "message", "label": "作品集", "text": "作品集"},
                },
                {
                    "bounds": {"x": 1667, "y": 0, "width": 833, "height": 843},
                    "action": {"type": "message", "label": "聯絡我們", "text": "聯絡我們"},
                },
            ],
        }
        r = self._http.post(f"{self.BASE}/richmenu", json=body)
        r.raise_for_status()
        rich_menu_id: str = r.json()["richMenuId"]

        mime = "image/jpeg" if image_path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
        r = self._http.post(
            f"https://api-data.line.me/v2/bot/richmenu/{rich_menu_id}/content",
            content=image_path.read_bytes(),
            headers={"Content-Type": mime},
        )
        r.raise_for_status()
        return rich_menu_id

    def set_default_rich_menu(self, rich_menu_id: str) -> None:
        r = self._http.post(f"{self.BASE}/user/all/richmenu/{rich_menu_id}")
        r.raise_for_status()

    def delete_rich_menu(self, rich_menu_id: str) -> None:
        r = self._http.delete(f"{self.BASE}/richmenu/{rich_menu_id}")
        r.raise_for_status()
