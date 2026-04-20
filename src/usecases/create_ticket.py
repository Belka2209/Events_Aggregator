"""Create ticket usecase."""

import logging
from datetime import datetime, timezone
from typing import Any

from src.models.enums import EventStatus
from src.models.outbox import Outbox, OutboxEventType
from src.models.ticket import Ticket
from src.repositories.event_repository import EventRepository
from src.repositories.idempotency_repository import IdempotencyRepository
from src.repositories.outbox_repository import OutboxRepository
from src.repositories.ticket_repository import TicketRepository
from src.services.events_provider_client import (
    EventsProviderClient,
    ProviderError,
)
from src.usecases.exceptions import (
    EventNotFound,
    EventNotPublished,
    IdempotencyConflict,
    ProviderEventNotFound,
    ProviderOperationFailed,
    ProviderUnavailable,
    RegistrationDeadlinePassed,
    SeatNotAvailable,
)

logger = logging.getLogger(__name__)


class CreateTicketUsecase:
    """Use case for creating a ticket."""

    def __init__(
        self,
        event_repo: EventRepository,
        ticket_repo: TicketRepository,
        outbox_repo: OutboxRepository,
        idempotency_repo: IdempotencyRepository,
        client: EventsProviderClient,
    ):
        """Initialize use case."""
        self._event_repo = event_repo
        self._ticket_repo = ticket_repo
        self._outbox_repo = outbox_repo
        self._idempotency_repo = idempotency_repo
        self._client = client

    async def execute(
        self,
        event_id: str,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Execute ticket creation.

        Args:
            event_id: Event UUID.
            first_name: Participant first name.
            last_name: Participant last name.
            email: Participant email.
            seat: Seat identifier.
            idempotency_key: Optional idempotency key.

        Returns:
            Dictionary with ticket_id and event details.

        Raises:
            UsecaseError: If validation fails or provider returns an error.
        """
        if idempotency_key:
            existing = await self._idempotency_repo.get(idempotency_key)
            if existing:
                if existing.event_id != event_id:
                    raise IdempotencyConflict(
                        "Idempotency key already used with different event",
                    )
                if (
                    existing.request_data.get("seat") != seat
                    or existing.request_data.get("email") != email
                ):
                    raise IdempotencyConflict(
                        "Idempotency key already used with different data",
                    )
                logger.info(
                    "Returning existing ticket for idempotency key: %s",
                    idempotency_key,
                )
                return {
                    "ticket_id": existing.ticket_id,
                    "event_id": existing.event_id,
                }

        event = await self._event_repo.get(event_id)
        if not event:
            raise EventNotFound

        if event.status != EventStatus.PUBLISHED:
            raise EventNotPublished(event.status)

        if (
            event.registration_deadline
            and datetime.now(timezone.utc) > event.registration_deadline
        ):
            raise RegistrationDeadlinePassed

        registration = None
        booked_seat = seat
        candidate_seats: list[str] = [seat]
        tried_seats: set[str] = set()

        while candidate_seats:
            current_seat = candidate_seats.pop(0)
            tried_seats.add(current_seat)
            try:
                registration = await self._client.register(
                    event_id=event_id,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    seat=current_seat,
                )
                booked_seat = current_seat
                break
            except ProviderError as e:
                if e.status_code == 400:
                    # A seat may become unavailable between /seats and /tickets calls.
                    # Try the next актуальное место from provider before returning 400.
                    try:
                        seats_data = await self._client.get_seats(event_id)
                    except ProviderError:
                        raise SeatNotAvailable from e

                    fallback_seat = next(
                        (
                            available_seat
                            for available_seat in seats_data.seats
                            if available_seat not in tried_seats
                        ),
                        None,
                    )
                    if fallback_seat:
                        logger.warning(
                            "Seat %s unavailable for event %s, retrying with %s",
                            current_seat,
                            event_id,
                            fallback_seat,
                        )
                        candidate_seats.append(fallback_seat)
                        continue

                    raise SeatNotAvailable from e
                if e.status_code == 404:
                    raise ProviderEventNotFound from e
                if e.status_code == 503:
                    raise ProviderUnavailable from e
                logger.error("Provider error during registration: %s", e.detail)
                raise ProviderOperationFailed from e

        if registration is None:
            raise SeatNotAvailable

        ticket = Ticket(
            ticket_id=registration.ticket_id,
            event_id=event_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            seat=booked_seat,
            created_at=datetime.now(timezone.utc),
        )
        await self._ticket_repo.create(ticket)

        outbox_record = Outbox(
            event_type=OutboxEventType.TICKET_CREATED.value,
            payload={
                "ticket_id": ticket.ticket_id,
                "event_id": event_id,
                "event_name": event.name,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "seat": booked_seat,
                "message": f"Вы успешно зарегистрированы на мероприятие '{event.name}'",
                "idempotency_key": f"ticket-{ticket.ticket_id}",
            },
            status="pending",
        )
        await self._outbox_repo.create(outbox_record)

        if idempotency_key:
            await self._idempotency_repo.create(
                key=idempotency_key,
                ticket_id=ticket.ticket_id,
                event_id=event_id,
                request_data={
                    "event_id": event_id,
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "seat": seat,
                },
            )

        logger.info("Ticket created: %s for event %s", ticket.ticket_id, event_id)

        return {
            "ticket_id": ticket.ticket_id,
            "event_id": event_id,
        }
