"""Outbox repository."""

from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.outbox import Outbox, OutboxStatus


class OutboxRepository(Protocol):
    """Outbox repository protocol."""

    async def create(self, outbox: Outbox) -> Outbox:
        """Create outbox record."""
        ...

    async def get_pending(self, limit: int = 100) -> list[Outbox]:
        """Get pending outbox records."""
        ...

    async def mark_sent(self, outbox: Outbox) -> None:
        """Mark record as sent."""
        ...

    async def mark_failed(self, outbox: Outbox, error_message: str) -> None:
        """Mark record as failed."""
        ...

    async def mark_retry(self, outbox: Outbox, error_message: str) -> None:
        """Increment retry counter and keep record pending."""
        ...


class SQLAlchemyOutboxRepository:
    """SQLAlchemy implementation of OutboxRepository."""

    def __init__(self, session: AsyncSession):
        """Initialize repository.

        Args:
            session: Async database session.
        """
        self._session = session

    @staticmethod
    def _safe_retry_count(value: object) -> int:
        """Safely convert retry counter value from DB to int."""
        if isinstance(value, int):
            return value
        try:
            return int(value)  # Handles legacy string values.
        except (TypeError, ValueError):
            return 0

    async def create(self, outbox: Outbox) -> Outbox:
        """Create outbox record.

        Args:
            outbox: Outbox record to create.

        Returns:
            Created outbox record.
        """
        self._session.add(outbox)
        await self._session.flush()
        return outbox

    async def get_pending(self, limit: int = 100) -> list[Outbox]:
        """Get pending outbox records.

        Args:
            limit: Maximum number of records to fetch.

        Returns:
            List of pending outbox records.
        """
        result = await self._session.execute(
            select(Outbox)
            .where(Outbox.status == OutboxStatus.PENDING.value)
            .order_by(Outbox.created_at)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def mark_sent(self, outbox: Outbox) -> None:
        """Mark record as sent.

        Args:
            outbox: Outbox record to mark as sent.
        """
        from datetime import datetime, timezone

        outbox.status = OutboxStatus.SENT.value
        outbox.sent_at = datetime.now(timezone.utc)
        await self._session.flush()

    async def mark_failed(self, outbox: Outbox, error_message: str) -> None:
        """Mark record as failed.

        Args:
            outbox: Outbox record to mark as failed.
            error_message: Error message.
        """
        outbox.status = OutboxStatus.FAILED.value
        outbox.error_message = error_message
        outbox.retry_count = self._safe_retry_count(outbox.retry_count) + 1
        await self._session.flush()

    async def mark_retry(self, outbox: Outbox, error_message: str) -> None:
        """Increment retry counter and keep status pending.

        Args:
            outbox: Outbox record to retry later.
            error_message: Last error message.
        """
        outbox.status = OutboxStatus.PENDING.value
        outbox.error_message = error_message
        outbox.retry_count = self._safe_retry_count(outbox.retry_count) + 1
        await self._session.flush()
