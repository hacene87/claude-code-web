"""
User Session Model
==================

Manages API authentication sessions.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserSession(Base):
    """User authentication session for API access."""

    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Token hashes (never store raw tokens)
    token_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    refresh_token_hash: Mapped[Optional[str]] = mapped_column(String(256))

    # Session info
    device_info: Mapped[Optional[str]] = mapped_column(String(500))
    ip_address: Mapped[Optional[str]] = mapped_column(String(50))

    # Expiration
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    last_activity_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    def __repr__(self) -> str:
        return f"<UserSession(user_id='{self.user_id}', expires_at={self.expires_at})>"
