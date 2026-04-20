"""Seats endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends

from src.core.dependencies import get_seat_query_service
from src.schemas.api_schemas import SeatsResponse
from src.services.seat_query_service import SeatQueryService

router = APIRouter()


@router.get("/events/{event_id}/seats", response_model=SeatsResponse)
async def get_seats(
    service: Annotated[SeatQueryService, Depends(get_seat_query_service)],
    event_id: str,
) -> SeatsResponse:
    """Get available seats for an event.

    Args:
        service: Seat query service.
        event_id: Event UUID.

    Returns:
        List of available seats.
    """
    return await service.get_seats(event_id)
