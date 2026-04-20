"""Tickets endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from src.core.dependencies import (
    get_create_ticket_usecase,
    get_delete_ticket_usecase,
)
from src.schemas.api_schemas import (
    TicketCreateRequest,
    TicketCreateResponse,
    TicketDeleteResponse,
)
from src.usecases.create_ticket import CreateTicketUsecase
from src.usecases.delete_ticket import DeleteTicketUsecase
from src.usecases.exceptions import (
    EventNotFound,
    EventNotPublished,
    IdempotencyConflict,
    ProviderEventNotFound,
    ProviderOperationFailed,
    ProviderTicketNotFound,
    ProviderUnavailable,
    RegistrationDeadlinePassed,
    SeatNotAvailable,
    TicketNotFound,
    UsecaseError,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def _raise_http_error(exc: UsecaseError) -> None:
    """Convert use case domain exception to HTTPException."""
    if isinstance(exc, IdempotencyConflict):
        raise HTTPException(status_code=409, detail=exc.detail) from exc
    if isinstance(
        exc, (EventNotPublished, RegistrationDeadlinePassed, SeatNotAvailable)
    ):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if isinstance(
        exc,
        (EventNotFound, ProviderEventNotFound, TicketNotFound, ProviderTicketNotFound),
    ):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, ProviderUnavailable):
        raise HTTPException(
            status_code=503, detail="Events Provider is unavailable"
        ) from exc
    if isinstance(exc, ProviderOperationFailed):
        raise HTTPException(status_code=500, detail="Provider error") from exc
    raise HTTPException(status_code=500, detail="Internal server error") from exc


@router.post("/tickets", response_model=TicketCreateResponse, status_code=201)
async def create_ticket(
    request: TicketCreateRequest,
    usecase: Annotated[CreateTicketUsecase, Depends(get_create_ticket_usecase)],
) -> TicketCreateResponse:
    """Register for an event.

    Args:
        request: Ticket creation request data with event_id.
        usecase: Create ticket use case.

    Returns:
        Created ticket information.
    """
    try:
        result = await usecase.execute(
            event_id=request.event_id,
            first_name=request.first_name,
            last_name=request.last_name,
            email=request.email,
            seat=request.seat,
            idempotency_key=request.idempotency_key,
        )
    except UsecaseError as exc:
        _raise_http_error(exc)

    return TicketCreateResponse(ticket_id=result["ticket_id"])


@router.delete("/tickets/{ticket_id}", response_model=TicketDeleteResponse)
async def delete_ticket(
    ticket_id: str,
    usecase: Annotated[DeleteTicketUsecase, Depends(get_delete_ticket_usecase)],
) -> TicketDeleteResponse:
    """Cancel registration for an event.

    Args:
        ticket_id: Ticket UUID from path.
        usecase: Delete ticket use case.

    Returns:
        Deletion status.
    """
    try:
        await usecase.execute(ticket_id=ticket_id)
    except UsecaseError as exc:
        _raise_http_error(exc)

    return TicketDeleteResponse(success=True)
