"""
Status Routes
=============

System status and health endpoints.
"""

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.routes.auth import get_current_user, User
from app.api.dependencies import (
    get_monitor_service,
    get_updater_service,
    get_error_detector_service,
    get_error_fixer_service
)
from app.core.config import get_settings

router = APIRouter()

# Track startup time for uptime calculation
_startup_time = datetime.utcnow()


class ComponentStatus(BaseModel):
    """Status of a single component."""
    name: str
    status: str  # running, stopped, error
    details: Dict[str, Any] = {}


class SystemStatus(BaseModel):
    """Overall system status."""
    status: str  # running, stopped, error
    uptime_seconds: int
    last_poll: str = None
    active_errors: int = 0
    pending_updates: int = 0
    components: Dict[str, str] = {}


@router.get("", response_model=SystemStatus)
async def get_system_status(current_user: User = Depends(get_current_user)):
    """
    Get overall system status.

    Returns status of all components and key metrics.
    """
    from sqlalchemy import select, func
    from app.core.database import get_session
    from app.models.error import Error, ErrorStatus
    from app.models.module_update import ModuleUpdate, UpdateStatus

    monitor = get_monitor_service()
    updater = get_updater_service()
    detector = get_error_detector_service()
    fixer = get_error_fixer_service()

    # Calculate uptime
    uptime = int((datetime.utcnow() - _startup_time).total_seconds())

    # Get counts from database
    async with get_session() as session:
        # Active errors count
        result = await session.execute(
            select(func.count(Error.id)).where(
                Error.status.in_([ErrorStatus.DETECTED, ErrorStatus.QUEUED, ErrorStatus.FIXING])
            )
        )
        active_errors = result.scalar() or 0

        # Pending updates count
        result = await session.execute(
            select(func.count(ModuleUpdate.id)).where(
                ModuleUpdate.status == UpdateStatus.PENDING
            )
        )
        pending_updates = result.scalar() or 0

    # Determine overall status
    components = {
        "monitor": "running" if monitor and monitor.is_running else "stopped",
        "updater": "updating" if updater and updater.is_updating else "idle",
        "error_detector": "running" if detector and detector.is_running else "stopped",
        "error_fixer": "running" if fixer and fixer.is_running else "stopped",
    }

    all_running = all(
        s in ("running", "idle")
        for s in components.values()
    )
    overall_status = "running" if all_running else "degraded"

    return SystemStatus(
        status=overall_status,
        uptime_seconds=uptime,
        active_errors=active_errors,
        pending_updates=pending_updates,
        components=components
    )


@router.get("/components", response_model=list[ComponentStatus])
async def get_component_status(current_user: User = Depends(get_current_user)):
    """Get detailed status of each component."""
    monitor = get_monitor_service()
    updater = get_updater_service()
    detector = get_error_detector_service()
    fixer = get_error_fixer_service()
    settings = get_settings()

    components = []

    # Monitor status
    components.append(ComponentStatus(
        name="monitor",
        status="running" if monitor and monitor.is_running else "stopped",
        details={
            "polling_interval": settings.github.polling_interval,
            "repositories_count": len(settings.github.repositories)
        }
    ))

    # Updater status
    components.append(ComponentStatus(
        name="updater",
        status="updating" if updater and updater.is_updating else "idle",
        details={
            "backup_enabled": settings.backup.enabled,
            "backup_retention_days": settings.backup.retention_days
        }
    ))

    # Error detector status
    components.append(ComponentStatus(
        name="error_detector",
        status="running" if detector and detector.is_running else "stopped",
        details={
            "log_file": settings.odoo.log_file
        }
    ))

    # Error fixer status
    current_fix = fixer.current_fix if fixer else None
    components.append(ComponentStatus(
        name="error_fixer",
        status="fixing" if current_fix else ("running" if fixer and fixer.is_running else "stopped"),
        details={
            "current_fix": current_fix,
            "max_attempts": settings.retry.max_attempts,
            "claude_enabled": settings.claude.enabled
        }
    ))

    return components


@router.get("/metrics")
async def get_metrics(current_user: User = Depends(get_current_user)):
    """Get system metrics."""
    from sqlalchemy import select, func
    from app.core.database import get_session
    from app.models.error import Error, ErrorStatus, FixAttempt, FixAttemptStatus
    from app.models.module_update import ModuleUpdate, UpdateStatus
    from datetime import timedelta

    async with get_session() as session:
        today = datetime.utcnow().date()
        today_start = datetime.combine(today, datetime.min.time())

        # Updates today
        result = await session.execute(
            select(func.count(ModuleUpdate.id)).where(
                ModuleUpdate.created_at >= today_start
            )
        )
        updates_today = result.scalar() or 0

        # Successful updates today
        result = await session.execute(
            select(func.count(ModuleUpdate.id)).where(
                ModuleUpdate.created_at >= today_start,
                ModuleUpdate.status == UpdateStatus.SUCCESS
            )
        )
        successful_updates_today = result.scalar() or 0

        # Errors detected today
        result = await session.execute(
            select(func.count(Error.id)).where(
                Error.detected_at >= today_start
            )
        )
        errors_today = result.scalar() or 0

        # Errors resolved today
        result = await session.execute(
            select(func.count(Error.id)).where(
                Error.resolved_at >= today_start
            )
        )
        resolved_today = result.scalar() or 0

        # Fix success rate (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        result = await session.execute(
            select(func.count(FixAttempt.id)).where(
                FixAttempt.started_at >= week_ago
            )
        )
        total_attempts = result.scalar() or 0

        result = await session.execute(
            select(func.count(FixAttempt.id)).where(
                FixAttempt.started_at >= week_ago,
                FixAttempt.status == FixAttemptStatus.SUCCESS
            )
        )
        successful_attempts = result.scalar() or 0

        success_rate = (successful_attempts / total_attempts * 100) if total_attempts > 0 else 0

    return {
        "updates_today": updates_today,
        "successful_updates_today": successful_updates_today,
        "errors_today": errors_today,
        "resolved_today": resolved_today,
        "fix_success_rate_7d": round(success_rate, 1),
        "total_fix_attempts_7d": total_attempts,
        "successful_fixes_7d": successful_attempts,
    }
