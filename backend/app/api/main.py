"""
FastAPI Application
===================

Main FastAPI application with REST API and WebSocket support.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.core.config import get_settings
from app.core.database import init_db, close_db
from app.services.event_bus import get_event_bus
from app.services.monitor import MonitorService
from app.services.updater import UpdaterService
from app.services.error_detector import ErrorDetectorService
from app.services.error_fixer import ErrorFixerService
from app.api.dependencies import set_services

logger = structlog.get_logger()

# Service instances
monitor_service: MonitorService = None
updater_service: UpdaterService = None
error_detector_service: ErrorDetectorService = None
error_fixer_service: ErrorFixerService = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager."""
    global monitor_service, updater_service, error_detector_service, error_fixer_service

    settings = get_settings()
    event_bus = get_event_bus()

    # Initialize database
    await init_db()
    logger.info("database_initialized")

    # Initialize services
    monitor_service = MonitorService(event_bus)
    updater_service = UpdaterService(event_bus)
    error_detector_service = ErrorDetectorService(event_bus)
    error_fixer_service = ErrorFixerService(event_bus)

    # Register services with dependencies module
    set_services(monitor_service, updater_service, error_detector_service, error_fixer_service)

    # Start services
    await monitor_service.start()
    await error_detector_service.start()
    await error_fixer_service.start()

    logger.info("services_started")

    yield

    # Cleanup
    await monitor_service.stop()
    await error_detector_service.stop()
    await error_fixer_service.stop()
    await close_db()

    logger.info("services_stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    # Import routes here to avoid circular imports
    from app.api.routes import auth, status, updates, errors, config, websocket

    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Odoo Automation Service - Automated monitoring and error resolution",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
    app.include_router(status.router, prefix="/api/v1/status", tags=["Status"])
    app.include_router(updates.router, prefix="/api/v1/updates", tags=["Updates"])
    app.include_router(errors.router, prefix="/api/v1/errors", tags=["Errors"])
    app.include_router(config.router, prefix="/api/v1/config", tags=["Configuration"])
    app.include_router(websocket.router, tags=["WebSocket"])

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": settings.app_version,
        }

    return app


# Create application instance
app = create_app()
