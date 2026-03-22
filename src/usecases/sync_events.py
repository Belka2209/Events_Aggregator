"""Sync events usecase."""

import logging
from datetime import datetime

from src.models.event import Event, Place
from src.repositories.event_repository import EventRepository
from src.repositories.place_repository import PlaceRepository
from src.repositories.sync_state_repository import SyncStateRepository
from src.services.events_paginator import EventsPaginator
from src.services.events_provider_client import EventsProviderClient

logger = logging.getLogger(__name__)


class SyncEventsUsecase:
    """Use case for synchronizing events from Events Provider API."""

    def __init__(
        self,
        client: EventsProviderClient,
        event_repo: EventRepository,
        place_repo: PlaceRepository,
        sync_state_repo: SyncStateRepository,
    ):
        """Initialize use case.

        Args:
            client: EventsProviderClient instance.
            event_repo: EventRepository instance.
            place_repo: PlaceRepository instance.
            sync_state_repo: SyncStateRepository instance.
        """
        self._client = client
        self._event_repo = event_repo
        self._place_repo = place_repo
        self._sync_state_repo = sync_state_repo

    async def execute(self, changed_at: str | None = None) -> dict:
        """Execute synchronization.
        Args:
        changed_at: Start date in YYYY-MM-DD format.
                    Required for first sync, ignored for incremental sync.
        Returns:
            Dict with sync statistics.
        """
        logger.info("Starting events synchronization")

        # Get last sync state
        last_sync = await self._sync_state_repo.get_latest()
        last_changed_at = last_sync.last_changed_at
        if not last_changed_at:
            raise ValueError("changed_at parameter is required")

        # Определяем changed_at_str
        if last_sync and last_sync.last_changed_at:
            # Инкрементальная синхронизация - используем дату из БД
            changed_at_str = last_sync.last_changed_at.strftime("%Y-%m-%d")
            last_changed_at = last_sync.last_changed_at
            logger.info(f"Incremental sync with changed_at={changed_at_str}")
        else:
            # Первая синхронизация - проверяем, что передан changed_at
            if not changed_at:
                error_msg = "changed_at parameter is required for first sync"
                logger.error(error_msg)
                await self._sync_state_repo.create(
                    last_changed_at=None,
                    sync_status="failed",
                    error_message=error_msg,
                )
                return {"created": 0, "updated": 0, "errors": 0, "error": error_msg}
            # Проверяем формат даты
            try:
                datetime.strptime(changed_at, "%Y-%m-%d")
            except ValueError:
                error_msg = f"Invalid changed_at format: {changed_at}. Use YYYY-MM-DD"
                logger.error(error_msg)
                await self._sync_state_repo.create(
                    last_changed_at=None,
                    sync_status="failed",
                    error_message=error_msg,
                )
                return {"created": 0, "updated": 0, "errors": 0, "error": error_msg}

            changed_at_str = changed_at
            logger.info(f"Initial sync with changed_at={changed_at_str}")

        stats = {"created": 0, "updated": 0, "errors": 0}

        try:
            # Create paginator and iterate through all events
            paginator = EventsPaginator(self._client, changed_at_str)
            max_changed_at: datetime | None = None

            async for event_data in paginator:
                try:
                    # Parse changed_at to track max
                    event_changed_at = datetime.fromisoformat(event_data.changed_at)
                    if max_changed_at is None or event_changed_at > max_changed_at:
                        max_changed_at = event_changed_at

                    # Upsert place first
                    place = Place(
                        id=event_data.place.id,
                        name=event_data.place.name,
                        city=event_data.place.city,
                        address=event_data.place.address,
                        seats_pattern=event_data.place.seats_pattern,
                        changed_at=(
                            datetime.fromisoformat(event_data.place.changed_at)
                            if event_data.place.changed_at
                            else None
                        ),
                        created_at=(
                            datetime.fromisoformat(event_data.place.created_at)
                            if event_data.place.created_at
                            else None
                        ),
                    )
                    await self._place_repo.upsert(place)

                    # Upsert event
                    event = Event(
                        id=event_data.id,
                        name=event_data.name,
                        place_id=event_data.place.id,
                        event_time=datetime.fromisoformat(event_data.event_time),
                        registration_deadline=(
                            datetime.fromisoformat(event_data.registration_deadline)
                            if event_data.registration_deadline
                            else None
                        ),
                        status=event_data.status,
                        number_of_visitors=event_data.number_of_visitors,
                        changed_at=event_changed_at,
                        created_at=(
                            datetime.fromisoformat(event_data.created_at)
                            if event_data.created_at
                            else None
                        ),
                        status_changed_at=(
                            datetime.fromisoformat(event_data.status_changed_at)
                            if event_data.status_changed_at
                            else None
                        ),
                    )

                    existing = await self._event_repo.get(event.id)
                    if existing:
                        await self._event_repo.upsert(event)
                        stats["updated"] += 1
                    else:
                        await self._event_repo.upsert(event)
                        stats["created"] += 1

                except Exception as e:
                    logger.error(f"Error processing event {event_data.id}: {e}")
                    stats["errors"] += 1

            # Update sync state
            await self._sync_state_repo.create(
                last_changed_at=max_changed_at,
                sync_status="success",
            )

            logger.info(
                f"Sync completed: {stats['created']} created, "
                f"{stats['updated']} updated, {stats['errors']} errors",
            )

        except Exception as e:
            logger.error(f"Sync failed: {e}")
            await self._sync_state_repo.create(
                last_changed_at=last_changed_at,
                sync_status="failed",
                error_message=str(e),
            )
            stats["error"] = str(e)

        return stats
