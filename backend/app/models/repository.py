"""
Repository Model
================

Represents a Git repository being monitored.
Implements data storage for FR-MON-001.
"""

from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import String, Boolean, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.module_update import ModuleUpdate


class Repository(Base):
    """Git repository configuration and state."""

    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    path: Mapped[str] = mapped_column(String(500), unique=True, nullable=False, index=True)
    remote: Mapped[str] = mapped_column(String(100), default="origin", nullable=False)
    branch: Mapped[str] = mapped_column(String(100), default="main", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # State tracking
    last_commit_hash: Mapped[Optional[str]] = mapped_column(String(40))
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_error: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    module_updates: Mapped[List["ModuleUpdate"]] = relationship(
        "ModuleUpdate",
        back_populates="repository",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Repository(path='{self.path}', branch='{self.branch}', enabled={self.enabled})>"
