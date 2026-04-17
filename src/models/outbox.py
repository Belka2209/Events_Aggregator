"""Outbox model for guaranteed event delivery."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class OutboxStatus(str, Enum):
    """Outbox record status."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class OutboxEventType(str, Enum):
    """Outbox event types."""

    TICKET_CREATED = "ticket_created"


class Outbox(Base):
    """Outbox model for transactional outbox pattern."""

    __tablename__ = "outbox"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=OutboxStatus.PENDING.value
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_outbox_status_created", "status", "created_at"),)

    def __repr__(self) -> str:
        return f"<Outbox(id={self.id}, event_type={self.event_type}, status={self.status})>"
