"""
API Dependencies
================

Dependency injection for FastAPI routes.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.monitor import MonitorService
    from app.services.updater import UpdaterService
    from app.services.error_detector import ErrorDetectorService
    from app.services.error_fixer import ErrorFixerService

# Service instances (set by main.py during startup)
_monitor_service = None
_updater_service = None
_error_detector_service = None
_error_fixer_service = None


def set_services(monitor, updater, error_detector, error_fixer):
    """Set service instances (called by main.py during startup)."""
    global _monitor_service, _updater_service, _error_detector_service, _error_fixer_service
    _monitor_service = monitor
    _updater_service = updater
    _error_detector_service = error_detector
    _error_fixer_service = error_fixer


def get_monitor_service() -> "MonitorService":
    """Get the monitor service instance."""
    return _monitor_service


def get_updater_service() -> "UpdaterService":
    """Get the updater service instance."""
    return _updater_service


def get_error_detector_service() -> "ErrorDetectorService":
    """Get the error detector service instance."""
    return _error_detector_service


def get_error_fixer_service() -> "ErrorFixerService":
    """Get the error fixer service instance."""
    return _error_fixer_service
