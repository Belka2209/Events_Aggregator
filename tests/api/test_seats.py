"""Tests for seats API."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from src.models.event import Event
from src.services.events_provider_client import SeatsData


@pytest.mark.asyncio
async def test_get_seats(
    client: AsyncClient, sample_event: Event, mock_provider_client: MagicMock
):
    """Test get available seats for an event."""
    mock_seats = ["A1", "A2", "B1"]

    mock_provider_client.get_seats = AsyncMock(
        return_value=SeatsData(seats=mock_seats)
    )

    response = await client.get(f"/api/events/{sample_event.id}/seats")

    assert response.status_code == 200
    data = response.json()
    assert data["available_seats"] == mock_seats
    mock_provider_client.get_seats.assert_called_once_with(sample_event.id)


@pytest.mark.asyncio
async def test_get_seats_event_not_found(client: AsyncClient):
    """Test get seats for non-existent event."""
    response = await client.get("/api/events/non-existent-id/seats")
    assert response.status_code == 404
