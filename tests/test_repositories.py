"""Tests for repositories."""

from datetime import datetime, timezone

import pytest

from src.models.event import Event, Place
from src.models.ticket import Ticket


@pytest.mark.asyncio
async def test_event_repository_upsert(event_repository, sample_place):
    """Test EventRepository upsert."""
    event_id = "new-event-id"
    event = Event(
        id=event_id,
        name="New Event",
        place_id=sample_place.id,
        event_time=datetime.now(timezone.utc),
        status="new",
    )

    # Test insert
    saved = await event_repository.upsert(event)
    assert saved.id == event_id

    # Test update
    saved.name = "Updated Name"
    updated = await event_repository.upsert(saved)
    assert updated.name == "Updated Name"


@pytest.mark.asyncio
async def test_place_repository_upsert(place_repository):
    """Test PlaceRepository upsert."""
    place_id = "new-place-id"
    place = Place(id=place_id, name="New Place", city="New City", address="New Address")

    # Test insert
    saved = await place_repository.upsert(place)
    assert saved.id == place_id

    # Test update
    saved.city = "Updated City"
    updated = await place_repository.upsert(saved)
    assert updated.city == "Updated City"


@pytest.mark.asyncio
async def test_ticket_repository_create_get_delete(ticket_repository, sample_event):
    """Test TicketRepository operations."""
    ticket_id = "test-ticket-id"
    ticket = Ticket(
        ticket_id=ticket_id,
        event_id=sample_event.id,
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        seat="A1",
        created_at=datetime.now(timezone.utc),
    )

    # Test create
    await ticket_repository.create(ticket)

    # Test get
    found = await ticket_repository.get_by_ticket_id(ticket_id)
    assert found is not None
    assert found.first_name == "John"

    # Test delete
    await ticket_repository.delete(found)
    deleted = await ticket_repository.get_by_ticket_id(ticket_id)
    assert deleted is None


@pytest.mark.asyncio
async def test_sync_state_repository_create_get_latest(sync_state_repository):
    """Test SyncStateRepository operations."""
    last_changed = datetime(2023, 5, 1, tzinfo=timezone.utc)

    # Test create
    await sync_state_repository.create(
        last_changed_at=last_changed, sync_status="success"
    )

    # Test get_latest
    latest = await sync_state_repository.get_latest()
    assert latest is not None
    assert latest.sync_status == "success"
    # Note: SQLite might return naive datetime, so we handle it if needed
    if latest.last_changed_at.tzinfo is None:
        assert latest.last_changed_at == last_changed.replace(tzinfo=None)
    else:
        assert latest.last_changed_at == last_changed
