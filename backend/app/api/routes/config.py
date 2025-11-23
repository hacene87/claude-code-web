"""
Configuration Routes
====================

System configuration management endpoints.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.routes.auth import get_current_user, require_admin, User
from app.core.config import get_settings, reload_settings

router = APIRouter()


class RepositoryConfigResponse(BaseModel):
    """Repository configuration."""
    path: str
    remote: str
    branch: str
    enabled: bool


class ConfigResponse(BaseModel):
    """System configuration response."""
    polling_interval: int
    max_retry_attempts: int
    automation_enabled: bool
    claude_enabled: bool
    backup_enabled: bool
    backup_retention_days: int
    repositories: List[RepositoryConfigResponse]


class ConfigUpdate(BaseModel):
    """Configuration update request."""
    polling_interval: Optional[int] = Field(None, ge=1, le=300)
    max_retry_attempts: Optional[int] = Field(None, ge=1, le=10)
    automation_enabled: Optional[bool] = None


class ConfigUpdateResponse(BaseModel):
    """Configuration update response."""
    status: str
    restart_required: bool


@router.get("", response_model=ConfigResponse)
async def get_config(current_user: User = Depends(get_current_user)):
    """Get current system configuration."""
    settings = get_settings()

    repositories = [
        RepositoryConfigResponse(
            path=repo.path,
            remote=repo.remote,
            branch=repo.branch,
            enabled=repo.enabled
        )
        for repo in settings.github.repositories
    ]

    return ConfigResponse(
        polling_interval=settings.github.polling_interval,
        max_retry_attempts=settings.retry.max_attempts,
        automation_enabled=settings.claude.enabled,
        claude_enabled=settings.claude.enabled,
        backup_enabled=settings.backup.enabled,
        backup_retention_days=settings.backup.retention_days,
        repositories=repositories
    )


@router.put("", response_model=ConfigUpdateResponse)
async def update_config(
    config: ConfigUpdate,
    current_user: User = Depends(require_admin)
):
    """
    Update system configuration.

    Requires admin role.
    Note: This updates runtime configuration only.
    For persistent changes, update the config file.
    """
    settings = get_settings()
    restart_required = False

    # Update polling interval
    if config.polling_interval is not None:
        settings.github.polling_interval = config.polling_interval

    # Update max retry attempts
    if config.max_retry_attempts is not None:
        settings.retry.max_attempts = config.max_retry_attempts

    # Update automation enabled
    if config.automation_enabled is not None:
        settings.claude.enabled = config.automation_enabled

    return ConfigUpdateResponse(
        status="updated",
        restart_required=restart_required
    )


@router.post("/reload", response_model=ConfigUpdateResponse)
async def reload_config(current_user: User = Depends(require_admin)):
    """
    Reload configuration from file.

    Requires admin role.
    """
    try:
        reload_settings()
        return ConfigUpdateResponse(
            status="reloaded",
            restart_required=False
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reload config: {str(e)}")
