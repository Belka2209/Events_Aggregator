"""Seats endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.dependencies import get_events_provider_client
from src.repositories.event_repository import SQLAlchemyEventRepository
from src.schemas.api_schemas import SeatsResponse
from src.services.events_provider_client import EventsProviderClient

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/events/{event_id}/seats", response_model=SeatsResponse)
async def get_seats(
    session: Annotated[AsyncSession, Depends(get_session)],
    event_id: str,
    client: EventsProviderClient = Depends(get_events_provider_client),
) -> SeatsResponse:
    """Get available seats for an event.

    Args:
        session: Database session.
        event_id: Event UUID.
        client: Events Provider client.

    Returns:
        List of available seats.
    """
    # Verify event exists in local DB
    event_repo = SQLAlchemyEventRepository(session)
    event = await event_repo.get(event_id)

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Get seats from Events Provider API
    try:
        seats_data = await client.get_seats(event_id)
    except Exception as e:
        logger.error("Error getting seats for event %s: %s", event_id, e)
        raise HTTPException(status_code=500, detail="Failed to get seats from provider")

    return SeatsResponse(event_id=event_id, available_seats=seats_data.seats)
