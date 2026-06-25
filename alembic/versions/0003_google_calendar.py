"""add google calendar columns

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-25

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("studio_profile", sa.Column("google_access_token", sa.String(), nullable=True))
    op.add_column("studio_profile", sa.Column("google_refresh_token", sa.String(), nullable=True))
    op.add_column("studio_profile", sa.Column("google_token_expiry", sa.DateTime(timezone=True), nullable=True))
    op.add_column("appointments", sa.Column("google_calendar_event_id", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("appointments", "google_calendar_event_id")
    op.drop_column("studio_profile", "google_token_expiry")
    op.drop_column("studio_profile", "google_refresh_token")
    op.drop_column("studio_profile", "google_access_token")
