"""FastAPI application."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.api.routes import events, health, seats, sync, tickets
from src.core.database import engine
from src.models import Base
from src.services.background_sync import BackgroundSyncService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global background sync service
_background_sync_service: BackgroundSyncService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    global _background_sync_service

    # Startup
    logger.info("Application startup")

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database tables created")

    # Start background sync service
    try:
        _background_sync_service = BackgroundSyncService()
        await _background_sync_service.start()
        logger.info("Background sync service started successfully")
    except Exception as e:
        logger.error("Failed to start background sync service: %s", e)
        _background_sync_service = None

    yield

    # Shutdown
    logger.info("Application shutdown")

    # Stop background sync service
    if _background_sync_service:
        await _background_sync_service.stop()


app = FastAPI(
    title="Events Aggregator",
    description="Backend service for aggregating events from Events Provider API",
    version="0.1.0",
    lifespan=lifespan,
)


# Exception handlers
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


# Include routers
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(sync.router, prefix="/api", tags=["Sync"])
app.include_router(events.router, prefix="/api", tags=["Events"])
app.include_router(seats.router, prefix="/api", tags=["Seats"])
app.include_router(tickets.router, prefix="/api", tags=["Tickets"])


@app.get("/")
async def root() -> dict:
    """Root endpoint."""
    return {"message": "Events Aggregator API", "status": "ok"}
