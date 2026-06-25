from __future__ import annotations

import uuid
from datetime import date as dt_date
from datetime import datetime, time
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    PrimaryKeyConstraint,
    String,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class User(Base):
    __tablename__ = "users"

    line_user_id: Mapped[str] = mapped_column(String, primary_key=True)
    display_name: Mapped[str | None] = mapped_column(String)
    current_agent_key: Mapped[str | None] = mapped_column(String)
    preferred_language: Mapped[str] = mapped_column(
        String, nullable=False, default="zh", server_default="zh"
    )
    followed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    is_blocked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (UniqueConstraint("line_user_id", "agent_key", name="uq_user_agent"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    line_user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.line_user_id"), nullable=False
    )
    agent_key: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    message_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (Index("ix_messages_conv_created", "conversation_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    token_input: Mapped[int | None] = mapped_column(Integer)
    token_output: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class UsageCounter(Base):
    __tablename__ = "usage_counters"
    __table_args__ = (PrimaryKeyConstraint("line_user_id", "window_kind", "window_start"),)

    line_user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.line_user_id"), nullable=False
    )
    window_kind: Mapped[str] = mapped_column(String, nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    message_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )


class DailyCost(Base):
    __tablename__ = "daily_cost"

    date: Mapped[dt_date] = mapped_column(Date, primary_key=True)
    total_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, default=Decimal("0"), server_default="0"
    )
    killed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )


class StudioProfile(Base):
    """Singleton row (id=1). All nail tech studio metadata for the AI and admin."""
    __tablename__ = "studio_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    studio_name: Mapped[str] = mapped_column(String, nullable=False, server_default="Hualienvibe")
    owner_name: Mapped[str | None] = mapped_column(String)
    address: Mapped[str | None] = mapped_column(String)
    phone: Mapped[str | None] = mapped_column(String)
    instagram: Mapped[str | None] = mapped_column(String)
    website: Mapped[str | None] = mapped_column(String)
    cancellation_policy: Mapped[str | None] = mapped_column(String)
    aftercare_notes: Mapped[str | None] = mapped_column(String)
    ai_persona_notes: Mapped[str | None] = mapped_column(String)
    owner_line_user_id: Mapped[str | None] = mapped_column(String)
    google_access_token: Mapped[str | None] = mapped_column(String)
    google_refresh_token: Mapped[str | None] = mapped_column(String)
    google_token_expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Service(Base):
    __tablename__ = "services"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    name_en: Mapped[str] = mapped_column(String, nullable=False, server_default="")
    name_tl: Mapped[str] = mapped_column(String, nullable=False, server_default="")
    name_id: Mapped[str] = mapped_column(String, nullable=False, server_default="")
    name_vi: Mapped[str] = mapped_column(String, nullable=False, server_default="")
    description: Mapped[str] = mapped_column(String, nullable=False, server_default="")
    agent_notes: Mapped[str] = mapped_column(String, nullable=False, server_default="")
    duration_min: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String)
    category: Mapped[str] = mapped_column(String, nullable=False, server_default="general")
    is_available: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    in_carousel: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    appointments: Mapped[list[Appointment]] = relationship(back_populates="service")
    portfolio_items: Mapped[list[PortfolioItem]] = relationship(back_populates="service")


class WeeklyTemplate(Base):
    """One row per active day of week. dow: 0=Mon … 6=Sun."""
    __tablename__ = "weekly_template"

    dow: Mapped[int] = mapped_column(Integer, primary_key=True)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    slot_duration_min: Mapped[int] = mapped_column(Integer, nullable=False, default=90)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )


class DateOverride(Base):
    """Block a specific date or override its hours."""
    __tablename__ = "date_overrides"

    date: Mapped[dt_date] = mapped_column(Date, primary_key=True)
    is_blocked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    custom_start: Mapped[time | None] = mapped_column(Time)
    custom_end: Mapped[time | None] = mapped_column(Time)


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    line_user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.line_user_id"), nullable=False
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("services.id"), nullable=False
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_min: Mapped[int] = mapped_column(Integer, nullable=False)
    # status: confirmed → completed | cancelled (auto-confirmed on booking)
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="confirmed", server_default="confirmed"
    )
    customer_name: Mapped[str] = mapped_column(String, nullable=False, server_default="")
    notes: Mapped[str | None] = mapped_column(String)
    google_calendar_event_id: Mapped[str | None] = mapped_column(String)
    reminder_sent: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    service: Mapped[Service] = relationship(back_populates="appointments")


class PortfolioItem(Base):
    __tablename__ = "portfolio_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String, nullable=False, server_default="")
    image_url: Mapped[str] = mapped_column(String, nullable=False)
    service_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("services.id"), nullable=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_visible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    service: Mapped[Service | None] = relationship(back_populates="portfolio_items")
