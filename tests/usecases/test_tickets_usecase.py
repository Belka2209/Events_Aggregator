"""Tests for ticket usecases."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.usecases.create_ticket import CreateTicketUsecase
from src.usecases.delete_ticket import DeleteTicketUsecase
from src.services.events_provider_client import RegistrationData, UnregisterData
from src.models.event import Event


@pytest.mark.asyncio
async def test_create_ticket_usecase(
    sample_event: Event, ticket_repository, event_repository
):
    """Test CreateTicketUsecase."""
    mock_client = MagicMock()
    mock_client.register = AsyncMock(
        return_value=RegistrationData(ticket_id="test-ticket-id")
    )

    # Note: CreateTicketUsecase checks event status.
    sample_event.status = "published"

    usecase = CreateTicketUsecase(
        event_repo=event_repository, ticket_repo=ticket_repository, client=mock_client
    )

    result = await usecase.execute(
        event_id=sample_event.id,
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        seat="A1",
    )

    assert result.ticket_id == "test-ticket-id"
    mock_client.register.assert_called_once()


@pytest.mark.asyncio
async def test_delete_ticket_usecase(sample_event: Event, ticket_repository):
    """Test DeleteTicketUsecase."""
    mock_client = MagicMock()
    mock_client.unregister = AsyncMock(return_value=UnregisterData(success=True))

    # We need a ticket in the repo for DeleteTicketUsecase to find it
    from src.models.ticket import Ticket
    from datetime import datetime, timezone

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
