#!/usr/bin/env python3
"""Seed nail services into the database.

Usage:
    DATABASE_URL=postgresql://... python scripts/seed_services.py

Or with .env:
    python scripts/seed_services.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Allow running from repo root without installing the package
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

SERVICES = [
    dict(
        name="日式光療凝膠",
        name_en="Japanese Gel Nails",
        name_tl="Japanese Gel Nails",
        name_id="Gel Kuku Jepang",
        name_vi="Gel móng Nhật",
        description="採用日本原裝凝膠，持久光澤、不易脫落，適合各種場合。",
        agent_notes="Duration 90 min. Popular choice. Includes base, color, top coat.",
        duration_min=90,
        price=1200,
        category="gel",
        image_url="/uploads/services/gel.jpg",
        in_carousel=True,
        sort_order=1,
    ),
    dict(
        name="手繪彩繪設計",
        name_en="Hand-painted Nail Art",
        name_tl="Hand-painted Nail Art",
        name_id="Seni Kuku Dilukis Tangan",
        name_vi="Vẽ móng tay nghệ thuật",
        description="專業美甲師手工繪製，從簡單線條到複雜圖案，展現獨特個性。",
        agent_notes="Duration 120 min. Price varies by complexity. Shown price is base.",
        duration_min=120,
        price=1800,
        category="art",
        image_url="/uploads/services/art.jpg",
        in_carousel=True,
        sort_order=2,
    ),
    dict(
        name="漸層渲染",
        name_en="Ombre Gradient",
        name_tl="Ombre Gradient",
        name_id="Gradien Ombre",
        name_vi="Móng chuyển màu Ombre",
        description="流行的漸層暈染效果，顏色自然過渡，時尚百搭。",
        agent_notes="Duration 90 min. Customer can choose 2–3 colors.",
        duration_min=90,
        price=1400,
        category="gel",
        image_url="/uploads/services/ombre.jpg",
        in_carousel=True,
        sort_order=3,
    ),
    dict(
        name="凝膠卸除",
        name_en="Gel Removal",
        name_tl="Pag-alis ng Gel",
        name_id="Pelepasan Gel",
        name_vi="Tháo gel móng",
        description="專業安全卸除舊凝膠，保護天然甲面，避免傷害。",
        agent_notes="Duration 30 min. Often booked together with new gel service.",
        duration_min=30,
        price=300,
        category="removal",
        image_url="/uploads/services/care.jpg",
        sort_order=4,
    ),
    dict(
        name="基礎修甲護理",
        name_en="Basic Nail Care",
        name_tl="Pangunahing Pag-aalaga ng Kuko",
        name_id="Perawatan Kuku Dasar",
        name_vi="Chăm sóc móng cơ bản",
        description="修剪、打磨、去死皮，讓雙手煥然一新。",
        agent_notes="Duration 45 min. No gel or polish included.",
        duration_min=45,
        price=500,
        category="care",
        image_url="/uploads/services/care.jpg",
        sort_order=5,
    ),
    dict(
        name="鑽飾造型",
        name_en="Rhinestone & Crystal Nail Art",
        name_tl="Rhinestone at Crystal Nail Art",
        name_id="Seni Kuku Berlian",
        name_vi="Đính đá trang trí móng",
        description="閃亮鑽飾點綴，增添華麗感，適合婚禮、派對等特殊場合。",
        agent_notes="Duration 120 min. Crystal/rhinestone quantity may affect price.",
        duration_min=120,
        price=2000,
        category="art",
        image_url="/uploads/services/crystal.jpg",
        in_carousel=True,
        sort_order=6,
    ),
    dict(
        name="法式美甲",
        name_en="French Manicure",
        name_tl="French Manicure",
        name_id="French Manicure",
        name_vi="Móng kiểu Pháp",
        description="經典白色法式尖端，優雅大方，永不過時。",
        agent_notes="Duration 75 min. Classic or modern French available.",
        duration_min=75,
        price=1000,
        category="gel",
        image_url="/uploads/services/french.jpg",
        sort_order=7,
    ),
    dict(
        name="足部光療凝膠",
        name_en="Pedicure Gel",
        name_tl="Pedicure Gel",
        name_id="Gel Pediküre",
        name_vi="Gel móng chân",
        description="專業足部護理加光療凝膠，讓雙腳同樣亮麗動人。",
        agent_notes="Duration 90 min. Includes foot soak and basic care.",
        duration_min=90,
        price=1300,
        category="pedicure",
        image_url="/uploads/services/pedicure.jpg",
        sort_order=8,
    ),
]


def main() -> None:
    get_engine()

    with session_scope() as session:
        existing = session.query(Service).count()
        if existing > 0:
            print(f"Database already has {existing} service(s). Skipping seed.")
            print("To re-seed, delete existing services first.")
            return

        for data in SERVICES:
            session.add(Service(**data))

        print(f"Inserted {len(SERVICES)} services:")
        for s in SERVICES:
            print(f"  [{s['category']:10s}] {s['name']} — NT${s['price']} / {s['duration_min']}min")


if __name__ == "__main__":
    main()
    print("\nDone.")
