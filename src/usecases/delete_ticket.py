"""Delete ticket usecase."""

import logging

from fastapi import HTTPException

from src.repositories.ticket_repository import TicketRepository
from src.services.events_provider_client import EventsProviderClient, ProviderError

logger = logging.getLogger(__name__)


class DeleteTicketUsecase:
    """Use case for deleting a ticket."""

    def __init__(
        self,
        ticket_repo: TicketRepository,
        client: EventsProviderClient,
    ):
        """Initialize use case."""
        self._ticket_repo = ticket_repo
        self._client = client

    async def execute(self, ticket_id: str) -> None:
        """Execute ticket deletion.

        Args:
            ticket_id: Ticket UUID.

        Raises:
            HTTPException: If ticket is not found or provider fails.
        """
        # Get ticket from local DB
        ticket = await self._ticket_repo.get_by_ticket_id(ticket_id)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")

        # Unregister from Events Provider API
        try:
            await self._client.unregister(event_id=ticket.event_id, ticket_id=ticket_id)
        except ProviderError as e:
            logger.error(
                "Provider error unregistering ticket %s: %s", ticket_id, e.detail
            )
            raise HTTPException(
                status_code=500, detail="Failed to unregister from provider"
            )

        # Delete ticket from local DB
        await self._ticket_repo.delete(ticket)
        # await self._ticket_repo.commit()

        logger.info("Ticket deleted: %s", ticket_id)
