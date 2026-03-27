"""Pydantic schemas for API."""

from datetime import datetime

from pydantic import BaseModel, Field


# Place schemas
class PlaceResponse(BaseModel):
    """Place response schema."""

    id: str
    name: str
    city: str
    address: str


class PlaceDetailResponse(BaseModel):
    """Place detail response schema with full information."""

    id: str
    name: str
    city: str
    address: str
    seats_pattern: str | None


# Event schemas
class EventResponse(BaseModel):
    """Event response schema."""

    id: str
    name: str
    place: PlaceResponse
    event_time: datetime
    registration_deadline: datetime | None
    status: str
    number_of_visitors: int


class EventDetailResponse(BaseModel):
    """Event detail response schema."""

    id: str
    name: str
    place: PlaceDetailResponse
    event_time: datetime
    registration_deadline: datetime | None
    status: str
    number_of_visitors: int


class EventsListResponse(BaseModel):
    """Events list response schema with pagination."""

    count: int
    next: str | None
    previous: str | None
    results: list[EventResponse]


# Seats schemas
class SeatsResponse(BaseModel):
    """Seats response schema."""

    event_id: str
    available_seats: list[str]


# Ticket schemas
class TicketCreateRequest(BaseModel):
    """Ticket create request schema."""

    event_id: str
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(
        ..., pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    )
    seat: str = Field(..., min_length=1, max_length=50)


class TicketCreateResponse(BaseModel):
    """Ticket create response schema."""

    ticket_id: str


class TicketDeleteResponse(BaseModel):
    """Ticket delete response schema."""

    success: bool


# Sync schemas
class SyncTriggerResponse(BaseModel):
    """Sync trigger response schema."""

    status: str
    message: str
    stats: dict | None = None


# Health schema
class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = "ok"
