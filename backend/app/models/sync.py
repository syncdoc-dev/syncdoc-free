"""Sync run audit log model"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class SyncRun(Base):
    """Audit log of ingestion runs"""

    __tablename__ = "sync_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    source_id: Mapped[str] = mapped_column(String, ForeignKey("sources.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String, nullable=False
    )  # "pending", "in_progress", "completed", "failed"
    nodes_added: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    nodes_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    drift_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
