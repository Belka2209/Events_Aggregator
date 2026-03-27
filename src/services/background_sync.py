"""Background sync service."""

import asyncio
import logging

import anyio

from src.core.database import async_session_maker
from src.core.settings import settings
from src.repositories.event_repository import SQLAlchemyEventRepository
from src.repositories.place_repository import SQLAlchemyPlaceRepository
from src.repositories.sync_state_repository import (
    SQLAlchemySyncStateRepository,
)
from src.services.events_provider_client import EventsProviderClient
from src.usecases.sync_events import SyncEventsUsecase

logger = logging.getLogger(__name__)


class BackgroundSyncService:
    """Background service for periodic events synchronization."""

    def __init__(self):
        """Initialize the service."""
        self._task: asyncio.Task | None = None
        self._stop_event = anyio.Event()

    async def start(self) -> None:
        """Start the background sync service."""
        logger.info("Starting background sync service")
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        """Stop the background sync service."""
        logger.info("Stopping background sync service")
        self._stop_event.set()
        if self._task:
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run(self) -> None:
        """Run the sync loop."""
        while not self._stop_event.is_set():
            try:
                await self._sync()
            except Exception as e:
                logger.error("Sync error: %s", e, exc_info=True)

            # Wait for the next sync interval
            try:
                with anyio.fail_after(settings.sync_interval_hours * 3600):
                    await self._stop_event.wait()
            except asyncio.TimeoutError:
                pass
            except anyio.EndOfStream:
                break

    async def _sync(self) -> None:
        """Execute synchronization."""
        logger.info("Running scheduled sync")

        async with async_session_maker() as session:
            # Create repositories
            event_repo = SQLAlchemyEventRepository(session)
            place_repo = SQLAlchemyPlaceRepository(session)
            sync_state_repo = SQLAlchemySyncStateRepository(session)

            # Create client and usecase
            client = EventsProviderClient()
            usecase = SyncEventsUsecase(
                client=client,
                event_repo=event_repo,
                place_repo=place_repo,
                sync_state_repo=sync_state_repo,
            )

            # Execute sync
            stats = await usecase.execute()
            logger.info("Scheduled sync completed: %s", stats)
