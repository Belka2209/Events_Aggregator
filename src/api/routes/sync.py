"""Sync endpoints."""

import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.repositories.event_repository import SQLAlchemyEventRepository
from src.repositories.place_repository import SQLAlchemyPlaceRepository
from src.repositories.sync_state_repository import SQLAlchemySyncStateRepository
from src.schemas.api_schemas import SyncTriggerResponse
from src.services.events_provider_client import EventsProviderClient
from src.usecases.sync_events import SyncEventsUsecase

router = APIRouter()
logger = logging.getLogger(__name__)


# Хранилище статуса синхронизации (in-memory, для продакшена лучше использовать Redis)
_sync_status = {
    "is_running": False,
    "last_sync_stats": None,
    "last_sync_error": None,
}


@router.get("/sync/status")
async def sync_status():
    """Get current sync status."""
    return {
        "is_running": _sync_status["is_running"],
        "last_sync_stats": _sync_status["last_sync_stats"],
        "last_sync_error": _sync_status["last_sync_error"],
    }


@router.post("/sync/trigger", response_model=SyncTriggerResponse)
async def trigger_sync(
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> SyncTriggerResponse:
    """Trigger manual synchronization in background.

    Returns:
        Sync status and statistics.
    """
    # Проверяем, не запущена ли уже синхронизация
    if _sync_status["is_running"]:
        return SyncTriggerResponse(
            status="already_running",
            message="Synchronization is already in progress",
            stats=None,
        )

    logger.info("Manual sync triggered")

    # Создаем репозитории
    event_repo = SQLAlchemyEventRepository(session)
    place_repo = SQLAlchemyPlaceRepository(session)
    sync_state_repo = SQLAlchemySyncStateRepository(session)

    # Создаем клиент и usecase
    client = EventsProviderClient()
    usecase = SyncEventsUsecase(
        client=client,
        event_repo=event_repo,
        place_repo=place_repo,
        sync_state_repo=sync_state_repo,
    )

    # Запускаем синхронизацию в фоне
    background_tasks.add_task(
        _run_sync,
        usecase,
    )

    return SyncTriggerResponse(
        status="started",
        message="Synchronization started in background",
        stats=None,
    )


async def _run_sync(usecase: SyncEventsUsecase) -> None:
    """Run sync in background."""
    _sync_status["is_running"] = True
    _sync_status["last_sync_error"] = None

    try:
        logger.info("Starting background sync...")
        stats = await usecase.execute()
        _sync_status["last_sync_stats"] = stats
        logger.info(f"Background sync completed: {stats}")
    except Exception as e:
        _sync_status["last_sync_error"] = str(e)
        logger.error(f"Background sync failed: {e}", exc_info=True)
    finally:
        _sync_status["is_running"] = False