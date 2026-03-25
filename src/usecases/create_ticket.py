"""Create ticket usecase."""

import logging
from datetime import datetime, timezone

from fastapi import HTTPException

from src.models.ticket import Ticket
from src.repositories.event_repository import EventRepository
from src.repositories.ticket_repository import TicketRepository
from src.services.events_provider_client import EventsProviderClient, ProviderError

logger = logging.getLogger(__name__)


class CreateTicketUsecase:
    """Use case for creating a ticket."""

    def __init__(
        self,
        event_repo: EventRepository,
        ticket_repo: TicketRepository,
        client: EventsProviderClient,
    ):
        """Initialize use case."""
        self._event_repo = event_repo
        self._ticket_repo = ticket_repo
        self._client = client

    async def execute(
        self,
        event_id: str,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> Ticket:
        """Execute ticket creation.

        Args:
            event_id: Event UUID.
            first_name: Participant first name.
            last_name: Participant last name.
            email: Participant email.
            seat: Seat identifier.

        Returns:
            Created ticket.

        Raises:
            HTTPException: If validation fails or provider returns an error.
        """
        # Get event from local DB
        event = await self._event_repo.get(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        # Validate event status
        if event.status != "published":
            raise HTTPException(
                status_code=400,
                detail=f"Event is not published (current status: {event.status})",
            )

        # Validate registration deadline
        if event.registration_deadline and datetime.now(timezone.utc) > event.registration_deadline:
            raise HTTPException(
                status_code=400, detail="Registration deadline has passed"
            )

        # Register with Events Provider API
        try:
            registration = await self._client.register(
                event_id=event_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                seat=seat,
            )
        except ProviderError as e:
            if e.status_code == 400:
                raise HTTPException(status_code=400, detail="Seat is not available")
            if e.status_code == 404:
                raise HTTPException(status_code=404, detail="Event not found in provider")
            logger.error("Provider error during registration: %s", e.detail)
            raise HTTPException(status_code=500, detail="Provider error")

        # Save ticket to local DB
        ticket = Ticket(
            ticket_id=registration.ticket_id,
            event_id=event_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            seat=seat,
            created_at=datetime.now(timezone.utc),
        )
        await self._ticket_repo.create(ticket)
        # await self._ticket_repo.commit()

        logger.info(f"Ticket created: {ticket.ticket_id} for event {event.id}")
        return ticket
