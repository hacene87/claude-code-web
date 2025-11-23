"""
Audit Log Model
===============

Records all privileged actions for security and compliance.
"""

from typing import Optional, Any

from sqlalchemy import String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditLog(Base):
    """Audit trail of system actions."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Action details
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    component: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Entity reference
    entity_type: Mapped[Optional[str]] = mapped_column(String(100))
    entity_id: Mapped[Optional[str]] = mapped_column(String(100))

    # Actor information
    user_id: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50))

    # Additional context
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)

    def __repr__(self) -> str:
        return f"<AuditLog(action='{self.action}', component='{self.component}', user='{self.user_id}')>"
