"""Events endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.requests import Request

from src.core.dependencies import get_event_query_service
from src.schemas.api_schemas import (
    EventDetailResponse,
    EventsListResponse,
)
from src.services.event_query_service import EventQueryService

router = APIRouter()


@router.get("/events", response_model=EventsListResponse)
async def get_events(
    request: Request,
    service: Annotated[EventQueryService, Depends(get_event_query_service)],
    date_from: str | None = Query(
        None, description="Filter events after this date (YYYY-MM-DD)"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
) -> EventsListResponse:
    """Get all events with pagination.

    Args:
        request: FastAPI request object.
        service: Event query service.
        date_from: Optional date filter.
        page: Page number.
        page_size: Page size.

    Returns:
        Paginated list of events.
    """
    return await service.get_events(
        request=request,
        date_from=date_from,
        page=page,
        page_size=page_size,
    )


@router.get("/events/{event_id}", response_model=EventDetailResponse)
async def get_event(
    service: Annotated[EventQueryService, Depends(get_event_query_service)],
    event_id: str,
) -> EventDetailResponse:
    """Get event details.

    Args:
        service: Event query service.
        event_id: Event UUID.

    Returns:
        Event details.
    """
    return await service.get_event(event_id)
