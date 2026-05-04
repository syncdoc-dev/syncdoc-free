"""Curated, read-only data explorer for organization owners."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Sequence

from fastapi import HTTPException
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import CurrentContext
from app.models.drift import DriftEvent
from app.models.node import InfraNode
from app.models.organization_membership import OrganizationMembership
from app.models.page import DocPage
from app.models.project import Project
from app.models.setting import AppSetting
from app.models.source import Source
from app.models.sync import SyncRun
from app.models.user import User
from app.models.workflow import PageWorkflow, WorkflowAuditLog

RowSerializer = Callable[[Any], dict[str, Any]]
QueryBuilder = Callable[[CurrentContext, str | None], Select[Any]]

_SECRET_SETTING_KEYS = {
    "llm_api_key",
    "openai_api_key",
    "anthropic_api_key",
    "slack_webhook_url",
    "github_token",
}


def _mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 4:
        return "••••"
    return "••••" + value[-4:]


def _matches_query(row: dict[str, Any], q: str, searchable_fields: Sequence[str]) -> bool:
    needle = q.strip().lower()
    if not needle:
        return True
    for field in searchable_fields:
        value = row.get(field)
        if value is not None and needle in str(value).lower():
            return True
    return False


def _serialize_source(source: Source) -> dict[str, Any]:
    return {
        "id": source.id,
        "type": source.type,
        "url": source.url,
        "project_id": source.project_id,
        "last_synced": source.last_synced,
        "created_at": source.created_at,
    }


def _serialize_project(project: Project) -> dict[str, Any]:
    return {
        "id": project.id,
        "name": project.name,
        "created_at": project.created_at,
    }


def _serialize_membership(row: tuple[OrganizationMembership, User]) -> dict[str, Any]:
    membership, user = row
    return {
        "id": membership.id,
        "user_id": user.id,
        "login": user.login,
        "email": user.email,
        "role": membership.role,
        "created_at": membership.created_at,
    }


def _serialize_page(page: DocPage) -> dict[str, Any]:
    return {
        "id": page.id,
        "source_id": page.source_id,
        "title": page.title,
        "version": page.version,
        "is_manually_edited": page.is_manually_edited,
        "updated_at": page.updated_at,
    }


def _serialize_workflow(workflow: PageWorkflow) -> dict[str, Any]:
    return {
        "id": workflow.id,
        "page_id": workflow.page_id,
        "state": workflow.state,
        "submitted_by_id": workflow.submitted_by_id,
        "reviewed_by_id": workflow.reviewed_by_id,
        "approved_by_id": workflow.approved_by_id,
        "published_by_id": workflow.published_by_id,
        "updated_at": workflow.updated_at,
    }


def _serialize_workflow_audit(log: WorkflowAuditLog) -> dict[str, Any]:
    return {
        "id": log.id,
        "workflow_id": log.workflow_id,
        "page_id": log.page_id,
        "actor_id": log.actor_id,
        "action": log.action,
        "from_state": log.from_state,
        "to_state": log.to_state,
        "comment": log.comment,
        "created_at": log.created_at,
    }


def _serialize_drift(row: tuple[DriftEvent, InfraNode]) -> dict[str, Any]:
    event, node = row
    return {
        "id": event.id,
        "node_id": event.node_id,
        "node_name": node.name,
        "page_id": event.page_id,
        "detected_at": event.detected_at,
        "resolved": bool(event.resolved),
        "resolved_at": event.resolved_at,
        "resolution_notes": event.resolution_notes,
    }


def _serialize_sync_run(row: tuple[SyncRun, Source]) -> dict[str, Any]:
    run, source = row
    return {
        "id": run.id,
        "source_id": run.source_id,
        "source_type": source.type,
        "status": run.status,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "nodes_added": run.nodes_added,
        "nodes_updated": run.nodes_updated,
        "drift_count": run.drift_count,
        "error_message": run.error_message,
    }


def _serialize_setting(setting: AppSetting) -> dict[str, Any]:
    value = _mask_secret(setting.value) if setting.key in _SECRET_SETTING_KEYS else setting.value
    return {
        "id": setting.key,
        "key": setting.key,
        "value": value,
        "is_secret": setting.key in _SECRET_SETTING_KEYS,
        "updated_at": setting.updated_at,
    }


@dataclass(frozen=True)
class ResourceAdapter:
    key: str
    label: str
    columns: list[str]
    searchable_fields: list[str]
    build_query: QueryBuilder
    serialize: RowSerializer
    returns_scalar_models: bool = True


def _source_query(ctx: CurrentContext, project_id: str | None) -> Select[Any]:
    query = select(Source).where(Source.organization_id == ctx.organization_id)
    if project_id:
        query = query.where(Source.project_id == project_id)
    return query.order_by(Source.created_at.desc())


def _project_query(ctx: CurrentContext, project_id: str | None) -> Select[Any]:
    query = select(Project).where(Project.organization_id == ctx.organization_id)
    if project_id:
        query = query.where(Project.id == project_id)
    return query.order_by(Project.created_at.desc())


def _membership_query(ctx: CurrentContext, project_id: str | None) -> Select[Any]:
    del project_id
    return (
        select(OrganizationMembership, User)
        .join(User, OrganizationMembership.user_id == User.id)
        .where(OrganizationMembership.organization_id == ctx.organization_id)
        .order_by(OrganizationMembership.created_at.desc())
    )


def _page_query(ctx: CurrentContext, project_id: str | None) -> Select[Any]:
    query = select(DocPage).where(DocPage.organization_id == ctx.organization_id)
    if project_id:
        query = query.where(DocPage.project_id == project_id)
    return query.order_by(DocPage.updated_at.desc())


def _workflow_query(ctx: CurrentContext, project_id: str | None) -> Select[Any]:
    query = (
        select(PageWorkflow)
        .join(DocPage, PageWorkflow.page_id == DocPage.id)
        .where(DocPage.organization_id == ctx.organization_id)
    )
    if project_id:
        query = query.where(DocPage.project_id == project_id)
    return query.order_by(PageWorkflow.updated_at.desc())


def _workflow_audit_query(ctx: CurrentContext, project_id: str | None) -> Select[Any]:
    query = (
        select(WorkflowAuditLog)
        .join(DocPage, WorkflowAuditLog.page_id == DocPage.id)
        .where(DocPage.organization_id == ctx.organization_id)
    )
    if project_id:
        query = query.where(DocPage.project_id == project_id)
    return query.order_by(WorkflowAuditLog.created_at.desc())


def _drift_query(ctx: CurrentContext, project_id: str | None) -> Select[Any]:
    query = (
        select(DriftEvent, InfraNode)
        .join(InfraNode, DriftEvent.node_id == InfraNode.id)
        .join(Source, InfraNode.source_id == Source.id)
        .where(Source.organization_id == ctx.organization_id)
    )
    if project_id:
        query = query.where(Source.project_id == project_id)
    return query.order_by(DriftEvent.detected_at.desc())


def _sync_run_query(ctx: CurrentContext, project_id: str | None) -> Select[Any]:
    query = (
        select(SyncRun, Source)
        .join(Source, SyncRun.source_id == Source.id)
        .where(Source.organization_id == ctx.organization_id)
    )
    if project_id:
        query = query.where(Source.project_id == project_id)
    return query.order_by(SyncRun.started_at.desc())


def _settings_query(_: CurrentContext, project_id: str | None) -> Select[Any]:
    del project_id
    return select(AppSetting).order_by(AppSetting.updated_at.desc(), AppSetting.key.asc())


RESOURCES: dict[str, ResourceAdapter] = {
    "sources": ResourceAdapter(
        key="sources",
        label="Sources",
        columns=["id", "type", "url", "project_id", "last_synced", "created_at"],
        searchable_fields=["id", "type", "url", "project_id"],
        build_query=_source_query,
        serialize=_serialize_source,
    ),
    "projects": ResourceAdapter(
        key="projects",
        label="Projects",
        columns=["id", "name", "created_at"],
        searchable_fields=["id", "name"],
        build_query=_project_query,
        serialize=_serialize_project,
    ),
    "organization_memberships": ResourceAdapter(
        key="organization_memberships",
        label="Organization Memberships",
        columns=["id", "user_id", "login", "email", "role", "created_at"],
        searchable_fields=["user_id", "login", "email", "role"],
        build_query=_membership_query,
        serialize=_serialize_membership,
        returns_scalar_models=False,
    ),
    "doc_pages": ResourceAdapter(
        key="doc_pages",
        label="Pages",
        columns=["id", "source_id", "title", "version", "is_manually_edited", "updated_at"],
        searchable_fields=["id", "source_id", "title"],
        build_query=_page_query,
        serialize=_serialize_page,
    ),
    "page_workflows": ResourceAdapter(
        key="page_workflows",
        label="Page Workflows",
        columns=[
            "id",
            "page_id",
            "state",
            "submitted_by_id",
            "reviewed_by_id",
            "approved_by_id",
            "published_by_id",
            "updated_at",
        ],
        searchable_fields=["id", "page_id", "state"],
        build_query=_workflow_query,
        serialize=_serialize_workflow,
    ),
    "workflow_audit_logs": ResourceAdapter(
        key="workflow_audit_logs",
        label="Workflow Audit Logs",
        columns=[
            "id",
            "workflow_id",
            "page_id",
            "actor_id",
            "action",
            "from_state",
            "to_state",
            "created_at",
        ],
        searchable_fields=["id", "workflow_id", "page_id", "actor_id", "action", "comment"],
        build_query=_workflow_audit_query,
        serialize=_serialize_workflow_audit,
    ),
    "drift_events": ResourceAdapter(
        key="drift_events",
        label="Drift Events",
        columns=[
            "id",
            "node_id",
            "node_name",
            "page_id",
            "detected_at",
            "resolved",
            "resolved_at",
            "resolution_notes",
        ],
        searchable_fields=["id", "node_id", "node_name", "page_id", "resolution_notes"],
        build_query=_drift_query,
        serialize=_serialize_drift,
        returns_scalar_models=False,
    ),
    "sync_runs": ResourceAdapter(
        key="sync_runs",
        label="Sync Runs",
        columns=[
            "id",
            "source_id",
            "source_type",
            "status",
            "started_at",
            "completed_at",
            "nodes_added",
            "nodes_updated",
            "drift_count",
            "error_message",
        ],
        searchable_fields=["id", "source_id", "source_type", "status", "error_message"],
        build_query=_sync_run_query,
        serialize=_serialize_sync_run,
        returns_scalar_models=False,
    ),
    "app_settings": ResourceAdapter(
        key="app_settings",
        label="App Settings",
        columns=["id", "key", "value", "is_secret", "updated_at"],
        searchable_fields=["id", "key", "value"],
        build_query=_settings_query,
        serialize=_serialize_setting,
    ),
}


def list_resources() -> list[dict[str, str]]:
    return [{"key": resource.key, "label": resource.label} for resource in RESOURCES.values()]


def get_resource_adapter(resource: str) -> ResourceAdapter:
    adapter = RESOURCES.get(resource)
    if adapter is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    return adapter


def _materialize_rows(result: Any, adapter: ResourceAdapter) -> list[Any]:
    if adapter.returns_scalar_models:
        return list(result.scalars().all())
    return list(result.all())


async def list_resource_items(
    db: AsyncSession,
    *,
    ctx: CurrentContext,
    resource: str,
    limit: int,
    offset: int,
    q: str | None,
    project_id: str | None,
) -> dict[str, Any]:
    adapter = get_resource_adapter(resource)
    result = await db.execute(adapter.build_query(ctx, project_id))
    items = [adapter.serialize(row) for row in _materialize_rows(result, adapter)]
    if q:
        items = [item for item in items if _matches_query(item, q, adapter.searchable_fields)]
    total = len(items)
    paged_items = items[offset : offset + limit]
    return {
        "resource": adapter.key,
        "label": adapter.label,
        "columns": adapter.columns,
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": paged_items,
    }


async def get_resource_item(
    db: AsyncSession,
    *,
    ctx: CurrentContext,
    resource: str,
    item_id: str,
    project_id: str | None,
) -> dict[str, Any]:
    adapter = get_resource_adapter(resource)
    result = await db.execute(adapter.build_query(ctx, project_id))
    items = [adapter.serialize(row) for row in _materialize_rows(result, adapter)]
    for item in items:
        if str(item.get("id")) == item_id:
            return {
                "resource": adapter.key,
                "label": adapter.label,
                "item": item,
            }
    raise HTTPException(status_code=404, detail="Record not found")
