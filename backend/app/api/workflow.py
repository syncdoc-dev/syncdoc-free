"""Workflow API endpoints for page review/approval pipeline"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentContext
from app.core.rbac import require_role
from app.models.page import DocPage
from app.models.workflow import (
    PageVersion,
    PageWorkflow,
    WorkflowAction,
    WorkflowAuditLog,
    WorkflowState,
)
from app.schemas.workflow import (
    PageVersionResponse,
    PageWithWorkflowResponse,
    WorkflowActionRequest,
    WorkflowActionResponse,
    WorkflowAuditLogResponse,
    WorkflowStateResponse,
)

router = APIRouter(prefix="/workflow", tags=["workflow"])


def _utcnow():
    return datetime.now(timezone.utc)


VALID_TRANSITIONS = {
    WorkflowState.DRAFT: [WorkflowState.PENDING_REVIEW],
    WorkflowState.PENDING_REVIEW: [WorkflowState.UNDER_REVIEW, WorkflowState.DRAFT],
    WorkflowState.UNDER_REVIEW: [
        WorkflowState.APPROVED,
        WorkflowState.REJECTED,
        WorkflowState.DRAFT,
    ],
    WorkflowState.APPROVED: [WorkflowState.PUBLISHED, WorkflowState.DRAFT],
    WorkflowState.PUBLISHED: [WorkflowState.ARCHIVED, WorkflowState.DRAFT],
    WorkflowState.REJECTED: [WorkflowState.DRAFT],
    WorkflowState.ARCHIVED: [WorkflowState.DRAFT],
}


async def get_page_with_workflow(
    page_id: str,
    db: AsyncSession,
    ctx: CurrentContext,
) -> tuple[DocPage, Optional[PageWorkflow]]:
    """Get page with its workflow"""
    page = await db.get(DocPage, page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    if page.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Page not found")

    result = await db.execute(select(PageWorkflow).where(PageWorkflow.page_id == page_id))
    workflow = result.scalar_one_or_none()

    return page, workflow


async def create_version(
    page: DocPage,
    db: AsyncSession,
    actor_id: Optional[int] = None,
    change_summary: Optional[str] = None,
) -> PageVersion:
    """Create a new version of the page"""
    version = PageVersion(
        id=uuid.uuid4().hex[:16],
        page_id=page.id,
        version=page.version,
        title=page.title,
        content_md=page.content_md,
        changed_by_id=actor_id,
        change_summary=change_summary,
    )
    db.add(version)
    return version


async def log_audit(
    page_id: str,
    workflow_id: str,
    action: str,
    from_state: Optional[str],
    to_state: Optional[str],
    db: AsyncSession,
    actor_id: Optional[int] = None,
    comment: Optional[str] = None,
) -> WorkflowAuditLog:
    """Log an audit entry"""
    audit = WorkflowAuditLog(
        id=uuid.uuid4().hex[:16],
        page_id=page_id,
        workflow_id=workflow_id,
        action=action,
        from_state=from_state,
        to_state=to_state,
        actor_id=actor_id,
        comment=comment,
    )
    db.add(audit)
    return audit


@router.get("/pages/{page_id}", response_model=PageWithWorkflowResponse)
async def get_page_workflow(
    page_id: str,
    ctx: CurrentContext = Depends(require_role("viewer")),
    db: AsyncSession = Depends(get_db),
):
    """Get page with workflow state"""
    page, workflow = await get_page_with_workflow(page_id, db, ctx)

    return PageWithWorkflowResponse(
        id=page.id,
        source_id=page.source_id,
        title=page.title,
        content_md=page.content_md,
        version=page.version,
        is_manually_edited=page.is_manually_edited,
        created_at=page.created_at,
        updated_at=page.updated_at,
        workflow=WorkflowStateResponse.model_validate(workflow) if workflow else None,
    )


@router.post("/pages/{page_id}/submit", response_model=WorkflowActionResponse)
async def submit_for_review(
    page_id: str,
    request: WorkflowActionRequest,
    ctx: CurrentContext = Depends(require_role("member")),
    db: AsyncSession = Depends(get_db),
):
    """Submit a page for review"""
    page, workflow = await get_page_with_workflow(page_id, db, ctx)

    if workflow is None:
        workflow = PageWorkflow(
            id=uuid.uuid4().hex[:16],
            page_id=page_id,
            state=WorkflowState.DRAFT.value,
        )
        db.add(workflow)

    current_state = WorkflowState(workflow.state)

    if current_state not in VALID_TRANSITIONS:
        raise HTTPException(
            status_code=400, detail=f"Cannot submit from state: {current_state.value}"
        )

    if WorkflowState.PENDING_REVIEW not in VALID_TRANSITIONS[current_state]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot submit for review from state: {current_state.value}",
        )

    from_state = workflow.state
    workflow.state = WorkflowState.PENDING_REVIEW.value
    workflow.submitted_by_id = ctx.user.id
    workflow.submitted_at = _utcnow()

    await create_version(page, db, ctx.user.id, "Submitted for review")
    await log_audit(
        page_id,
        workflow.id,
        WorkflowAction.SUBMIT_FOR_REVIEW.value,
        from_state,
        WorkflowState.PENDING_REVIEW.value,
        db,
        ctx.user.id,
        request.comment,
    )

    await db.commit()
    await db.refresh(workflow)

    return WorkflowActionResponse(
        success=True,
        workflow=WorkflowStateResponse.model_validate(workflow),
        message="Page submitted for review",
    )


@router.post("/pages/{page_id}/start-review", response_model=WorkflowActionResponse)
async def start_review(
    page_id: str,
    request: WorkflowActionRequest,
    ctx: CurrentContext = Depends(require_role("member")),
    db: AsyncSession = Depends(get_db),
):
    """Start reviewing a page"""
    page, workflow = await get_page_with_workflow(page_id, db, ctx)

    if not workflow:
        raise HTTPException(status_code=404, detail="No workflow found for page")

    current_state = WorkflowState(workflow.state)

    if current_state != WorkflowState.PENDING_REVIEW:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Can only start review from pending_review state, current: {current_state.value}"
            ),
        )

    from_state = workflow.state
    workflow.state = WorkflowState.UNDER_REVIEW.value
    workflow.reviewed_by_id = ctx.user.id
    workflow.reviewed_at = _utcnow()

    await log_audit(
        page_id,
        workflow.id,
        WorkflowAction.START_REVIEW.value,
        from_state,
        WorkflowState.UNDER_REVIEW.value,
        db,
        ctx.user.id,
        request.comment,
    )

    await db.commit()
    await db.refresh(workflow)

    return WorkflowActionResponse(
        success=True,
        workflow=WorkflowStateResponse.model_validate(workflow),
        message="Review started",
    )


@router.post("/pages/{page_id}/approve", response_model=WorkflowActionResponse)
async def approve_page(
    page_id: str,
    request: WorkflowActionRequest,
    ctx: CurrentContext = Depends(require_role("member")),
    db: AsyncSession = Depends(get_db),
):
    """Approve a page"""
    page, workflow = await get_page_with_workflow(page_id, db, ctx)

    if not workflow:
        raise HTTPException(status_code=404, detail="No workflow found for page")

    current_state = WorkflowState(workflow.state)

    if current_state != WorkflowState.UNDER_REVIEW:
        raise HTTPException(
            status_code=400,
            detail=f"Can only approve from under_review state, current: {current_state.value}",
        )

    from_state = workflow.state
    workflow.state = WorkflowState.APPROVED.value
    workflow.approved_by_id = ctx.user.id
    workflow.approved_at = _utcnow()
    workflow.review_comment = request.comment

    await create_version(page, db, ctx.user.id, "Approved")
    await log_audit(
        page_id,
        workflow.id,
        WorkflowAction.APPROVE.value,
        from_state,
        WorkflowState.APPROVED.value,
        db,
        ctx.user.id,
        request.comment,
    )

    await db.commit()
    await db.refresh(workflow)

    return WorkflowActionResponse(
        success=True,
        workflow=WorkflowStateResponse.model_validate(workflow),
        message="Page approved",
    )


@router.post("/pages/{page_id}/reject", response_model=WorkflowActionResponse)
async def reject_page(
    page_id: str,
    request: WorkflowActionRequest,
    ctx: CurrentContext = Depends(require_role("member")),
    db: AsyncSession = Depends(get_db),
):
    """Reject a page"""
    if not request.rejection_reason:
        raise HTTPException(status_code=400, detail="Rejection reason is required")

    page, workflow = await get_page_with_workflow(page_id, db, ctx)

    if not workflow:
        raise HTTPException(status_code=404, detail="No workflow found for page")

    current_state = WorkflowState(workflow.state)

    if current_state != WorkflowState.UNDER_REVIEW:
        raise HTTPException(
            status_code=400,
            detail=f"Can only reject from under_review state, current: {current_state.value}",
        )

    from_state = workflow.state
    workflow.state = WorkflowState.REJECTED.value
    workflow.reviewed_by_id = ctx.user.id
    workflow.reviewed_at = _utcnow()
    workflow.rejection_reason = request.rejection_reason

    await create_version(page, db, ctx.user.id, f"Rejected: {request.rejection_reason}")
    await log_audit(
        page_id,
        workflow.id,
        WorkflowAction.REJECT.value,
        from_state,
        WorkflowState.REJECTED.value,
        db,
        ctx.user.id,
        request.rejection_reason,
    )

    await db.commit()
    await db.refresh(workflow)

    return WorkflowActionResponse(
        success=True,
        workflow=WorkflowStateResponse.model_validate(workflow),
        message="Page rejected",
    )


@router.post("/pages/{page_id}/publish", response_model=WorkflowActionResponse)
async def publish_page(
    page_id: str,
    request: WorkflowActionRequest,
    ctx: CurrentContext = Depends(require_role("member")),
    db: AsyncSession = Depends(get_db),
):
    """Publish an approved page"""
    page, workflow = await get_page_with_workflow(page_id, db, ctx)

    if not workflow:
        raise HTTPException(status_code=404, detail="No workflow found for page")

    current_state = WorkflowState(workflow.state)

    if current_state != WorkflowState.APPROVED:
        raise HTTPException(
            status_code=400,
            detail=f"Can only publish from approved state, current: {current_state.value}",
        )

    from_state = workflow.state
    workflow.state = WorkflowState.PUBLISHED.value
    workflow.published_by_id = ctx.user.id
    workflow.published_at = _utcnow()

    await create_version(page, db, ctx.user.id, "Published")
    await log_audit(
        page_id,
        workflow.id,
        WorkflowAction.PUBLISH.value,
        from_state,
        WorkflowState.PUBLISHED.value,
        db,
        ctx.user.id,
        request.comment,
    )

    await db.commit()
    await db.refresh(workflow)

    return WorkflowActionResponse(
        success=True,
        workflow=WorkflowStateResponse.model_validate(workflow),
        message="Page published",
    )


@router.post("/pages/{page_id}/archive", response_model=WorkflowActionResponse)
async def archive_page(
    page_id: str,
    request: WorkflowActionRequest,
    ctx: CurrentContext = Depends(require_role("member")),
    db: AsyncSession = Depends(get_db),
):
    """Archive a published page"""
    page, workflow = await get_page_with_workflow(page_id, db, ctx)

    if not workflow:
        raise HTTPException(status_code=404, detail="No workflow found for page")

    current_state = WorkflowState(workflow.state)

    if current_state != WorkflowState.PUBLISHED:
        raise HTTPException(
            status_code=400,
            detail=f"Can only archive from published state, current: {current_state.value}",
        )

    from_state = workflow.state
    workflow.state = WorkflowState.ARCHIVED.value

    await create_version(page, db, ctx.user.id, "Archived")
    await log_audit(
        page_id,
        workflow.id,
        WorkflowAction.ARCHIVE.value,
        from_state,
        WorkflowState.ARCHIVED.value,
        db,
        ctx.user.id,
        request.comment,
    )

    await db.commit()
    await db.refresh(workflow)

    return WorkflowActionResponse(
        success=True,
        workflow=WorkflowStateResponse.model_validate(workflow),
        message="Page archived",
    )


@router.post("/pages/{page_id}/reopen", response_model=WorkflowActionResponse)
async def reopen_workflow(
    page_id: str,
    request: WorkflowActionRequest,
    ctx: CurrentContext = Depends(require_role("member")),
    db: AsyncSession = Depends(get_db),
):
    """Reopen workflow from rejected/archived state back to draft"""
    page, workflow = await get_page_with_workflow(page_id, db, ctx)

    if not workflow:
        raise HTTPException(status_code=404, detail="No workflow found for page")

    current_state = WorkflowState(workflow.state)

    if current_state not in [WorkflowState.REJECTED, WorkflowState.ARCHIVED]:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Can only reopen from rejected or archived state, current: {current_state.value}"
            ),
        )

    from_state = workflow.state
    workflow.state = WorkflowState.DRAFT.value

    await create_version(page, db, ctx.user.id, "Reopened")
    await log_audit(
        page_id,
        workflow.id,
        WorkflowAction.REOPEN.value,
        from_state,
        WorkflowState.DRAFT.value,
        db,
        ctx.user.id,
        request.comment,
    )

    await db.commit()
    await db.refresh(workflow)

    return WorkflowActionResponse(
        success=True,
        workflow=WorkflowStateResponse.model_validate(workflow),
        message="Workflow reopened as draft",
    )


@router.get("/pages/{page_id}/versions", response_model=List[PageVersionResponse])
async def list_page_versions(
    page_id: str,
    ctx: CurrentContext = Depends(require_role("viewer")),
    db: AsyncSession = Depends(get_db),
):
    """List all versions of a page"""
    await get_page_with_workflow(page_id, db, ctx)
    result = await db.execute(
        select(PageVersion)
        .where(PageVersion.page_id == page_id)
        .order_by(PageVersion.version.desc(), PageVersion.created_at.desc())
    )
    versions = result.scalars().all()

    return [PageVersionResponse.model_validate(v) for v in versions]


@router.get("/pages/{page_id}/audit", response_model=List[WorkflowAuditLogResponse])
async def get_workflow_audit_log(
    page_id: str,
    ctx: CurrentContext = Depends(require_role("viewer")),
    db: AsyncSession = Depends(get_db),
):
    """Get audit log for a page's workflow"""
    await get_page_with_workflow(page_id, db, ctx)
    result = await db.execute(
        select(WorkflowAuditLog)
        .where(WorkflowAuditLog.page_id == page_id)
        .order_by(WorkflowAuditLog.created_at.desc())
    )
    logs = result.scalars().all()

    return [WorkflowAuditLogResponse.model_validate(log) for log in logs]
