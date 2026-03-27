"""Ticket model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base

if TYPE_CHECKING:
    from src.models.event import Event


class Ticket(Base):
    """Ticket model representing a registration."""

    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    ticket_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False
    )
    event_id: Mapped[str] = mapped_column(
        ForeignKey("events.id"), nullable=False
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    seat: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationship
    event: Mapped["Event"] = relationship(
        back_populates="tickets", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Ticket(id={self.id}, ticket_id={self.ticket_id}, event_id={self.event_id})>"
