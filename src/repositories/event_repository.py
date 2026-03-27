"""Event repository."""

from datetime import datetime
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.event import Event


class EventRepository(Protocol):
    """Event repository protocol."""

    async def get(self, event_id: str) -> Event | None:
        """Get event by ID."""
        ...

    async def get_all(
        self,
        date_from: datetime | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Event], int]:
        """Get all events with optional date filter and pagination."""
        ...

    async def upsert(self, event: Event) -> Event:
        """Insert or update event."""
        ...


class SQLAlchemyEventRepository:
    """SQLAlchemy implementation of EventRepository."""

    def __init__(self, session: AsyncSession):
        """Initialize repository.

        Args:
            session: Async database session.
        """
        self._session = session

    async def get(self, event_id: str) -> Event | None:
        """Get event by ID.

        Args:
            event_id: Event UUID.

        Returns:
            Event or None.
        """
        result = await self._session.execute(
            select(Event).options(selectinload(Event.place)).where(Event.id == event_id),
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        date_from: datetime | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Event], int]:
        """Get all events with optional date filter and pagination.

        Args:
            date_from: Filter events after this date.
            offset: Pagination offset.
            limit: Page size.

        Returns:
            Tuple of (list of events, total count).
        """
        # Build query
        query = select(Event).options(selectinload(Event.place))

        if date_from:
            query = query.where(Event.event_time >= date_from)

        # Get total count
        count_query = select(func.count()).select_from(Event)
        if date_from:
            count_query = count_query.where(Event.event_time >= date_from)
        count_result = await self._session.execute(count_query)
        total = count_result.scalar() or 0

        # Apply pagination
        query = query.offset(offset).limit(limit)
        result = await self._session.execute(query)
        events = list(result.scalars().all())

        return events, total

    async def upsert(self, event: Event) -> Event:
        """Insert or update event.

        Args:
            event: Event to upsert.

        Returns:
            Saved event.
        """
        existing = await self.get(event.id)

        if existing:
            # Update existing
            existing.name = event.name
            existing.place_id = event.place_id
            existing.event_time = event.event_time
            existing.registration_deadline = event.registration_deadline
            existing.status = event.status
            existing.number_of_visitors = event.number_of_visitors
            existing.changed_at = event.changed_at
            existing.status_changed_at = event.status_changed_at
            await self._session.flush()
            return existing
        else:
            # Insert new
            self._session.add(event)
            await self._session.flush()
            return event
