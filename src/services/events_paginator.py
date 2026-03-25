"""Events paginator for iterating through all events."""

import logging
from collections.abc import AsyncIterator

from src.services.events_provider_client import EventData, EventsProviderClient

logger = logging.getLogger(__name__)


class EventsPaginator:
    """Paginator for iterating through all events from Events Provider API."""

    def __init__(self, client: EventsProviderClient, changed_at: str):
        """Initialize the paginator.

        Args:
            client: EventsProviderClient instance.
            changed_at: Date filter in YYYY-MM-DD format.
        """
        self._client = client
        self._changed_at = changed_at

    def __aiter__(self) -> AsyncIterator[EventData]:
        """Return async iterator."""
        return self._paginate()

    async def _paginate(self) -> AsyncIterator[EventData]:
        """Iterate through all pages of events."""
        cursor: str | None = None
        page = 1

        while True:
            logger.debug("Fetching page %d with cursor=%s", page, cursor)

            events, next_cursor = await self._client.events(
                changed_at=self._changed_at,
                cursor=cursor,
            )

            logger.debug("Got %d events, next_cursor=%s", len(events), next_cursor)

            for event in events:
                yield event

            if next_cursor is None:
                logger.debug("No more pages")
                break

            cursor = self._extract_cursor(next_cursor)
            page += 1
            logger.debug("Next cursor extracted: %s", cursor)

    def _extract_cursor(self, next_url: str) -> str | None:
        """Extract cursor from next URL.

        Args:
            next_url: Full URL with cursor parameter.

        Returns:
            Cursor string or None.
        """
        if not next_url:
            return None

        # Parse cursor from URL
        if "cursor=" in next_url:
            return next_url.split("cursor=")[1]

        return None
