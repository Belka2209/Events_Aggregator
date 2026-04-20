"""Tests for ticket usecases."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.enums import EventStatus
from src.models.event import Event
from src.models.ticket import Ticket
from src.services.events_provider_client import (
    ProviderError,
    RegistrationData,
    SeatsData,
    UnregisterData,
)
from src.usecases.create_ticket import CreateTicketUsecase
from src.usecases.delete_ticket import DeleteTicketUsecase
from src.usecases.exceptions import ProviderUnavailable


@pytest.mark.asyncio
async def test_create_ticket_usecase(
    sample_event: Event, ticket_repository, event_repository, db_session
):
    """Test CreateTicketUsecase."""
    from src.repositories.idempotency_repository import (
        SQLAlchemyIdempotencyRepository,
    )
    from src.repositories.outbox_repository import SQLAlchemyOutboxRepository

    mock_client = MagicMock()
    mock_client.register = AsyncMock(
        return_value=RegistrationData(ticket_id="test-ticket-id")
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
    )

    assert result["ticket_id"] == "test-ticket-id"
    mock_client.register.assert_called_once()


@pytest.mark.asyncio
async def test_delete_ticket_usecase(sample_event: Event, ticket_repository):
    """Test DeleteTicketUsecase."""
    mock_client = MagicMock()
    mock_client.unregister = AsyncMock(return_value=UnregisterData(success=True))

    # We need a ticket in the repo for DeleteTicketUsecase to find it
    ticket = Ticket(
        ticket_id="test-ticket-id",
        event_id=sample_event.id,
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        seat="A1",
        created_at=datetime.now(timezone.utc),
    )
    await ticket_repository.create(ticket)

    usecase = DeleteTicketUsecase(ticket_repo=ticket_repository, client=mock_client)

    await usecase.execute(ticket_id="test-ticket-id")

    mock_client.unregister.assert_called_once_with(
        event_id=sample_event.id, ticket_id="test-ticket-id"
    )

    # Verify ticket is deleted from repo
    deleted_ticket = await ticket_repository.get_by_ticket_id("test-ticket-id")
    assert deleted_ticket is None


@pytest.mark.asyncio
async def test_delete_ticket_usecase_provider_unavailable(
    sample_event: Event, ticket_repository
):
    """Test DeleteTicketUsecase raises ProviderUnavailable."""
    mock_client = MagicMock()
    mock_client.unregister = AsyncMock(
        side_effect=ProviderError(status_code=503, detail="provider unavailable")
    )

    ticket = Ticket(
        ticket_id="test-ticket-id-unavailable",
        event_id=sample_event.id,
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        seat="A1",
        created_at=datetime.now(timezone.utc),
    )
    await ticket_repository.create(ticket)

    usecase = DeleteTicketUsecase(ticket_repo=ticket_repository, client=mock_client)

    with pytest.raises(ProviderUnavailable):
        await usecase.execute(ticket_id=ticket.ticket_id)


@pytest.mark.asyncio
async def test_create_ticket_usecase_provider_unavailable(
    sample_event: Event, ticket_repository, event_repository, db_session
):
    """Test CreateTicketUsecase raises ProviderUnavailable."""
    from src.repositories.idempotency_repository import SQLAlchemyIdempotencyRepository
    from src.repositories.outbox_repository import SQLAlchemyOutboxRepository

    mock_client = MagicMock()
    mock_client.register = AsyncMock(
        side_effect=ProviderError(status_code=503, detail="provider unavailable")
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

    with pytest.raises(ProviderUnavailable):
        await usecase.execute(
            event_id=sample_event.id,
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            seat="A1",
        )


@pytest.mark.asyncio
async def test_create_ticket_usecase_retries_with_fallback_seat(
    sample_event: Event, ticket_repository, event_repository, db_session
):
    """Test CreateTicketUsecase retries with next available seat."""
    from src.repositories.idempotency_repository import SQLAlchemyIdempotencyRepository
    from src.repositories.outbox_repository import SQLAlchemyOutboxRepository

    mock_client = MagicMock()
    mock_client.register = AsyncMock(
        side_effect=[
            ProviderError(status_code=400, detail="Seat is unavailable"),
            RegistrationData(ticket_id="test-ticket-id-fallback"),
        ]
    )
    mock_client.get_seats = AsyncMock(return_value=SeatsData(seats=["A2", "A3"]))

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
    )

    assert result["ticket_id"] == "test-ticket-id-fallback"
    assert mock_client.register.await_count == 2
    first_call = mock_client.register.await_args_list[0].kwargs
    second_call = mock_client.register.await_args_list[1].kwargs
    assert first_call["seat"] == "A1"
    assert second_call["seat"] == "A2"
