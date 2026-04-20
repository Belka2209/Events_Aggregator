"""Shared model enums."""

from enum import Enum


class EventStatus(str, Enum):
    """Event lifecycle status."""

    NEW = "new"
    ACTIVE = "active"
    PUBLISHED = "published"
    REGISTRATION_CLOSED = "registration_closed"
    FINISHED = "finished"
