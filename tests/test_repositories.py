"""Tests for repositories."""

import uuid
from datetime import datetime, timezone

import pytest

from src.models.event import Event, Place
from src.models.outbox import Outbox, OutboxEventType, OutboxStatus
from src.models.ticket import Ticket
from src.repositories.idempotency_repository import (
    SQLAlchemyIdempotencyRepository,
)
from src.repositories.outbox_repository import SQLAlchemyOutboxRepository


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


@pytest.mark.asyncio
async def test_outbox_create_and_get_pending(db_session):
    """Test outbox repository create and get pending."""
    repo = SQLAlchemyOutboxRepository(db_session)

    outbox = Outbox(
        id=str(uuid.uuid4()),
        event_type=OutboxEventType.TICKET_CREATED.value,
        payload={"ticket_id": "test-123", "message": "Test"},
        status=OutboxStatus.PENDING.value,
    )

    created = await repo.create(outbox)
    assert created.id == outbox.id

    pending = await repo.get_pending(limit=10)
    assert len(pending) == 1
    assert pending[0].id == outbox.id


@pytest.mark.asyncio
async def test_outbox_mark_sent(db_session):
    """Test marking outbox record as sent."""
    repo = SQLAlchemyOutboxRepository(db_session)

    outbox = Outbox(
        id=str(uuid.uuid4()),
        event_type=OutboxEventType.TICKET_CREATED.value,
        payload={"ticket_id": "test-123"},
        status=OutboxStatus.PENDING.value,
    )
    await repo.create(outbox)

    await repo.mark_sent(outbox)
    await db_session.commit()

    pending = await repo.get_pending(limit=10)
    assert len(pending) == 0


@pytest.mark.asyncio
async def test_outbox_mark_failed(db_session):
    """Test marking outbox record as failed."""
    repo = SQLAlchemyOutboxRepository(db_session)

    outbox = Outbox(
        id=str(uuid.uuid4()),
        event_type=OutboxEventType.TICKET_CREATED.value,
        payload={"ticket_id": "test-123"},
        status=OutboxStatus.PENDING.value,
    )
    await repo.create(outbox)

    await repo.mark_failed(outbox, "Error occurred")
    await db_session.commit()

    assert outbox.status == OutboxStatus.FAILED.value
    assert outbox.error_message == "Error occurred"
    assert outbox.retry_count == 1


@pytest.mark.asyncio
async def test_outbox_mark_retry(db_session):
    """Test marking outbox record for retry."""
    repo = SQLAlchemyOutboxRepository(db_session)

    outbox = Outbox(
        id=str(uuid.uuid4()),
        event_type=OutboxEventType.TICKET_CREATED.value,
        payload={"ticket_id": "test-123"},
        status=OutboxStatus.PENDING.value,
    )
    await repo.create(outbox)

    await repo.mark_retry(outbox, "Temporary error")
    await db_session.commit()

    assert outbox.status == OutboxStatus.PENDING.value
    assert outbox.error_message == "Temporary error"
    assert outbox.retry_count == 1


@pytest.mark.asyncio
async def test_outbox_get_pending_empty(db_session):
    """Test getting pending when none exist."""
    repo = SQLAlchemyOutboxRepository(db_session)

    pending = await repo.get_pending(limit=10)
    assert len(pending) == 0


@pytest.mark.asyncio
async def test_idempotency_create_and_get(db_session):
    """Test idempotency repository create and get."""
    repo = SQLAlchemyIdempotencyRepository(db_session)

    key = "unique-key-123"
    record = await repo.create(
        key=key,
        ticket_id="ticket-456",
        event_id="event-789",
        request_data={"seat": "A1", "email": "test@test.com"},
    )

    assert record.key == key

    found = await repo.get(key)
    assert found is not None
    assert found.key == key
    assert found.ticket_id == "ticket-456"


@pytest.mark.asyncio
async def test_idempotency_get_not_found(db_session):
    """Test get idempotency key that doesn't exist."""
    repo = SQLAlchemyIdempotencyRepository(db_session)

    found = await repo.get("non-existent-key")
    assert found is None
