"""
System Configuration Model
==========================

Stores runtime configuration in the database.
"""

from typing import Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SystemConfig(Base):
    """Key-value store for system configuration."""

    __tablename__ = "system_config"

    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    updated_by: Mapped[Optional[str]] = mapped_column(String(100))

    def __repr__(self) -> str:
        return f"<SystemConfig(key='{self.key}')>"
