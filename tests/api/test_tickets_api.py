"""Tests for tickets API."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from src.models.event import Event
from src.services.events_provider_client import RegistrationData


@pytest.mark.asyncio
async def test_register_ticket(
    client: AsyncClient, sample_event: Event, mock_provider_client: MagicMock
):
    """Test register ticket for an event."""
    ticket_id = str(uuid.uuid4())
    registration_payload = {
        "event_id": sample_event.id,
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "seat": "A1",
    }

    # Ensure event is published
    sample_event.status = "published"

    mock_provider_client.register = AsyncMock(
        return_value=RegistrationData(ticket_id=ticket_id)
    )

    response = await client.post("/api/tickets", json=registration_payload)

    assert response.status_code == 201
    data = response.json()
    assert data["ticket_id"] == ticket_id
    mock_provider_client.register.assert_called_once()


@pytest.mark.asyncio
async def test_register_ticket_event_not_found(client: AsyncClient):
    """Test register ticket for non-existent event."""
    registration_payload = {
        "event_id": str(uuid.uuid4()),
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "seat": "A1",
    }
    response = await client.post("/api/tickets", json=registration_payload)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_unregister_ticket(
    client: AsyncClient,
    sample_event: Event,
    db_session,
    mock_provider_client: MagicMock,
):
    """Test unregister ticket."""
    ticket_id = str(uuid.uuid4())

    # Create a ticket in DB
    from datetime import datetime, timezone

    from src.models.ticket import Ticket

    ticket = Ticket(
        ticket_id=ticket_id,
        event_id=sample_event.id,
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        seat="A1",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(ticket)
    await db_session.flush()

    mock_provider_client.unregister = AsyncMock()

    response = await client.delete(f"/api/tickets/{ticket_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    mock_provider_client.unregister.assert_called_once_with(
        event_id=sample_event.id, ticket_id=ticket_id
    )
