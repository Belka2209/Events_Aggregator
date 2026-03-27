"""Events endpoints."""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.repositories.event_repository import SQLAlchemyEventRepository
from src.schemas.api_schemas import (
    EventDetailResponse,
    EventResponse,
    EventsListResponse,
    PlaceDetailResponse,
    PlaceResponse,
)

router = APIRouter()


def build_next_url(
    request: Request, page: int, page_size: int, date_from: str | None
) -> str | None:
    """Build next page URL."""
    base_url = str(request.url).split("?")[0]
    params = f"?page={page + 1}&page_size={page_size}"
    if date_from:
        params += f"&date_from={date_from}"
    return f"{base_url}{params}"


def build_previous_url(
    request: Request, page: int, page_size: int, date_from: str | None
) -> str | None:
    """Build previous page URL."""
    if page <= 1:
        return None
    base_url = str(request.url).split("?")[0]
    params = f"?page={page - 1}&page_size={page_size}"
    if date_from:
        params += f"&date_from={date_from}"
    return f"{base_url}{params}"


@router.get("/events", response_model=EventsListResponse)
async def get_events(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    date_from: str | None = Query(
        None, description="Filter events after this date (YYYY-MM-DD)"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
) -> EventsListResponse:
    """Get all events with pagination.

    Args:
        request: FastAPI request object.
        session: Database session.
        date_from: Optional date filter.
        page: Page number.
        page_size: Page size.

    Returns:
        Paginated list of events.
    """
    # Parse date_from
    date_from_dt: datetime | None = None
    if date_from:
        try:
            date_from_dt = datetime.strptime(date_from, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid date_from format. Use YYYY-MM-DD",
            )
    # Get repository
    repo = SQLAlchemyEventRepository(session)

    # Get events
    offset = (page - 1) * page_size
    events, total = await repo.get_all(
        date_from=date_from_dt,
        offset=offset,
        limit=page_size,
    )

    # Build response
    results = [
        EventResponse(
            id=event.id,
            name=event.name,
            place=PlaceResponse(
                id=event.place.id,
                name=event.place.name,
                city=event.place.city,
                address=event.place.address,
            ),
            event_time=event.event_time,
            registration_deadline=event.registration_deadline,
            status=event.status,
            number_of_visitors=event.number_of_visitors,
        )
        for event in events
    ]

    next_url = (
        build_next_url(request, page, page_size, date_from)
        if len(events) == page_size
        else None
    )
    previous_url = build_previous_url(request, page, page_size, date_from)

    return EventsListResponse(
        count=total,
        next=next_url,
        previous=previous_url,
        results=results,
    )


@router.get("/events/{event_id}", response_model=EventDetailResponse)
async def get_event(
    session: Annotated[AsyncSession, Depends(get_session)],
    event_id: str,
) -> EventDetailResponse:
    """Get event details.

    Args:
        session: Database session.
        event_id: Event UUID.

    Returns:
        Event details.
    """
    repo = SQLAlchemyEventRepository(session)
    event = await repo.get(event_id)

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return EventDetailResponse(
        id=event.id,
        name=event.name,
        place=PlaceDetailResponse(
            id=event.place.id,
            name=event.place.name,
            city=event.place.city,
            address=event.place.address,
            seats_pattern=event.place.seats_pattern,
        ),
        event_time=event.event_time,
        registration_deadline=event.registration_deadline,
        status=event.status,
        number_of_visitors=event.number_of_visitors,
    )
