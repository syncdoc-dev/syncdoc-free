"""Workflow models for page review/approval pipeline"""

from datetime import datetime, timezone
from enum import Enum

import sqlalchemy as sa
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class WorkflowState(str, Enum):
    """Page workflow states"""

    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    PUBLISHED = "published"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class WorkflowAction(str, Enum):
    """Actions that can be taken in the workflow"""

    SUBMIT_FOR_REVIEW = "submit_for_review"
    START_REVIEW = "start_review"
    APPROVE = "approve"
    PUBLISH = "publish"
    REJECT = "reject"
    ARCHIVE = "archive"
    REOPEN = "reopen"


class PageWorkflow(Base):
    """Tracks workflow state for a page"""

    __tablename__ = "page_workflows"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    page_id: Mapped[str] = mapped_column(
        String, ForeignKey("doc_pages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    state: Mapped[str] = mapped_column(String, default=WorkflowState.DRAFT.value, nullable=False)
    submitted_by_id: Mapped[int | None] = mapped_column(
        sa.Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_by_id: Mapped[int | None] = mapped_column(
        sa.Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_by_id: Mapped[int | None] = mapped_column(
        sa.Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    published_by_id: Mapped[int | None] = mapped_column(
        sa.Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )


class PageVersion(Base):
    """Version history for pages"""

    __tablename__ = "page_versions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    page_id: Mapped[str] = mapped_column(
        String, ForeignKey("doc_pages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    changed_by_id: Mapped[int | None] = mapped_column(
        sa.Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    change_summary: Mapped[str | None] = mapped_column(String, nullable=True)
    workflow_state: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )


class WorkflowAuditLog(Base):
    """Audit log for workflow actions"""

    __tablename__ = "workflow_audit_log"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    page_id: Mapped[str] = mapped_column(
        String, ForeignKey("doc_pages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workflow_id: Mapped[str] = mapped_column(
        String, ForeignKey("page_workflows.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String, nullable=False)
    from_state: Mapped[str | None] = mapped_column(String, nullable=True)
    to_state: Mapped[str | None] = mapped_column(String, nullable=True)
    actor_id: Mapped[int | None] = mapped_column(
        sa.Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
