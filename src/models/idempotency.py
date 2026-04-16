"""Idempotency key model for ensuring idempotent operations."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class IdempotencyKey(Base):
    """Model for storing idempotency keys and their results."""

    __tablename__ = "idempotency_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    ticket_id: Mapped[str] = mapped_column(String(36), nullable=False)
    event_id: Mapped[str] = mapped_column(String(36), nullable=False)
    request_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    __table_args__ = (Index("ix_idempotency_key_key", "key"),)

    def __repr__(self) -> str:
        return f"<IdempotencyKey(key={self.key}, ticket_id={self.ticket_id})>"
