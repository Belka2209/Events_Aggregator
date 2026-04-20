"""Tests for create ticket usecase with idempotency."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.enums import EventStatus
from src.services.events_provider_client import RegistrationData
from src.usecases.create_ticket import CreateTicketUsecase
from src.usecases.exceptions import IdempotencyConflict


@pytest.mark.asyncio
async def test_create_ticket_with_idempotency_key_new(
    db_session, sample_event, ticket_repository, event_repository
):
    """Test ticket creation with new idempotency key."""
    from src.repositories.idempotency_repository import (
        SQLAlchemyIdempotencyRepository,
    )
    from src.repositories.outbox_repository import SQLAlchemyOutboxRepository

    mock_client = MagicMock()
    mock_client.register = AsyncMock(
        return_value=RegistrationData(ticket_id="new-ticket-id")
    )

    sample_event.status = EventStatus.PUBLISHED

    outbox_repo = SQLAlchemyOutboxRepository(db_session)
    idempotency_repo = SQLAlchemyIdempotencyRepository(db_session)

    usecase = CreateTicketUsecase(
        event_repo=event_repository,
        ticket_repo=ticket_repository,
        outbox_repo=outbox_repo,
        idempotency_repo=idempotency_repo,
        client=mock_client,
    )

    result = await usecase.execute(
        event_id=sample_event.id,
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        seat="A1",
        idempotency_key="my-unique-key",
    )

    assert result["ticket_id"] == "new-ticket-id"
    mock_client.register.assert_called_once()


@pytest.mark.asyncio
async def test_create_ticket_with_idempotency_key_existing(
    db_session, sample_event, ticket_repository, event_repository
):
    """Test ticket creation with existing idempotency key returns existing ticket."""
    from src.repositories.idempotency_repository import (
        SQLAlchemyIdempotencyRepository,
    )
    from src.repositories.outbox_repository import SQLAlchemyOutboxRepository

    mock_client = MagicMock()
    mock_client.register = AsyncMock(
        return_value=RegistrationData(ticket_id="new-ticket-id")
    )

    sample_event.status = EventStatus.PUBLISHED

    outbox_repo = SQLAlchemyOutboxRepository(db_session)
    idempotency_repo = SQLAlchemyIdempotencyRepository(db_session)

    await idempotency_repo.create(
        key="existing-key",
        ticket_id="existing-ticket-id",
        event_id=sample_event.id,
        request_data={
            "event_id": sample_event.id,
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "seat": "A1",
        },
    )

    mock_client.reset_mock()

    usecase = CreateTicketUsecase(
        event_repo=event_repository,
        ticket_repo=ticket_repository,
        outbox_repo=outbox_repo,
        idempotency_repo=idempotency_repo,
        client=mock_client,
    )

    result = await usecase.execute(
        event_id=sample_event.id,
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        seat="A1",
        idempotency_key="existing-key",
    )

    assert result["ticket_id"] == "existing-ticket-id"
    mock_client.register.assert_not_called()


@pytest.mark.asyncio
async def test_create_ticket_idempotency_key_conflict_different_event(
    db_session, sample_event, ticket_repository, event_repository
):
    """Test idempotency key with different event raises domain conflict."""

    from src.repositories.idempotency_repository import (
        SQLAlchemyIdempotencyRepository,
    )
    from src.repositories.outbox_repository import SQLAlchemyOutboxRepository

    sample_event.status = EventStatus.PUBLISHED

    outbox_repo = SQLAlchemyOutboxRepository(db_session)
    idempotency_repo = SQLAlchemyIdempotencyRepository(db_session)

    await idempotency_repo.create(
        key="conflict-key",
        ticket_id="ticket-1",
        event_id="different-event-id",
        request_data={"event_id": "different-event-id"},
    )

    usecase = CreateTicketUsecase(
        event_repo=event_repository,
        ticket_repo=ticket_repository,
        outbox_repo=outbox_repo,
        idempotency_repo=idempotency_repo,
        client=MagicMock(),
    )

    with pytest.raises(IdempotencyConflict):
        await usecase.execute(
            event_id=sample_event.id,
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            seat="A1",
            idempotency_key="conflict-key",
        )


@pytest.mark.asyncio
async def test_create_ticket_idempotency_key_conflict_different_data(
    db_session, sample_event, ticket_repository, event_repository
):
    """Test idempotency key with different data raises domain conflict."""

    from src.repositories.idempotency_repository import (
        SQLAlchemyIdempotencyRepository,
    )
    from src.repositories.outbox_repository import SQLAlchemyOutboxRepository

    sample_event.status = EventStatus.PUBLISHED

    outbox_repo = SQLAlchemyOutboxRepository(db_session)
    idempotency_repo = SQLAlchemyIdempotencyRepository(db_session)

    await idempotency_repo.create(
        key="conflict-key",
        ticket_id="ticket-1",
        event_id=sample_event.id,
        request_data={
            "event_id": sample_event.id,
            "seat": "A1",
            "email": "old@example.com",
        },
    )

    usecase = CreateTicketUsecase(
        event_repo=event_repository,
        ticket_repo=ticket_repository,
        outbox_repo=outbox_repo,
        idempotency_repo=idempotency_repo,
        client=MagicMock(),
    )

    with pytest.raises(IdempotencyConflict):
        await usecase.execute(
            event_id=sample_event.id,
            first_name="John",
            last_name="Doe",
            email="new@example.com",
            seat="A2",
            idempotency_key="conflict-key",
        )


@pytest.mark.asyncio
async def test_create_ticket_creates_outbox_record(
    db_session, sample_event, ticket_repository, event_repository
):
    """Test ticket creation also creates outbox record."""
    from src.repositories.idempotency_repository import (
        SQLAlchemyIdempotencyRepository,
    )
    from src.repositories.outbox_repository import SQLAlchemyOutboxRepository

    mock_client = MagicMock()
    mock_client.register = AsyncMock(
        return_value=RegistrationData(ticket_id="ticket-outbox-test")
    )

    sample_event.status = EventStatus.PUBLISHED

    outbox_repo = SQLAlchemyOutboxRepository(db_session)
    idempotency_repo = SQLAlchemyIdempotencyRepository(db_session)

    usecase = CreateTicketUsecase(
        event_repo=event_repository,
        ticket_repo=ticket_repository,
        outbox_repo=outbox_repo,
        idempotency_repo=idempotency_repo,
        client=mock_client,
    )

    await usecase.execute(
        event_id=sample_event.id,
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        seat="A1",
    )

    pending = await outbox_repo.get_pending(limit=10)
    assert len(pending) == 1
    assert pending[0].payload["ticket_id"] == "ticket-outbox-test"
