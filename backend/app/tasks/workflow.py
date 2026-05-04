"""Workflow tasks for async processing"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.celery_app import app
from app.core.config import settings
from app.models.page import DocPage
from app.models.workflow import PageVersion, PageWorkflow, WorkflowState
from app.services.notifications import send_workflow_notification

logger = logging.getLogger(__name__)


@app.task(bind=True)
def process_workflow_notification(self, workflow_id: str, action: str):
    """
    Send notifications for workflow events.

    This task is called asynchronously after workflow state changes
    to notify relevant users via Slack, email, or webhook.
    """
    return asyncio.run(_process_notification_async(workflow_id, action, self.request.id))


async def _process_notification_async(
    workflow_id: str, action: str, task_id: str | None = None
) -> dict:
    """Async implementation for sending workflow notifications."""
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        try:
            workflow = await session.get(PageWorkflow, workflow_id)
            if not workflow:
                logger.warning(f"Workflow not found: {workflow_id}")
                return {"status": "skipped", "reason": "workflow_not_found"}

            page = await session.get(DocPage, workflow.page_id)
            if not page:
                logger.warning(f"Page not found: {workflow.page_id}")
                return {"status": "skipped", "reason": "page_not_found"}

            await send_workflow_notification(workflow, page, action, db=session)

            return {
                "status": "completed",
                "workflow_id": workflow_id,
                "task_id": task_id,
                "action": action,
            }

        except Exception:
            logger.exception(f"Workflow notification failed for {workflow_id}")
            raise
        finally:
            pass

    await engine.dispose()


@app.task(bind=True)
def cleanup_old_versions(self, page_id: str, keep_last: int = 10):
    """
    Cleanup old page versions, keeping only the most recent ones.

    This is a maintenance task that can be run periodically to
    prevent the version history from growing too large.
    """
    return asyncio.run(_cleanup_versions_async(page_id, keep_last, self.request.id))


async def _cleanup_versions_async(page_id: str, keep_last: int, task_id: str | None = None) -> dict:
    """Async implementation for cleaning up old versions."""
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        try:
            result = await session.execute(
                select(PageVersion)
                .where(PageVersion.page_id == page_id)
                .order_by(PageVersion.version.desc())
            )
            versions = result.scalars().all()

            if len(versions) <= keep_last:
                return {
                    "status": "skipped",
                    "page_id": page_id,
                    "reason": "versions_within_limit",
                    "current_count": len(versions),
                }

            versions_to_delete = versions[keep_last:]
            for version in versions_to_delete:
                await session.delete(version)

            await session.commit()

            logger.info(
                "Cleaned up %d old versions for page %s, kept %d",
                len(versions_to_delete),
                page_id,
                keep_last,
            )

            return {
                "status": "completed",
                "page_id": page_id,
                "task_id": task_id,
                "deleted_count": len(versions_to_delete),
                "kept_count": keep_last,
            }

        except Exception:
            logger.exception(f"Version cleanup failed for page {page_id}")
            raise

    await engine.dispose()


@app.task(bind=True)
def auto_archive_old_published(self, days_old: int = 90):
    """
    Automatically archive published pages that haven't been updated in a while.

    This is a scheduled task that can be run periodically to keep the
    system clean and encourage teams to review old documentation.
    """
    return asyncio.run(_auto_archive_async(days_old, self.request.id))


async def _auto_archive_async(days_old: int, task_id: str | None = None) -> dict:
    """Async implementation for auto-archiving old published pages."""
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)

    async with session_factory() as session:
        try:
            result = await session.execute(
                select(PageWorkflow).where(
                    PageWorkflow.state == WorkflowState.PUBLISHED.value,
                    PageWorkflow.updated_at < cutoff_date,
                )
            )
            workflows = result.scalars().all()

            archived_count = 0
            for workflow in workflows:
                workflow.state = WorkflowState.ARCHIVED.value
                archived_count += 1

            await session.commit()

            logger.info(f"Auto-archived {archived_count} pages older than {days_old} days")

            return {
                "status": "completed",
                "task_id": task_id,
                "archived_count": archived_count,
                "days_old": days_old,
            }

        except Exception:
            logger.exception("Auto-archive task failed")
            raise

    await engine.dispose()
