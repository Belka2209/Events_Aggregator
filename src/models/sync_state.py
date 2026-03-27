"""SyncState model for tracking synchronization state."""

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class SyncState(Base):
    """SyncState model for tracking synchronization metadata."""

    __tablename__ = "sync_states"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    last_sync_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sync_status: Mapped[str] = mapped_column(String(50), default="pending")
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    def __repr__(self) -> str:
        return f"<SyncState(id={self.id}, status={self.sync_status})>"
