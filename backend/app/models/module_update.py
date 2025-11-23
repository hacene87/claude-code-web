"""
Module Update Model
===================

Tracks Odoo module update history.
Implements data storage for FR-UPD-001.
"""

import enum
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.repository import Repository


class UpdateStatus(str, enum.Enum):
    """Status of a module update operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ModuleUpdate(Base):
    """Record of a module update operation."""

    __tablename__ = "module_updates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    module_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)

    # Commit tracking
    previous_commit: Mapped[Optional[str]] = mapped_column(String(40))
    current_commit: Mapped[str] = mapped_column(String(40), nullable=False)

    # Status
    status: Mapped[UpdateStatus] = mapped_column(
        Enum(UpdateStatus),
        default=UpdateStatus.PENDING,
        nullable=False,
        index=True
    )

    # Details
    files_changed: Mapped[Optional[List[str]]] = mapped_column(JSON)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    backup_path: Mapped[Optional[str]] = mapped_column(String(500))

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)

    # Relationships
    repository: Mapped["Repository"] = relationship(
        "Repository",
        back_populates="module_updates"
    )

    def __repr__(self) -> str:
        return f"<ModuleUpdate(module='{self.module_name}', status={self.status.value})>"
