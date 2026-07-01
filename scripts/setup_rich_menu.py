#!/usr/bin/env python3
"""
Delete the old Hualienvibe rich menu and create a new one, then set it as
default for all users. Run whenever the image changes:

    python scripts/setup_rich_menu.py [path/to/image.jpg]

Reads LINE_CHANNEL_ACCESS_TOKEN and LIFF_ID from .env (or environment).
Prints the new RICH_MENU_ID so you can update Railway Variables.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx

# Load .env if present, but don't require it
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
LIFF_ID = os.environ.get("LIFF_ID", "")

if not TOKEN:
    print("ERROR: set LINE_CHANNEL_ACCESS_TOKEN environment variable")
    sys.exit(1)
if not LIFF_ID:
    print("ERROR: set LIFF_ID environment variable")
    sys.exit(1)

RICH_MENU_BODY = {
    "size": {"width": 2500, "height": 843},
    "selected": True,
    "name": "Hualienvibe Main Menu",
    "chatBarText": "選單",
    "areas": [
        {
            "bounds": {"x": 0, "y": 0, "width": 833, "height": 843},
            "action": {
                "type": "uri",
                "label": "預約",
                "uri": f"https://liff.line.me/{LIFF_ID}",
            },
        },
        {
            "bounds": {"x": 833, "y": 0, "width": 834, "height": 843},
            "action": {
                "type": "message",
                "label": "本月優惠",
                "text": "本月優惠",
            },
        },
        {
            "bounds": {"x": 1667, "y": 0, "width": 833, "height": 843},
            "action": {
                "type": "message",
                "label": "聯絡我們",
                "text": "聯絡我們",
            },
        },
    ],
}

BASE = "https://api.line.me/v2/bot"


def main() -> None:
    headers = {"Authorization": f"Bearer {TOKEN}"}

    default_image = Path(__file__).parent.parent / "app" / "assets" / "rich-menu.jpg"
    image_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_image
    if not image_path.exists():
        print(f"ERROR: image not found at {image_path}. Pass path as argument: python {sys.argv[0]} /path/to/image.jpg")
        sys.exit(1)

    mime = "image/jpeg" if image_path.suffix.lower() in (".jpg", ".jpeg") else "image/png"

    with httpx.Client(headers=headers, timeout=30) as client:
        # 1. Delete existing menu with the same name
        existing = client.get(f"{BASE}/richmenu/list").json().get("richmenus", [])
        for m in existing:
            if m.get("name") == "Hualienvibe Main Menu":
                client.delete(f"{BASE}/richmenu/{m['richMenuId']}")
                print(f"Deleted old menu: {m['richMenuId']}")

        # 2. Create rich menu structure
        print("Creating rich menu structure...")
        r = client.post(f"{BASE}/richmenu", json=RICH_MENU_BODY)
        r.raise_for_status()
        rich_menu_id = r.json()["richMenuId"]
        print(f"  Created: {rich_menu_id}")

        # 3. Upload image
        print(f"Uploading image: {image_path} ...")
        r = client.post(
            f"https://api-data.line.me/v2/bot/richmenu/{rich_menu_id}/content",
            content=image_path.read_bytes(),
            headers={**headers, "Content-Type": mime},
        )
        r.raise_for_status()
        print("  Image uploaded.")

        # 4. Set as default for all users
        print("Setting as default rich menu for all users...")
        r = client.post(f"{BASE}/user/all/richmenu/{rich_menu_id}")
        r.raise_for_status()
        print("  Set as default.")

    print(f"\nDone! Rich menu ID: {rich_menu_id}")
    print(f"Add to your .env:  RICH_MENU_ID={rich_menu_id}")


if __name__ == "__main__":
    main()
