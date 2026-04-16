"""Tickets endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.dependencies import get_events_provider_client
from src.repositories.event_repository import SQLAlchemyEventRepository
from src.repositories.idempotency_repository import SQLAlchemyIdempotencyRepository
from src.repositories.outbox_repository import SQLAlchemyOutboxRepository
from src.repositories.ticket_repository import SQLAlchemyTicketRepository
from src.schemas.api_schemas import (
    TicketCreateRequest,
    TicketCreateResponse,
    TicketDeleteResponse,
)
from src.services.events_provider_client import EventsProviderClient
from src.usecases.create_ticket import CreateTicketUsecase
from src.usecases.delete_ticket import DeleteTicketUsecase

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/tickets", response_model=TicketCreateResponse, status_code=201)
async def create_ticket(
    request: TicketCreateRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    client: EventsProviderClient = Depends(get_events_provider_client),
) -> TicketCreateResponse:
    """Register for an event.

    Args:
        request: Ticket creation request data with event_id.
        session: Database session.
        client: Events Provider client.

    Returns:
        Created ticket information.
    """
    event_repo = SQLAlchemyEventRepository(session)
    ticket_repo = SQLAlchemyTicketRepository(session)
    outbox_repo = SQLAlchemyOutboxRepository(session)
    idempotency_repo = SQLAlchemyIdempotencyRepository(session)
    usecase = CreateTicketUsecase(
        event_repo, ticket_repo, outbox_repo, idempotency_repo, client
    )

    result = await usecase.execute(
        event_id=request.event_id,
        first_name=request.first_name,
        last_name=request.last_name,
        email=request.email,
        seat=request.seat,
        idempotency_key=request.idempotency_key,
    )

    return TicketCreateResponse(ticket_id=result["ticket_id"])


@router.delete("/tickets/{ticket_id}", response_model=TicketDeleteResponse)
async def delete_ticket(
    ticket_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    client: EventsProviderClient = Depends(get_events_provider_client),
) -> TicketDeleteResponse:
    """Cancel registration for an event.

    Args:
        ticket_id: Ticket UUID from path.
        session: Database session.
        client: Events Provider client.

    Returns:
        Deletion status.
    """
    ticket_repo = SQLAlchemyTicketRepository(session)
    usecase = DeleteTicketUsecase(ticket_repo, client)

    await usecase.execute(ticket_id=ticket_id)

    return TicketDeleteResponse(success=True)
