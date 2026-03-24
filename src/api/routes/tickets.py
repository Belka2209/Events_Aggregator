"""Tickets endpoints."""

import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.models.ticket import Ticket
from src.repositories.event_repository import SQLAlchemyEventRepository
from src.repositories.ticket_repository import SQLAlchemyTicketRepository
from src.schemas.api_schemas import (
    TicketCreateRequest,
    TicketCreateResponse,
    TicketDeleteResponse,
)
from src.services.events_provider_client import EventsProviderClient

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/tickets", response_model=TicketCreateResponse, status_code=201)
async def create_ticket(
    request: TicketCreateRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TicketCreateResponse:
    """Register for an event.

    Args:
        request: Ticket creation request data with event_id.
        session: Database session.

    Returns:
        Created ticket information.
    """
    event_id = request.event_id
    
    # Get event from local DB
    event_repo = SQLAlchemyEventRepository(session)
    event = await event_repo.get(event_id)

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Validate event status
    if event.status != "published":
        raise HTTPException(
            status_code=400,
            detail=f"Event is not published (current status: {event.status})",
        )

    # Validate registration deadline
    if event.registration_deadline:
        now = datetime.now(timezone.utc)
        if now > event.registration_deadline:
            raise HTTPException(
                status_code=400, detail="Registration deadline has passed"
            )

    # Register with Events Provider API
    client = EventsProviderClient()
    try:
        registration = await client.register(
            event_id=event_id,
            first_name=request.first_name,
            last_name=request.last_name,
            email=request.email,
            seat=request.seat,
        )
    except HTTPException as e:
        if e.status_code == 400:
            raise HTTPException(status_code=400, detail="Seat is not available")
        if e.status_code == 404:
            raise HTTPException(status_code=400, detail="Event not found in provider")
        raise

    # Save ticket to local DB
    ticket_repo = SQLAlchemyTicketRepository(session)
    ticket = Ticket(
        ticket_id=registration.ticket_id,
        event_id=event_id,
        first_name=request.first_name,
        last_name=request.last_name,
        email=request.email,
        seat=request.seat,
        created_at=datetime.now(timezone.utc),
    )
    await ticket_repo.create(ticket)

    logger.info(
        f"Ticket created: {registration.ticket_id} for event {event_id}"
    )

    return TicketCreateResponse(ticket_id=registration.ticket_id)


@router.delete("/tickets/{ticket_id}", response_model=TicketDeleteResponse)
async def delete_ticket(
    ticket_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TicketDeleteResponse:
    """Cancel registration for an event.

    Args:
        ticket_id: Ticket UUID from path.
        session: Database session.

    Returns:
        Deletion status.
    """
    # Get ticket from local DB
    ticket_repo = SQLAlchemyTicketRepository(session)
    ticket = await ticket_repo.get_by_ticket_id(ticket_id)

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Unregister from Events Provider API
    client = EventsProviderClient()
    try:
        await client.unregister(event_id=ticket.event_id, ticket_id=ticket_id)
    except HTTPException as e:
        logger.error(f"Provider error unregistering ticket {ticket_id}: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"System error unregistering ticket {ticket_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to unregister from provider"
        )

    # Delete ticket from local DB
    await ticket_repo.delete(ticket)

    logger.info(f"Ticket deleted: {ticket_id}")

    return TicketDeleteResponse(success=True)
