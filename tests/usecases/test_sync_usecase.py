"""Tests for sync events usecase."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.services.events_provider_client import EventData, PlaceData
from src.usecases.sync_events import SyncEventsUsecase


@pytest.mark.asyncio
async def test_sync_events_initial(
    event_repository, place_repository, sync_state_repository
):
    """Test initial synchronization."""
    mock_client = MagicMock()

    # Mock event data from API
    now_iso = datetime.now(timezone.utc).isoformat()
    event_data = EventData(
        id="api-event-id",
        name="API Event",
        place=PlaceData(
            id="api-place-id",
            name="API Place",
            city="API City",
            address="API Address",
            seats_pattern=None,
            changed_at=now_iso,
            created_at=now_iso,
        ),
        event_time=now_iso,
        registration_deadline=None,
        status="active",
        number_of_visitors=10,
        changed_at=now_iso,
        created_at=now_iso,
        status_changed_at=None,
    )

    # Mock Paginator to return one event
    mock_paginator = MagicMock()
    mock_paginator.__aiter__.return_value = [event_data]

    with patch(
        "src.usecases.sync_events.EventsPaginator", return_value=mock_paginator
    ):
        usecase = SyncEventsUsecase(
            client=mock_client,
            event_repo=event_repository,
            place_repo=place_repository,
            sync_state_repo=sync_state_repository,
        )

        stats = await usecase.execute()

        assert stats["created"] == 1
        assert stats["updated"] == 0
        assert stats["errors"] == 0

        # Verify event was saved
        event = await event_repository.get("api-event-id")
        assert event is not None
        assert event.name == "API Event"

        # Verify sync state was updated
        latest_sync = await sync_state_repository.get_latest()
        assert latest_sync is not None
        assert latest_sync.sync_status == "success"


@pytest.mark.asyncio
async def test_sync_events_incremental(
    event_repository, place_repository, sync_state_repository
):
    """Test incremental synchronization."""
    mock_client = MagicMock()

    # Create previous sync state
    last_sync_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
    await sync_state_repository.create(
        last_changed_at=last_sync_date, sync_status="success"
    )

    # Mock event data with later date
    now_iso = datetime.now(timezone.utc).isoformat()
    event_data = EventData(
        id="api-event-id",
        name="Updated API Event",
        place=PlaceData(
            id="api-place-id",
            name="API Place",
            city="API City",
            address="API Address",
            seats_pattern=None,
            changed_at=now_iso,
            created_at=now_iso,
        ),
        event_time=now_iso,
        registration_deadline=None,
        status="active",
        number_of_visitors=10,
        changed_at=now_iso,
        created_at=now_iso,
        status_changed_at=None,
    )

    mock_paginator = MagicMock()
    mock_paginator.__aiter__.return_value = [event_data]

    with patch(
        "src.usecases.sync_events.EventsPaginator", return_value=mock_paginator
    ):
        usecase = SyncEventsUsecase(
            client=mock_client,
            event_repo=event_repository,
            place_repo=place_repository,
            sync_state_repo=sync_state_repository,
        )

        stats = await usecase.execute()

        assert stats["created"] == 1

        # Verify sync state was updated with new date
        latest_sync = await sync_state_repository.get_latest()

        # Handle possible naive/aware comparison if SQLite returns naive
        latest_changed = latest_sync.last_changed_at
        if latest_changed.tzinfo is None and last_sync_date.tzinfo is not None:
            last_sync_date_cmp = last_sync_date.replace(tzinfo=None)
        else:
            last_sync_date_cmp = last_sync_date

        assert latest_changed > last_sync_date_cmp


@pytest.mark.asyncio
async def test_sync_events_failure(
    event_repository, place_repository, sync_state_repository
):
    """Test synchronization failure."""
    mock_client = MagicMock()

    # Mock Paginator to raise error
    with patch(
        "src.usecases.sync_events.EventsPaginator",
        side_effect=Exception("API Error"),
    ):
        usecase = SyncEventsUsecase(
            client=mock_client,
            event_repo=event_repository,
            place_repo=place_repository,
            sync_state_repo=sync_state_repository,
        )

        stats = await usecase.execute()

        assert stats["error"] == "API Error"

        # Verify sync state was updated with failed status
        latest_sync = await sync_state_repository.get_latest()
        assert latest_sync.sync_status == "failed"
        assert latest_sync.error_message == "API Error"
