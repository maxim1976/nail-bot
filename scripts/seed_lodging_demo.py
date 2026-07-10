#!/usr/bin/env python3
"""Seed lodging demo room types (山里暖陽 price table) into the database.

Usage:
    DATABASE_URL=postgresql://... python scripts/seed_lodging_demo.py

Or with .env:
    python scripts/seed_lodging_demo.py

House rules: 加人加床最多 5 床、每床 NT$800；12 人以下包棟無加床；2 歲以下嬰兒不計人數。
Each row is a whole-house (包棟) config with quantity=1.
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
from app.models import RoomType

# 適合人數, 房型名稱, 平日, 旺日, 連續假日
ROOMS = [
    dict(
        name="包棟-6人（四人房×1＋雙人房×1）",
        name_en="Whole house for 6",
        description="四人房 1 間＋雙人房 1 間，適合 6 人小家庭或朋友。",
        capacity=6,
        max_capacity=6,
        max_extra_beds=0,
        price_weekday=10500,
        price_peak=18000,
        price_holiday=21000,
        sort_order=1,
    ),
    dict(
        name="包棟-8人（四人房×2）",
        name_en="Whole house for 8",
        description="四人房 2 間，適合 8 人團體。",
        capacity=8,
        max_capacity=8,
        max_extra_beds=0,
        price_weekday=12000,
        price_peak=18000,
        price_holiday=21000,
        sort_order=2,
    ),
    dict(
        name="包棟-10人（四人房×2＋雙人房×1）",
        name_en="Whole house for 10",
        description="四人房 2 間＋雙人房 1 間，適合 10 人團體。",
        capacity=10,
        max_capacity=10,
        max_extra_beds=0,
        price_weekday=13500,
        price_peak=18000,
        price_holiday=21000,
        sort_order=3,
    ),
    dict(
        name="包棟-12人（四人房×3）",
        name_en="Whole house for 12",
        description="四人房 3 間，適合 12 人大團體。12 人以下包棟無加床。",
        capacity=12,
        max_capacity=12,
        max_extra_beds=0,
        price_weekday=15000,
        price_peak=18000,
        price_holiday=21000,
        sort_order=4,
    ),
    dict(
        name="包棟-16人（四人房×3＋雙人房×2）",
        name_en="Whole house for 16",
        description="四人房 3 間＋雙人房 2 間，適合 16 人大團體。加人加床最多 5 床、每床 NT$800。",
        capacity=16,
        max_capacity=21,
        max_extra_beds=5,
        price_weekday=18000,
        price_peak=21000,
        price_holiday=24000,
        sort_order=5,
    ),
]

COMMON = dict(quantity=1, extra_bed_price=800, is_available=True)


def main() -> None:
    get_engine()

    with session_scope() as session:
        existing = session.query(RoomType).count()
        if existing > 0:
            print(f"Database already has {existing} room type(s). Skipping seed.")
            print("To re-seed, delete existing room types first.")
            return

        for data in ROOMS:
            session.add(RoomType(**{**COMMON, **data}))

        print(f"Inserted {len(ROOMS)} room types:")
        for r in ROOMS:
            print(
                f"  {r['name']} — 平日 NT${r['price_weekday']} / "
                f"旺日 NT${r['price_peak']} / 連續假日 NT${r['price_holiday']}"
            )


if __name__ == "__main__":
    main()
    print("\nDone.")
