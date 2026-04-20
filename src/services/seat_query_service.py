"""Service layer for seat query endpoint."""

import logging

from fastapi import HTTPException

from src.repositories.event_repository import EventRepository
from src.schemas.api_schemas import SeatsResponse
from src.services.events_provider_client import EventsProviderClient, ProviderError

logger = logging.getLogger(__name__)


class SeatQueryService:
    """Business logic for querying available seats."""

    def __init__(
        self,
        event_repo: EventRepository,
        client: EventsProviderClient,
    ):
        self._event_repo = event_repo
        self._client = client

    async def get_seats(self, event_id: str) -> SeatsResponse:
        """Return available seats for event."""
        event = await self._event_repo.get(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        try:
            seats_data = await self._client.get_seats(event_id)
        except ProviderError as exc:
            logger.error("Provider error getting seats for event %s: %s", event_id, exc)
            if exc.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail="Event not found in provider",
                ) from exc
            if exc.status_code == 503:
                raise HTTPException(
                    status_code=503,
                    detail="Events Provider is unavailable",
                ) from exc
            raise HTTPException(
                status_code=500,
                detail="Failed to get seats from provider",
            ) from exc

        return SeatsResponse(event_id=event_id, available_seats=seats_data.seats)
