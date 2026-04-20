"""Sync events usecase."""

import logging
from datetime import datetime, timezone

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
        """Initialize use case."""
        self._client = client
        self._event_repo = event_repo
        self._place_repo = place_repo
        self._sync_state_repo = sync_state_repo

    async def execute(self) -> dict:
        """Execute synchronization."""
        logger.info("Starting events synchronization")

        # Get last sync state
        last_sync = await self._sync_state_repo.get_latest()

        # Определяем changed_at для запроса к API
        if last_sync and last_sync.last_changed_at:
            # Инкрементальная синхронизация - используем дату из БД
            changed_at_str = last_sync.last_changed_at.strftime("%Y-%m-%d")
            logger.info("Incremental sync with changed_at=%s", changed_at_str)
        else:
            # Первая синхронизация - получаем все события
            changed_at_str = "2000-01-01"
            logger.info("Initial sync with changed_at=%s", changed_at_str)

        stats = {"created": 0, "updated": 0, "errors": 0}

        try:
            # Создаем пагинатор
            paginator = EventsPaginator(self._client, changed_at_str)
            max_changed_at: datetime | None = None
            event_count = 0

            async for event_data in paginator:
                event_count += 1

                try:
                    # Парсим changed_at для отслеживания максимума
                    event_changed_at = datetime.fromisoformat(event_data.changed_at)
                    if max_changed_at is None or event_changed_at > max_changed_at:
                        max_changed_at = event_changed_at

                    # Upsert place
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
                    logger.error("Error processing event %s: %s", event_data.id, e)
                    stats["errors"] += 1

            logger.info("Total events processed: %d", event_count)

            # Сохраняем состояние синхронизации
            if max_changed_at:
                await self._sync_state_repo.create(
                    last_changed_at=max_changed_at,
                    sync_status="success",
                )
                logger.info("Saved sync state with last_changed_at=%s", max_changed_at)
            else:
                # Если не было событий, сохраняем текущую дату
                current_date = datetime.now(timezone.utc)
                await self._sync_state_repo.create(
                    last_changed_at=current_date,
                    sync_status="success",
                    error_message="No events found",
                )
                logger.info("No events found, saved current date=%s", current_date)

            logger.info(
                "Sync completed: %d created, %d updated, %d errors",
                stats["created"],
                stats["updated"],
                stats["errors"],
            )

        except Exception as e:
            logger.error("Sync failed: %s", e, exc_info=True)
            await self._sync_state_repo.create(
                last_changed_at=last_sync.last_changed_at if last_sync else None,
                sync_status="failed",
                error_message=str(e),
            )
            stats["error"] = str(e)

        return stats
