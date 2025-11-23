"""
Errors Routes
=============

Error management and fix tracking endpoints.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, desc

from app.api.routes.auth import get_current_user, require_developer, User
from app.api.dependencies import get_error_fixer_service
from app.core.database import get_session
from app.models.error import Error, ErrorStatus, ErrorSeverity, ErrorCategory, FixAttempt

router = APIRouter()


class ErrorSummary(BaseModel):
    """Summary of an error."""
    id: str
    error_type: str
    severity: str
    category: str
    module_name: Optional[str]
    message: str
    status: str
    attempts: int
    detected_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ErrorList(BaseModel):
    """Paginated list of errors."""
    total: int
    items: List[ErrorSummary]


class FixAttemptSummary(BaseModel):
    """Summary of a fix attempt."""
    id: int
    attempt_number: int
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    execution_time_seconds: Optional[float]
    files_modified: Optional[List[str]]

    class Config:
        from_attributes = True


class ErrorDetail(BaseModel):
    """Detailed error information."""
    id: str
    error_type: str
    severity: str
    category: str
    message: str
    stack_trace: Optional[str]
    module_name: Optional[str]
    file_path: Optional[str]
    line_number: Optional[int]
    context_before: Optional[List[str]]
    context_after: Optional[List[str]]
    raw_log: Optional[str]
    status: str
    auto_fixable: bool
    detected_at: datetime
    resolved_at: Optional[datetime]
    ignored_at: Optional[datetime]
    ignored_by: Optional[str]
    fix_attempts: List[FixAttemptSummary]

    class Config:
        from_attributes = True


class RetryResponse(BaseModel):
    """Response from retry operation."""
    status: str
    attempt_number: int


class IgnoreResponse(BaseModel):
    """Response from ignore operation."""
    status: str


@router.get("", response_model=ErrorList)
async def list_errors(
    current_user: User = Depends(get_current_user),
    status: Optional[str] = Query(None, description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    category: Optional[str] = Query(None, description="Filter by category"),
    module: Optional[str] = Query(None, description="Filter by module name"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """
    List errors with pagination and filtering.
    """
    async with get_session() as session:
        # Build query
        query = select(Error).order_by(desc(Error.detected_at))

        if status:
            try:
                status_enum = ErrorStatus(status)
                query = query.where(Error.status == status_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

        if severity:
            try:
                severity_enum = ErrorSeverity(severity)
                query = query.where(Error.severity == severity_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")

        if category:
            try:
                category_enum = ErrorCategory(category)
                query = query.where(Error.category == category_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid category: {category}")

        if module:
            query = query.where(Error.module_name.ilike(f"%{module}%"))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        result = await session.execute(count_query)
        total = result.scalar() or 0

        # Apply pagination
        query = query.offset(offset).limit(limit)
        result = await session.execute(query)
        errors = result.scalars().all()

        items = []
        for e in errors:
            # Get attempt count
            attempt_result = await session.execute(
                select(func.count(FixAttempt.id)).where(FixAttempt.error_id == e.id)
            )
            attempt_count = attempt_result.scalar() or 0

            items.append(ErrorSummary(
                id=e.id,
                error_type=e.error_type,
                severity=e.severity.value,
                category=e.category.value,
                module_name=e.module_name,
                message=e.message[:200],
                status=e.status.value,
                attempts=attempt_count,
                detected_at=e.detected_at,
                resolved_at=e.resolved_at
            ))

        return ErrorList(total=total, items=items)


@router.get("/active", response_model=List[ErrorSummary])
async def list_active_errors(
    current_user: User = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=50)
):
    """Get list of active (unresolved) errors."""
    async with get_session() as session:
        query = select(Error).where(
            Error.status.in_([
                ErrorStatus.DETECTED,
                ErrorStatus.QUEUED,
                ErrorStatus.FIXING
            ])
        ).order_by(desc(Error.detected_at)).limit(limit)

        result = await session.execute(query)
        errors = result.scalars().all()

        items = []
        for e in errors:
            attempt_result = await session.execute(
                select(func.count(FixAttempt.id)).where(FixAttempt.error_id == e.id)
            )
            attempt_count = attempt_result.scalar() or 0

            items.append(ErrorSummary(
                id=e.id,
                error_type=e.error_type,
                severity=e.severity.value,
                category=e.category.value,
                module_name=e.module_name,
                message=e.message[:200],
                status=e.status.value,
                attempts=attempt_count,
                detected_at=e.detected_at,
                resolved_at=e.resolved_at
            ))

        return items


@router.get("/{error_id}", response_model=ErrorDetail)
async def get_error(
    error_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get details of a specific error."""
    async with get_session() as session:
        result = await session.execute(
            select(Error).where(Error.id == error_id)
        )
        error = result.scalar_one_or_none()

        if not error:
            raise HTTPException(status_code=404, detail="Error not found")

        # Get fix attempts
        attempts_result = await session.execute(
            select(FixAttempt)
            .where(FixAttempt.error_id == error_id)
            .order_by(FixAttempt.attempt_number)
        )
        attempts = attempts_result.scalars().all()

        fix_attempts = [
            FixAttemptSummary(
                id=a.id,
                attempt_number=a.attempt_number,
                status=a.status.value,
                started_at=a.started_at,
                completed_at=a.completed_at,
                execution_time_seconds=a.execution_time_seconds,
                files_modified=a.files_modified
            )
            for a in attempts
        ]

        return ErrorDetail(
            id=error.id,
            error_type=error.error_type,
            severity=error.severity.value,
            category=error.category.value,
            message=error.message,
            stack_trace=error.stack_trace,
            module_name=error.module_name,
            file_path=error.file_path,
            line_number=error.line_number,
            context_before=error.context_before,
            context_after=error.context_after,
            raw_log=error.raw_log,
            status=error.status.value,
            auto_fixable=error.auto_fixable,
            detected_at=error.detected_at,
            resolved_at=error.resolved_at,
            ignored_at=error.ignored_at,
            ignored_by=error.ignored_by,
            fix_attempts=fix_attempts
        )


@router.post("/{error_id}/retry", response_model=RetryResponse)
async def retry_error(
    error_id: str,
    current_user: User = Depends(require_developer)
):
    """
    Retry fixing an error.

    Requires developer or admin role.
    """
    fixer = get_error_fixer_service()
    success = await fixer.retry_error(error_id)

    if not success:
        raise HTTPException(
            status_code=400,
            detail="Cannot retry this error (not found or not in valid state)"
        )

    # Get new attempt number
    async with get_session() as session:
        result = await session.execute(
            select(func.count(FixAttempt.id)).where(FixAttempt.error_id == error_id)
        )
        attempt_count = result.scalar() or 0

    return RetryResponse(status="queued", attempt_number=attempt_count + 1)


@router.post("/{error_id}/ignore", response_model=IgnoreResponse)
async def ignore_error(
    error_id: str,
    current_user: User = Depends(require_developer)
):
    """
    Mark an error as ignored.

    Requires developer or admin role.
    """
    fixer = get_error_fixer_service()
    success = await fixer.ignore_error(error_id, current_user.username)

    if not success:
        raise HTTPException(status_code=404, detail="Error not found")

    return IgnoreResponse(status="ignored")
