"""Tests for events API."""

import pytest
from httpx import AsyncClient

from src.models.event import Event


@pytest.mark.asyncio
async def test_get_events(client: AsyncClient, sample_event: Event):
    """Test get events list."""
    response = await client.get("/api/events")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "count" in data
    assert data["count"] >= 1
    assert any(e["id"] == sample_event.id for e in data["results"])


@pytest.mark.asyncio
async def test_get_event_by_id(client: AsyncClient, sample_event: Event):
    """Test get single event by ID."""
    response = await client.get(f"/api/events/{sample_event.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_event.id
    assert data["name"] == sample_event.name


@pytest.mark.asyncio
async def test_get_event_not_found(client: AsyncClient):
    """Test get non-existent event."""
    response = await client.get("/api/events/non-existent-id")
    assert response.status_code == 404
