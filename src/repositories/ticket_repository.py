"""Ticket repository."""

from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.ticket import Ticket


class TicketRepository(Protocol):
    """Ticket repository protocol."""

    async def get(self, ticket_id: str) -> Ticket | None:
        """Get ticket by ID."""
        ...

    async def get_by_ticket_id(self, ticket_id: str) -> Ticket | None:
        """Get ticket by ticket_id (external ID)."""
        ...

    async def create(self, ticket: Ticket) -> Ticket:
        """Create ticket."""
        ...

    async def delete(self, ticket: Ticket) -> None:
        """Delete ticket."""
        ...


class SQLAlchemyTicketRepository:
    """SQLAlchemy implementation of TicketRepository."""

    def __init__(self, session: AsyncSession):
        """Initialize repository.

        Args:
            session: Async database session.
        """
        self._session = session

    async def get(self, ticket_id: str) -> Ticket | None:
        """Get ticket by internal ID.

        Args:
            ticket_id: Ticket UUID.

        Returns:
            Ticket or None.
        """
        result = await self._session.execute(
            select(Ticket).options(selectinload(Ticket.event)).where(Ticket.id == ticket_id),
        )
        return result.scalar_one_or_none()

    async def get_by_ticket_id(self, ticket_id: str) -> Ticket | None:
        """Get ticket by external ticket_id.

        Args:
            ticket_id: External ticket UUID.

        Returns:
            Ticket or None.
        """
        result = await self._session.execute(
            select(Ticket).options(selectinload(Ticket.event)).where(Ticket.ticket_id == ticket_id),
        )
        return result.scalar_one_or_none()

    async def create(self, ticket: Ticket) -> Ticket:
        """Create ticket.

        Args:
            ticket: Ticket to create.

        Returns:
            Created ticket.
        """
        self._session.add(ticket)
        await self._session.flush()
        return ticket

    async def delete(self, ticket: Ticket) -> None:
        """Delete ticket.

        Args:
            ticket: Ticket to delete.
        """
        await self._session.delete(ticket)
