"""add lodging models (room_types, bookings, holiday_dates)

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-10

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "room_types",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("name_en", sa.String(), nullable=False, server_default=""),
        sa.Column("description", sa.String(), nullable=False, server_default=""),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("max_capacity", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("price_weekday", sa.Integer(), nullable=False),
        sa.Column("price_peak", sa.Integer(), nullable=False),
        sa.Column("price_holiday", sa.Integer(), nullable=False),
        sa.Column("extra_bed_price", sa.Integer(), nullable=False, server_default="800"),
        sa.Column("max_extra_beds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "bookings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("line_user_id", sa.String(), sa.ForeignKey("users.line_user_id"), nullable=False),
        sa.Column("room_type_id", UUID(as_uuid=True), sa.ForeignKey("room_types.id"), nullable=False),
        sa.Column("check_in", sa.Date(), nullable=False),
        sa.Column("check_out", sa.Date(), nullable=False),
        sa.Column("guests", sa.Integer(), nullable=False),
        sa.Column("extra_beds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_price", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="confirmed"),
        sa.Column("customer_name", sa.String(), nullable=False, server_default=""),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("reminder_sent", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "holiday_dates",
        sa.Column("date", sa.Date(), primary_key=True),
        sa.Column("day_type", sa.String(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("holiday_dates")
    op.drop_table("bookings")
    op.drop_table("room_types")
