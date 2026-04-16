"""Idempotency key repository."""

from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.idempotency import IdempotencyKey


class IdempotencyRepository(Protocol):
    """Idempotency repository protocol."""

    async def get(self, key: str) -> IdempotencyKey | None:
        """Get idempotency key record."""
        ...

    async def create(
        self,
        key: str,
        ticket_id: str,
        event_id: str,
        request_data: dict,
    ) -> IdempotencyKey:
        """Create idempotency key record."""
        ...


class SQLAlchemyIdempotencyRepository:
    """SQLAlchemy implementation of IdempotencyRepository."""

    def __init__(self, session: AsyncSession):
        """Initialize repository.

        Args:
            session: Async database session.
        """
        self._session = session

    async def get(self, key: str) -> IdempotencyKey | None:
        """Get idempotency key record.

        Args:
            key: Idempotency key.

        Returns:
            Idempotency key record or None.
        """
        result = await self._session.execute(
            select(IdempotencyKey).where(IdempotencyKey.key == key),
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        key: str,
        ticket_id: str,
        event_id: str,
        request_data: dict,
    ) -> IdempotencyKey:
        """Create idempotency key record.

        Args:
            key: Idempotency key.
            ticket_id: Created ticket ID.
            event_id: Event ID.
            request_data: Request data.

        Returns:
            Created idempotency key record.
        """
        import uuid
        from datetime import datetime, timezone

        record = IdempotencyKey(
            id=str(uuid.uuid4()),
            key=key,
            ticket_id=ticket_id,
            event_id=event_id,
            request_data=request_data,
            created_at=datetime.now(timezone.utc),
        )
        self._session.add(record)
        await self._session.flush()
        return record
