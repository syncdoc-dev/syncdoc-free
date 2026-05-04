"""Source model"""

from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Source(Base):
    """IaC source (repo or file)"""

    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # "terraform", "docker", "ansible", etc.
    url: Mapped[str] = mapped_column(String, nullable=False)
    credentials_ref: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # Reference to env var or vault path
    last_synced: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )
    user_id: Mapped[int | None] = mapped_column(
        sa.Integer,
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    organization_id: Mapped[str | None] = mapped_column(
        String,
        sa.ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    project_id: Mapped[str | None] = mapped_column(
        String,
        sa.ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
