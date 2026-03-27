"""Tests for EventsPaginator."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.events_paginator import EventsPaginator
from src.services.events_provider_client import EventData, EventsProviderClient


@pytest.fixture
def mock_provider_client() -> MagicMock:
    """Fixture for a mocked EventsProviderClient."""
    client = MagicMock(spec=EventsProviderClient)
    client.events = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_paginator_single_page(mock_provider_client):
    """Test paginator with a single page of results."""
    # Arrange
    mock_events = [
        EventData(
            id=f"evt_{i}",
            name=f"Event {i}",
            place=None,
            event_time="",
            registration_deadline=None,
            status="",
            number_of_visitors=0,
            changed_at="2023-01-01T12:00:00Z",
            created_at="",
            status_changed_at="",
        )
        for i in range(5)
    ]
    mock_provider_client.events.return_value = (
        mock_events,
        None,
    )  # No next cursor
    paginator = EventsPaginator(mock_provider_client, "2023-01-01")

    # Act
    results = [event async for event in paginator]

    # Assert
    assert len(results) == 5
    assert results[0].id == "evt_0"
    mock_provider_client.events.assert_awaited_once_with(
        changed_at="2023-01-01", cursor=None
    )


@pytest.mark.asyncio
async def test_paginator_multiple_pages(mock_provider_client):
    """Test paginator with multiple pages."""
    # Arrange
    page1_events = [
        EventData(
            id="evt_1",
            name="Event 1",
            place=None,
            event_time="",
            registration_deadline=None,
            status="",
            number_of_visitors=0,
            changed_at="2023-01-01T12:00:00Z",
            created_at="",
            status_changed_at="",
        )
    ]
    page2_events = [
        EventData(
            id="evt_2",
            name="Event 2",
            place=None,
            event_time="",
            registration_deadline=None,
            status="",
            number_of_visitors=0,
            changed_at="2023-01-01T13:00:00Z",
            created_at="",
            status_changed_at="",
        )
    ]

    mock_provider_client.events.side_effect = [
        (page1_events, "http://test.com/api?cursor=p2"),
        (page2_events, None),
    ]
    paginator = EventsPaginator(mock_provider_client, "2023-01-01")

    # Act
    results = [event async for event in paginator]

    # Assert
    assert len(results) == 2
    assert results[0].id == "evt_1"
    assert results[1].id == "evt_2"
    assert mock_provider_client.events.call_count == 2
    mock_provider_client.events.assert_any_await(changed_at="2023-01-01", cursor=None)
    mock_provider_client.events.assert_any_await(changed_at="2023-01-01", cursor="p2")


@pytest.mark.asyncio
async def test_paginator_empty_response(mock_provider_client):
    """Test paginator when the provider returns no events."""
    # Arrange
    mock_provider_client.events.return_value = ([], None)
    paginator = EventsPaginator(mock_provider_client, "2023-01-01")

    # Act
    results = [event async for event in paginator]

    # Assert
    assert len(results) == 0
    mock_provider_client.events.assert_awaited_once()


@pytest.mark.asyncio
async def test_paginator_stops_on_is_last(mock_provider_client):
    """Test paginator stops when a page is returned with no next cursor, even if it has events."""
    # Arrange
    page1_events = [
        EventData(
            id="evt_1",
            name="Event 1",
            place=None,
            event_time="",
            registration_deadline=None,
            status="",
            number_of_visitors=0,
            changed_at="2023-01-01T12:00:00Z",
            created_at="",
            status_changed_at="",
        )
    ]
    mock_provider_client.events.return_value = (page1_events, None)
    paginator = EventsPaginator(mock_provider_client, "2023-01-01")

    # Act
    results = [event async for event in paginator]

    # Assert
    assert len(results) == 1
    assert mock_provider_client.events.call_count == 1
