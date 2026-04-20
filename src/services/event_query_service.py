"""Service layer for event query endpoints."""

from datetime import datetime, timezone

from fastapi import HTTPException
from fastapi.requests import Request

from src.repositories.event_repository import EventRepository
from src.schemas.api_schemas import (
    EventDetailResponse,
    EventResponse,
    EventsListResponse,
    PlaceDetailResponse,
    PlaceResponse,
)


def _parse_date_from(date_from: str | None) -> datetime | None:
    """Parse date_from in YYYY-MM-DD format to UTC datetime."""
    if not date_from:
        return None

    try:
        return datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid date_from format. Use YYYY-MM-DD",
        ) from exc


def _build_next_url(
    request: Request, page: int, page_size: int, date_from: str | None
) -> str | None:
    """Build next page URL."""
    base_url = str(request.url).split("?")[0]
    params = f"?page={page + 1}&page_size={page_size}"
    if date_from:
        params += f"&date_from={date_from}"
    return f"{base_url}{params}"


def _build_previous_url(
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


class EventQueryService:
    """Business logic for event query endpoints."""

    def __init__(self, event_repo: EventRepository):
        self._event_repo = event_repo

    async def get_events(
        self,
        request: Request,
        date_from: str | None,
        page: int,
        page_size: int,
    ) -> EventsListResponse:
        """Get all events with pagination."""
        date_from_dt = _parse_date_from(date_from)
        offset = (page - 1) * page_size
        events, total = await self._event_repo.get_all(
            date_from=date_from_dt,
            offset=offset,
            limit=page_size,
        )

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
            _build_next_url(request, page, page_size, date_from)
            if len(events) == page_size
            else None
        )
        previous_url = _build_previous_url(request, page, page_size, date_from)

        return EventsListResponse(
            count=total,
            next=next_url,
            previous=previous_url,
            results=results,
        )

    async def get_event(self, event_id: str) -> EventDetailResponse:
        """Get event details by id."""
        event = await self._event_repo.get(event_id)
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
