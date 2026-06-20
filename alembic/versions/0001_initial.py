"""initial

Revision ID: 0001
Revises:
Create Date: 2026-06-20

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # tables with no FK deps first
    op.create_table(
        "users",
        sa.Column("line_user_id", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=True),
        sa.Column("current_agent_key", sa.String(), nullable=True),
        sa.Column("preferred_language", sa.String(), server_default="zh", nullable=False),
        sa.Column(
            "followed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "is_blocked",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("line_user_id"),
    )

    op.create_table(
        "daily_cost",
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column(
            "total_cost_usd",
            sa.Numeric(10, 4),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "killed",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("date"),
    )

    op.create_table(
        "studio_profile",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("studio_name", sa.String(), server_default="Hualienvibe", nullable=False),
        sa.Column("owner_name", sa.String(), nullable=True),
        sa.Column("address", sa.String(), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("instagram", sa.String(), nullable=True),
        sa.Column("cancellation_policy", sa.String(), nullable=True),
        sa.Column("aftercare_notes", sa.String(), nullable=True),
        sa.Column("ai_persona_notes", sa.String(), nullable=True),
        sa.Column("owner_line_user_id", sa.String(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "services",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("name_en", sa.String(), server_default="", nullable=False),
        sa.Column("name_tl", sa.String(), server_default="", nullable=False),
        sa.Column("name_id", sa.String(), server_default="", nullable=False),
        sa.Column("name_vi", sa.String(), server_default="", nullable=False),
        sa.Column("description", sa.String(), server_default="", nullable=False),
        sa.Column("agent_notes", sa.String(), server_default="", nullable=False),
        sa.Column("duration_min", sa.Integer(), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.String(), nullable=True),
        sa.Column("category", sa.String(), server_default="general", nullable=False),
        sa.Column(
            "is_available",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "in_carousel",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "weekly_template",
        sa.Column("dow", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("slot_duration_min", sa.Integer(), server_default="90", nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("dow"),
    )

    op.create_table(
        "date_overrides",
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column(
            "is_blocked",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("custom_start", sa.Time(), nullable=True),
        sa.Column("custom_end", sa.Time(), nullable=True),
        sa.PrimaryKeyConstraint("date"),
    )

    # tables that depend on users
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("line_user_id", sa.String(), nullable=False),
        sa.Column("agent_key", sa.String(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_message_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("message_count", sa.Integer(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(["line_user_id"], ["users.line_user_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("line_user_id", "agent_key", name="uq_user_agent"),
    )

    op.create_table(
        "usage_counters",
        sa.Column("line_user_id", sa.String(), nullable=False),
        sa.Column("window_kind", sa.String(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("message_count", sa.Integer(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(["line_user_id"], ["users.line_user_id"]),
        sa.PrimaryKeyConstraint("line_user_id", "window_kind", "window_start"),
    )

    # portfolio_items depends on services
    op.create_table(
        "portfolio_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(), server_default="", nullable=False),
        sa.Column("image_url", sa.String(), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "is_visible",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # messages depends on conversations
    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("token_input", sa.Integer(), nullable=True),
        sa.Column("token_output", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["conversations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_messages_conv_created", "messages", ["conversation_id", "created_at"]
    )

    # appointments depends on users + services
    op.create_table(
        "appointments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("line_user_id", sa.String(), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_min", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), server_default="confirmed", nullable=False),
        sa.Column("customer_name", sa.String(), server_default="", nullable=False),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column(
            "reminder_sent",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["line_user_id"], ["users.line_user_id"]),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    # reverse order: children before parents
    op.drop_table("appointments")
    op.drop_index("ix_messages_conv_created", table_name="messages")
    op.drop_table("messages")
    op.drop_table("portfolio_items")
    op.drop_table("usage_counters")
    op.drop_table("conversations")
    op.drop_table("date_overrides")
    op.drop_table("weekly_template")
    op.drop_table("services")
    op.drop_table("studio_profile")
    op.drop_table("daily_cost")
    op.drop_table("users")
