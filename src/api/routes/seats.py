"""Seats endpoints."""

import logging
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.repositories.event_repository import SQLAlchemyEventRepository
from src.schemas.api_schemas import SeatsResponse
from src.services.events_provider_client import EventsProviderClient

router = APIRouter()
logger = logging.getLogger(__name__)

# Simple in-memory cache for seats
_seats_cache: dict[str, tuple[list[str], datetime]] = {}
_CACHE_TTL_SECONDS = 30


@router.get("/events/{event_id}/seats", response_model=SeatsResponse)
async def get_seats(
    session: Annotated[AsyncSession, Depends(get_session)],
    event_id: str,
) -> SeatsResponse:
    """Get available seats for an event.

    Args:
        session: Database session.
        event_id: Event UUID.

    Returns:
        List of available seats.
    """
    # Check cache
    now = datetime.now()
    if event_id in _seats_cache:
        cached_seats, cached_at = _seats_cache[event_id]
        if now - cached_at < timedelta(seconds=_CACHE_TTL_SECONDS):
            logger.debug(f"Returning cached seats for event {event_id}")
            return SeatsResponse(event_id=event_id, available_seats=cached_seats)

    # Verify event exists in local DB
    event_repo = SQLAlchemyEventRepository(session)
    event = await event_repo.get(event_id)

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Get seats from Events Provider API
    client = EventsProviderClient()
    try:
        seats_data = await client.get_seats(event_id)
    except Exception as e:
        logger.error(f"Error getting seats for event {event_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get seats from provider")

    # Update cache
    _seats_cache[event_id] = (seats_data.seats, now)

    return SeatsResponse(event_id=event_id, available_seats=seats_data.seats)
