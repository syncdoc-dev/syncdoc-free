"""API Key model for programmatic access"""

import secrets
from datetime import datetime, timezone
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class ApiKey(Base):
    """API key for programmatic access."""

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(sa.String, nullable=False)
    key_prefix: Mapped[str] = mapped_column(sa.String(16), nullable=False, unique=True, index=True)
    key_hash: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )

    @staticmethod
    def hash_key(key: str) -> str:
        """Hash an API key using SHA256."""
        import hashlib

        return hashlib.sha256(key.encode()).hexdigest()

    @staticmethod
    def generate_key() -> tuple[str, str]:
        """Generate a new API key. Returns (full_key, prefix)."""
        full_key = f"syncdoc_{secrets.token_urlsafe(32)}"
        prefix = full_key[:16]
        return full_key, prefix

    def is_valid(self) -> bool:
        """Check if the key is still valid."""
        if self.revoked_at:
            return False
        if self.expires_at and self.expires_at.replace(tzinfo=timezone.utc) < datetime.now(
            timezone.utc
        ):
            return False
        return True
