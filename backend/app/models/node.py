"""Infrastructure node and edge models"""

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class InfraNode(Base):
    """A single infrastructure resource"""

    __tablename__ = "infra_nodes"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    kind: Mapped[str] = mapped_column(String, nullable=False)  # "service", "resource", "role", etc.
    name: Mapped[str] = mapped_column(String, nullable=False)
    config_json: Mapped[dict] = mapped_column(JSON, nullable=False)  # Full config data
    source_id: Mapped[str] = mapped_column(String, ForeignKey("sources.id"), nullable=False)
    hash: Mapped[str] = mapped_column(String, nullable=False)  # For drift detection
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )


class InfraEdge(Base):
    """Relationship between infrastructure nodes"""

    __tablename__ = "infra_edges"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    from_node_id: Mapped[str] = mapped_column(String, ForeignKey("infra_nodes.id"), nullable=False)
    to_node_id: Mapped[str] = mapped_column(String, ForeignKey("infra_nodes.id"), nullable=False)
    relation_type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # "depends_on", "connects_to", etc.
    edge_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
