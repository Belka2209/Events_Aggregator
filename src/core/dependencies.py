"""Application dependencies."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.settings import settings
from src.repositories.event_repository import SQLAlchemyEventRepository
from src.repositories.idempotency_repository import SQLAlchemyIdempotencyRepository
from src.repositories.outbox_repository import SQLAlchemyOutboxRepository
from src.repositories.ticket_repository import SQLAlchemyTicketRepository
from src.services.event_query_service import EventQueryService
from src.services.events_provider_client import EventsProviderClient
from src.services.seat_query_service import SeatQueryService
from src.usecases.create_ticket import CreateTicketUsecase
from src.usecases.delete_ticket import DeleteTicketUsecase


def get_events_provider_client() -> EventsProviderClient:
    """Get events provider client."""
    return EventsProviderClient(api_key=settings.events_provider_api_key)


def get_event_query_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> EventQueryService:
    """Get event query service."""
    return EventQueryService(SQLAlchemyEventRepository(session))


def get_seat_query_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    client: EventsProviderClient = Depends(get_events_provider_client),
) -> SeatQueryService:
    """Get seat query service."""
    return SeatQueryService(
        event_repo=SQLAlchemyEventRepository(session),
        client=client,
    )


def get_create_ticket_usecase(
    session: Annotated[AsyncSession, Depends(get_session)],
    client: EventsProviderClient = Depends(get_events_provider_client),
) -> CreateTicketUsecase:
    """Get create ticket use case."""
    return CreateTicketUsecase(
        event_repo=SQLAlchemyEventRepository(session),
        ticket_repo=SQLAlchemyTicketRepository(session),
        outbox_repo=SQLAlchemyOutboxRepository(session),
        idempotency_repo=SQLAlchemyIdempotencyRepository(session),
        client=client,
    )


def get_delete_ticket_usecase(
    session: Annotated[AsyncSession, Depends(get_session)],
    client: EventsProviderClient = Depends(get_events_provider_client),
) -> DeleteTicketUsecase:
    """Get delete ticket use case."""
    return DeleteTicketUsecase(
        ticket_repo=SQLAlchemyTicketRepository(session),
        client=client,
    )
