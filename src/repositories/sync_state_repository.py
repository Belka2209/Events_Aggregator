"""SyncState repository."""

from datetime import datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.sync_state import SyncState


class SyncStateRepository(Protocol):
    """SyncState repository protocol."""

    async def get_latest(self) -> SyncState | None:
        """Get latest sync state."""
        ...

    async def create(
        self,
        last_changed_at: datetime | None = None,
        sync_status: str = "pending",
        error_message: str | None = None,
    ) -> SyncState:
        """Create sync state."""
        ...


class SQLAlchemySyncStateRepository:
    """SQLAlchemy implementation of SyncStateRepository."""

    def __init__(self, session: AsyncSession):
        """Initialize repository.

        Args:
            session: Async database session.
        """
        self._session = session

    async def get_latest(self) -> SyncState | None:
        """Get latest sync state.

        Returns:
            Latest SyncState or None.
        """
        result = await self._session.execute(
            select(SyncState).order_by(SyncState.id.desc()).limit(1),
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        last_changed_at: datetime | None = None,
        sync_status: str = "pending",
        error_message: str | None = None,
    ) -> SyncState:
        """Create sync state.

        Args:
            last_changed_at: Last changed_at value from sync.
            sync_status: Sync status.
            error_message: Error message if failed.

        Returns:
            Created SyncState.
        """
        from datetime import timezone

        sync_state = SyncState(
            last_sync_time=datetime.now(timezone.utc),
            last_changed_at=last_changed_at,
            sync_status=sync_status,
            error_message=error_message,
        )
        self._session.add(sync_state)
        await self._session.flush()
        return sync_state
