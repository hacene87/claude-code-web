"""
Updates Routes
==============

Module update management endpoints.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, desc

from app.api.routes.auth import get_current_user, require_developer, User
from app.api.dependencies import get_updater_service
from app.core.database import get_session
from app.core.config import get_settings
from app.models.module_update import ModuleUpdate, UpdateStatus

router = APIRouter()


class UpdateSummary(BaseModel):
    """Summary of a module update."""
    id: int
    module_name: str
    status: str
    commit_hash: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class UpdateList(BaseModel):
    """Paginated list of updates."""
    total: int
    items: List[UpdateSummary]


class TriggerUpdateRequest(BaseModel):
    """Request to trigger module updates."""
    modules: List[str]
    force: bool = False


class TriggerUpdateResponse(BaseModel):
    """Response from triggering updates."""
    job_id: str
    status: str


class UpdateDetail(BaseModel):
    """Detailed update information."""
    id: int
    repository_id: int
    module_name: str
    previous_commit: Optional[str]
    current_commit: str
    status: str
    files_changed: Optional[List[str]]
    error_message: Optional[str]
    backup_path: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=UpdateList)
async def list_updates(
    current_user: User = Depends(get_current_user),
    status: Optional[str] = Query(None, description="Filter by status"),
    module: Optional[str] = Query(None, description="Filter by module name"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """
    List module updates with pagination and filtering.
    """
    async with get_session() as session:
        # Build query
        query = select(ModuleUpdate).order_by(desc(ModuleUpdate.created_at))

        if status:
            try:
                status_enum = UpdateStatus(status)
                query = query.where(ModuleUpdate.status == status_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

        if module:
            query = query.where(ModuleUpdate.module_name.ilike(f"%{module}%"))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        result = await session.execute(count_query)
        total = result.scalar() or 0

        # Apply pagination
        query = query.offset(offset).limit(limit)
        result = await session.execute(query)
        updates = result.scalars().all()

        items = [
            UpdateSummary(
                id=u.id,
                module_name=u.module_name,
                status=u.status.value,
                commit_hash=u.current_commit[:7],
                created_at=u.created_at,
                completed_at=u.completed_at,
                duration_seconds=u.duration_seconds,
                error_message=u.error_message
            )
            for u in updates
        ]

        return UpdateList(total=total, items=items)


@router.get("/{update_id}", response_model=UpdateDetail)
async def get_update(
    update_id: int,
    current_user: User = Depends(get_current_user)
):
    """Get details of a specific update."""
    async with get_session() as session:
        result = await session.execute(
            select(ModuleUpdate).where(ModuleUpdate.id == update_id)
        )
        update = result.scalar_one_or_none()

        if not update:
            raise HTTPException(status_code=404, detail="Update not found")

        return UpdateDetail(
            id=update.id,
            repository_id=update.repository_id,
            module_name=update.module_name,
            previous_commit=update.previous_commit,
            current_commit=update.current_commit,
            status=update.status.value,
            files_changed=update.files_changed,
            error_message=update.error_message,
            backup_path=update.backup_path,
            started_at=update.started_at,
            completed_at=update.completed_at,
            duration_seconds=update.duration_seconds,
            created_at=update.created_at
        )


@router.post("/trigger", response_model=TriggerUpdateResponse)
async def trigger_update(
    request: TriggerUpdateRequest,
    current_user: User = Depends(require_developer)
):
    """
    Trigger module updates manually.

    Requires developer or admin role.
    """
    import uuid
    from app.services.updater import UpdateRequest

    updater = get_updater_service()
    settings = get_settings()

    if not request.modules:
        raise HTTPException(status_code=400, detail="No modules specified")

    if updater.is_updating:
        raise HTTPException(status_code=409, detail="Another update is in progress")

    # Create update request
    job_id = str(uuid.uuid4())
    update_request = UpdateRequest(
        modules=request.modules,
        database=settings.odoo.database,
        force_restart=request.force,
        backup_before=True,
        correlation_id=job_id
    )

    # Start update in background
    import asyncio
    asyncio.create_task(updater.update_modules(update_request))

    return TriggerUpdateResponse(job_id=job_id, status="queued")


@router.post("/{update_id}/retry", response_model=TriggerUpdateResponse)
async def retry_update(
    update_id: int,
    current_user: User = Depends(require_developer)
):
    """
    Retry a failed update.

    Requires developer or admin role.
    """
    import uuid

    async with get_session() as session:
        result = await session.execute(
            select(ModuleUpdate).where(ModuleUpdate.id == update_id)
        )
        update = result.scalar_one_or_none()

        if not update:
            raise HTTPException(status_code=404, detail="Update not found")

        if update.status not in (UpdateStatus.FAILED, UpdateStatus.ROLLED_BACK):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot retry update with status: {update.status.value}"
            )

        # Reset status
        update.status = UpdateStatus.PENDING
        update.error_message = None
        await session.commit()

    updater = get_updater_service()
    job_id = str(uuid.uuid4())

    # Trigger the update
    import asyncio
    asyncio.create_task(updater.trigger_update(update_id))

    return TriggerUpdateResponse(job_id=job_id, status="queued")
