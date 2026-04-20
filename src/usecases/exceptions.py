"""Domain exceptions for use cases."""

from src.models.enums import EventStatus


class UsecaseError(Exception):
    """Base class for use case errors."""


class EventNotFound(UsecaseError):
    """Event was not found in local storage."""

    def __init__(self):
        super().__init__("Event not found")


class EventNotPublished(UsecaseError):
    """Event is not in published status."""

    def __init__(self, status: EventStatus):
        self.status = status
        super().__init__(f"Event is not published (current status: {status.value})")


class RegistrationDeadlinePassed(UsecaseError):
    """Registration deadline has already passed."""

    def __init__(self):
        super().__init__("Registration deadline has passed")


class IdempotencyConflict(UsecaseError):
    """Idempotency key is reused with different data."""

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class SeatNotAvailable(UsecaseError):
    """Requested seat cannot be booked."""

    def __init__(self):
        super().__init__("Seat is not available")


class ProviderEventNotFound(UsecaseError):
    """Event not found in provider."""

    def __init__(self):
        super().__init__("Event not found in provider")


class ProviderTicketNotFound(UsecaseError):
    """Ticket not found in provider."""

    def __init__(self):
        super().__init__("Ticket not found in provider")


class ProviderUnavailable(UsecaseError):
    """Provider is unavailable."""

    def __init__(self):
        super().__init__("Events Provider is unavailable")


class ProviderOperationFailed(UsecaseError):
    """Provider operation failed with unknown error."""

    def __init__(self, detail: str = "Provider error"):
        self.detail = detail
        super().__init__(detail)


class TicketNotFound(UsecaseError):
    """Ticket was not found in local storage."""

    def __init__(self):
        super().__init__("Ticket not found")
