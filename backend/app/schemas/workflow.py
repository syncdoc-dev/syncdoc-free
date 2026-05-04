"""Workflow schema models"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class WorkflowStateResponse(BaseModel):
    """Workflow state response"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    page_id: str
    state: str
    submitted_by_id: Optional[int] = None
    reviewed_by_id: Optional[int] = None
    approved_by_id: Optional[int] = None
    published_by_id: Optional[int] = None
    review_comment: Optional[str] = None
    rejection_reason: Optional[str] = None
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class WorkflowActionRequest(BaseModel):
    """Request to perform a workflow action"""

    comment: Optional[str] = None
    rejection_reason: Optional[str] = None


class WorkflowActionResponse(BaseModel):
    """Response after performing a workflow action"""

    success: bool
    workflow: WorkflowStateResponse
    message: str


class PageVersionResponse(BaseModel):
    """Page version response"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    page_id: str
    version: int
    title: str
    content_md: str
    changed_by_id: Optional[int] = None
    change_summary: Optional[str] = None
    workflow_state: Optional[str] = None
    created_at: datetime


class WorkflowAuditLogResponse(BaseModel):
    """Workflow audit log response"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    page_id: str
    workflow_id: str
    action: str
    from_state: Optional[str] = None
    to_state: Optional[str] = None
    actor_id: Optional[int] = None
    comment: Optional[str] = None
    created_at: datetime


class PageWithWorkflowResponse(BaseModel):
    """Page with workflow information"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    source_id: Optional[str] = None
    title: str
    content_md: str
    version: int
    is_manually_edited: int
    created_at: datetime
    updated_at: datetime
    workflow: Optional[WorkflowStateResponse] = None
