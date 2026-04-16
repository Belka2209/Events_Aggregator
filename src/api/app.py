"""FastAPI application."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.api.routes import events, health, seats, sync, tickets
from src.core.database import engine
from src.core.settings import settings
from src.models import Base
from src.services.background_sync import BackgroundSyncService
from src.services.outbox_worker import outbox_worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

_background_sync_service: BackgroundSyncService | None = None


def _init_sentry() -> None:
    """Initialize Sentry/GlitchTip integration."""
    if not settings.glitchtip_dsn:
        logger.info("GlitchTip DSN not configured, skipping initialization")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        sentry_sdk.init(
            dsn=settings.glitchtip_dsn,
            integrations=[FastApiIntegration()],
            environment="production",
        )
        logger.info("GlitchTip initialized successfully")
    except ImportError:
        logger.warning("sentry-sdk not installed, skipping GlitchTip integration")
    except Exception as e:
        logger.error("Failed to initialize GlitchTip: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    global _background_sync_service

    logger.info("Application startup")

    _init_sentry()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database tables created")

    try:
        _background_sync_service = BackgroundSyncService()
        await _background_sync_service.start()
        logger.info("Background sync service started successfully")
    except Exception as e:
        logger.error("Failed to start background sync service: %s", e)
        _background_sync_service = None

    try:
        await outbox_worker.start()
        logger.info("Outbox worker started successfully")
    except Exception as e:
        logger.error("Failed to start outbox worker: %s", e)

    yield

    logger.info("Application shutdown")

    if _background_sync_service:
        await _background_sync_service.stop()

    await outbox_worker.stop()


app = FastAPI(
    title="Events Aggregator",
    description="Backend service for aggregating events from Events Provider API",
    version="0.2.0",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Validation exception handler."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.errors()},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler."""
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(sync.router, prefix="/api", tags=["Sync"])
app.include_router(events.router, prefix="/api", tags=["Events"])
app.include_router(seats.router, prefix="/api", tags=["Seats"])
app.include_router(tickets.router, prefix="/api", tags=["Tickets"])


@app.get("/")
async def root() -> dict:
    """Root endpoint."""
    return {"message": "Events Aggregator API", "status": "ok"}
