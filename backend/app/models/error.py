"""
Error Models
============

Tracks detected errors and fix attempts.
Implements data storage for FR-ERR-001, FR-ERR-002, FR-FIX-001, FR-FIX-002.
"""

import enum
import uuid
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey, Enum, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ErrorSeverity(str, enum.Enum):
    """Error severity levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ErrorCategory(str, enum.Enum):
    """Error category classification."""
    PYTHON = "PYTHON"
    DATABASE = "DATABASE"
    ODOO = "ODOO"
    ASSET = "ASSET"
    DEPENDENCY = "DEPENDENCY"


class ErrorStatus(str, enum.Enum):
    """Error lifecycle status."""
    DETECTED = "detected"
    QUEUED = "queued"
    FIXING = "fixing"
    RESOLVED = "resolved"
    FAILED = "failed"
    IGNORED = "ignored"


class FixAttemptStatus(str, enum.Enum):
    """Status of a fix attempt."""
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


class Error(Base):
    """Detected error from Odoo logs."""

    __tablename__ = "errors"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # Error classification
    error_type: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    severity: Mapped[ErrorSeverity] = mapped_column(
        Enum(ErrorSeverity),
        nullable=False,
        index=True
    )
    category: Mapped[ErrorCategory] = mapped_column(
        Enum(ErrorCategory),
        nullable=False,
        index=True
    )

    # Error details
    message: Mapped[str] = mapped_column(Text, nullable=False)
    stack_trace: Mapped[Optional[str]] = mapped_column(Text)

    # Source location
    module_name: Mapped[Optional[str]] = mapped_column(String(200), index=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(500))
    line_number: Mapped[Optional[int]] = mapped_column(Integer)

    # Context
    context_before: Mapped[Optional[List[str]]] = mapped_column(JSON)
    context_after: Mapped[Optional[List[str]]] = mapped_column(JSON)
    raw_log: Mapped[Optional[str]] = mapped_column(Text)

    # Status and tracking
    status: Mapped[ErrorStatus] = mapped_column(
        Enum(ErrorStatus),
        default=ErrorStatus.DETECTED,
        nullable=False,
        index=True
    )
    auto_fixable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    detected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    ignored_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    ignored_by: Mapped[Optional[str]] = mapped_column(String(200))

    # Relationships
    fix_attempts: Mapped[List["FixAttempt"]] = relationship(
        "FixAttempt",
        back_populates="error",
        cascade="all, delete-orphan",
        order_by="FixAttempt.attempt_number"
    )

    @property
    def attempt_count(self) -> int:
        """Number of fix attempts made."""
        return len(self.fix_attempts)

    def __repr__(self) -> str:
        return f"<Error(type='{self.error_type}', status={self.status.value}, attempts={self.attempt_count})>"


class FixAttempt(Base):
    """Record of an attempt to fix an error using Claude Code CLI."""

    __tablename__ = "fix_attempts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    error_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("errors.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Status
    status: Mapped[FixAttemptStatus] = mapped_column(
        Enum(FixAttemptStatus),
        default=FixAttemptStatus.IN_PROGRESS,
        nullable=False
    )

    # Claude interaction
    claude_prompt: Mapped[Optional[str]] = mapped_column(Text)
    claude_response: Mapped[Optional[str]] = mapped_column(Text)

    # Results
    files_modified: Mapped[Optional[List[str]]] = mapped_column(JSON)
    fix_diff: Mapped[Optional[str]] = mapped_column(Text)
    error_after_fix: Mapped[Optional[str]] = mapped_column(Text)

    # Performance
    execution_time_seconds: Mapped[Optional[float]] = mapped_column(Float)

    # Timestamps
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    error: Mapped["Error"] = relationship("Error", back_populates="fix_attempts")

    def __repr__(self) -> str:
        return f"<FixAttempt(error_id='{self.error_id}', attempt={self.attempt_number}, status={self.status.value})>"
