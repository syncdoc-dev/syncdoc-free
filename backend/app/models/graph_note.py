"""Graph note model"""

from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class GraphNote(Base):
    __tablename__ = "graph_notes"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        sa.ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
    )
    project_id: Mapped[str] = mapped_column(
        String,
        sa.ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
    )
    source_id: Mapped[str | None] = mapped_column(
        String,
        sa.ForeignKey("sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    from_node_id: Mapped[str | None] = mapped_column(
        String,
        sa.ForeignKey("infra_nodes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    to_node_id: Mapped[str | None] = mapped_column(
        String,
        sa.ForeignKey("infra_nodes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    color: Mapped[str] = mapped_column(String, default="#f59e0b")
    pos_x: Mapped[float] = mapped_column(Float, nullable=False)
    pos_y: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )
