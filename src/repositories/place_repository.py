"""Place repository."""

from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.event import Place


class PlaceRepository(Protocol):
    """Place repository protocol."""

    async def get(self, place_id: str) -> Place | None:
        """Get place by ID."""
        ...

    async def upsert(self, place: Place) -> Place:
        """Insert or update place."""
        ...


class SQLAlchemyPlaceRepository:
    """SQLAlchemy implementation of PlaceRepository."""

    def __init__(self, session: AsyncSession):
        """Initialize repository.

        Args:
            session: Async database session.
        """
        self._session = session

    async def get(self, place_id: str) -> Place | None:
        """Get place by ID.

        Args:
            place_id: Place UUID.

        Returns:
            Place or None.
        """
        result = await self._session.execute(
            select(Place).where(Place.id == place_id)
        )
        return result.scalar_one_or_none()

    async def upsert(self, place: Place) -> Place:
        """Insert or update place.

        Args:
            place: Place to upsert.

        Returns:
            Saved place.
        """
        existing = await self.get(place.id)

        if existing:
            # Update existing
            existing.name = place.name
            existing.city = place.city
            existing.address = place.address
            existing.seats_pattern = place.seats_pattern
            existing.changed_at = place.changed_at
            await self._session.flush()
            return existing
        else:
            # Insert new
            self._session.add(place)
            await self._session.flush()
            return place
