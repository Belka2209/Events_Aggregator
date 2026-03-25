"""Application dependencies."""

from src.core.settings import settings
from src.services.events_provider_client import EventsProviderClient


def get_events_provider_client() -> EventsProviderClient:
    """Get events provider client."""
    return EventsProviderClient(api_key=settings.events_provider_api_key)
