"""Outbox worker service for processing outbox records."""

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import async_session_maker
from src.core.settings import settings
from src.models.outbox import OutboxEventType, OutboxStatus
from src.repositories.outbox_repository import SQLAlchemyOutboxRepository
from src.services.capashino_client import CapashinoClient, CapashinoError

logger = logging.getLogger(__name__)


class OutboxWorker:
    """Worker for processing outbox records."""

    def __init__(self) -> None:
        """Initialize worker."""
        self._running = False
        self._task: asyncio.Task | None = None
        self._capashino = CapashinoClient()
        self._poll_interval = settings.outbox_poll_interval_seconds
        self._max_retries = settings.outbox_max_retries

    async def start(self) -> None:
        """Start the worker."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info("Outbox worker started")

    async def stop(self) -> None:
        """Stop the worker."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Outbox worker stopped")

    async def _run(self) -> None:
        """Main worker loop."""
        while self._running:
            try:
                await self._process_pending()
            except Exception as e:
                logger.error("Error processing outbox: %s", e)

            await asyncio.sleep(self._poll_interval)

    async def _process_pending(self) -> None:
        """Process pending outbox records."""
        async with async_session_maker() as session:
            repo = SQLAlchemyOutboxRepository(session)
            pending = await repo.get_pending(limit=50)

            for record in pending:
                await self._process_record(record, repo, session)

    async def _process_record(
        self,
        record,
        repo: SQLAlchemyOutboxRepository,
        session: AsyncSession,
    ) -> None:
        """Process a single outbox record.

        Args:
            record: Outbox record to process.
            repo: Outbox repository.
            session: Database session.
        """
        try:
            if record.event_type == OutboxEventType.TICKET_CREATED.value:
                await self._handle_ticket_created(record, repo, session)
            else:
                logger.warning("Unknown event type: %s", record.event_type)
                await repo.mark_failed(record, "Unknown event type")
                await session.commit()
        except CapashinoError as e:
            logger.error("Capashino error for record %s: %s", record.id, e.message)
            retry_count = int(record.retry_count)
            if retry_count >= self._max_retries:
                await repo.mark_failed(record, f"Max retries exceeded: {e.message}")
            else:
                record.status = OutboxStatus.PENDING.value
            await session.commit()
        except Exception as e:
            logger.error("Error processing record %s: %s", record.id, e)
            await repo.mark_failed(record, str(e))
            await session.commit()

    async def _handle_ticket_created(
        self,
        record,
        repo: SQLAlchemyOutboxRepository,
        session: AsyncSession,
    ) -> None:
        """Handle ticket_created event.

        Args:
            record: Outbox record.
            repo: Outbox repository.
            session: Database session.
        """
        payload = record.payload

        message = payload.get("message", "Вы успешно зарегистрированы на мероприятие")
        reference_id = payload.get("ticket_id")
        idempotency_key = payload.get("idempotency_key", f"outbox-{record.id}")

        await self._capashino.create_notification(
            message=message,
            reference_id=reference_id,
            idempotency_key=idempotency_key,
        )

        await repo.mark_sent(record)
        await session.commit()
        logger.info("Notification sent for ticket: %s", reference_id)


outbox_worker = OutboxWorker()
