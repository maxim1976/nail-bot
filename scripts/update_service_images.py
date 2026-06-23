#!/usr/bin/env python3
"""Add image URLs to existing services in the database.

Run once after services are already seeded:
    python3 scripts/update_service_images.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

if not os.environ.get("DATABASE_URL"):
    print("ERROR: DATABASE_URL not set")
    sys.exit(1)

from app.db import get_engine, session_scope
from app.models import Service

BASE = "/uploads/services"

# Maps Chinese name → image path (served from /uploads/services/)
IMAGE_MAP = {
    "日式光療凝膠": f"{BASE}/gel.jpg",
    "手繪彩繪設計": f"{BASE}/art.jpg",
    "漸層渲染":     f"{BASE}/ombre.jpg",
    "凝膠卸除":     f"{BASE}/care.jpg",
    "基礎修甲護理": f"{BASE}/care.jpg",
    "鑽飾造型":     f"{BASE}/crystal.jpg",
    "法式美甲":     f"{BASE}/french.jpg",
    "足部光療凝膠": f"{BASE}/pedicure.jpg",
}


def main() -> None:
    get_engine()
    with session_scope() as session:
        services = session.query(Service).all()
        updated = 0
        for svc in services:
            url = IMAGE_MAP.get(svc.name)
            if url and svc.image_url != url:
                svc.image_url = url
                print(f"  ✓ {svc.name} → {url}")
                updated += 1
            elif not url:
                print(f"  - {svc.name}: no mapping, skipped")
        print(f"\nUpdated {updated} service(s).")


if __name__ == "__main__":
    main()
