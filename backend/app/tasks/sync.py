"""Sync tasks for ingesting IaC sources"""

import asyncio
import logging
import shutil
import tempfile
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.celery_app import app
from app.connectors import get_connector
from app.core.config import settings
from app.models.drift import DriftEvent
from app.models.graph_edge_manual import GraphEdgeManual
from app.models.graph_note import GraphNote
from app.models.node import InfraEdge, InfraNode
from app.models.page import DocPage
from app.models.source import Source
from app.models.sync import SyncRun
from app.services.doc_generator import generate_doc_for_source
from app.services.notifications import send_drift_alert
from app.tasks.base import SyncDocTask

logger = logging.getLogger(__name__)


def _coerce_utc(dt: datetime | None) -> datetime | None:
    """Normalize DB datetimes so naive/aware values can be compared safely."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _compute_diff(old_config: dict, new_config: dict) -> dict:
    """Compute a simple diff between two config dicts.

    Returns a dict with 'added', 'removed', and 'changed' keys.
    """
    old_keys = set(old_config.keys())
    new_keys = set(new_config.keys())

    diff: dict = {
        "added": {k: new_config[k] for k in new_keys - old_keys},
        "removed": {k: old_config[k] for k in old_keys - new_keys},
        "changed": {},
    }

    for key in old_keys & new_keys:
        old_val = old_config[key]
        new_val = new_config[key]
        if old_val != new_val:
            diff["changed"][key] = {"old": old_val, "new": new_val}

    # Strip empty sections
    return {k: v for k, v in diff.items() if v}


@app.task(base=SyncDocTask, bind=True)
def sync_source(self, source_id: str):
    """
    Sync an IaC source: pull, parse, build graph, generate docs.

    This is the main orchestration task that:
    1. Fetches the source from the database
    2. Runs the appropriate connector (Terraform, Docker, Ansible, etc.)
    3. Parses raw data into InfraNode objects
    4. Builds a knowledge graph with edges (dependencies)
    5. Detects drift from previous snapshot
    6. Generates documentation with Claude
    7. Creates SyncRun audit log
    """
    return asyncio.run(_sync_source_async(source_id, self.request.id))


async def _upsert_edges(session: AsyncSession, results, node_id_map):
    """Create InfraEdges from parsed connector results, skipping duplicates."""
    for result in results:
        for edge_def in result.edges:
            target_id = node_id_map.get(edge_def["target_name"])
            if not target_id:
                continue  # Target not in this source — skip

            edge_check = await session.execute(
                select(InfraEdge).where(
                    InfraEdge.from_node_id == result.id,
                    InfraEdge.to_node_id == target_id,
                    InfraEdge.relation_type == edge_def["relation_type"],
                )
            )
            if edge_check.scalar_one_or_none():
                continue  # Edge already exists

            edge = InfraEdge(
                id=uuid.uuid4().hex[:16],
                from_node_id=result.id,
                to_node_id=target_id,
                relation_type=edge_def["relation_type"],
            )
            session.add(edge)


async def _sync_source_async(source_id: str, task_id: str | None = None) -> dict:  # noqa: C901
    """Async implementation of the sync pipeline."""
    # Create a fresh engine per task to avoid event loop conflicts in Celery
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    clone_dir = None
    async with session_factory() as session:
        # 0. Create SyncRun audit log
        sync_run = SyncRun(
            id=uuid.uuid4().hex[:16],
            source_id=source_id,
            started_at=datetime.now(timezone.utc),
            status="in_progress",
        )
        session.add(sync_run)
        await session.flush()

        try:
            # 1. Load source from database
            source = await session.get(Source, source_id)
            if not source:
                raise ValueError(f"Source not found: {source_id}")

            # 2. If the URL is a git remote, clone it first and use the local path
            source_url = source.url
            git_env: dict[str, str] = {}
            ssh_key_path = None

            if _is_git_url(source_url):
                from git import Repo
                from git.exc import GitCommandError

                from app.connectors.exceptions import PullError
                from app.services.credentials import CredentialManager

                clone_dir = tempfile.mkdtemp(prefix="syncdoc-sync-")

                # Try to get and use credentials for authentication
                credential = await CredentialManager.get_credential(session, source.id)
                if credential:
                    git_env, ssh_key_path = CredentialManager.get_git_auth_env(
                        credential, source_url
                    )
                    logger.info("Using credential for git clone of %s", source.id)

                try:
                    logger.info("Cloning %s to %s", source_url, clone_dir)
                    if credential and credential.credential_type == "token":
                        # Inject token into URL
                        secret = CredentialManager.decrypt_credential(credential)
                        source_url_with_auth = CredentialManager.inject_token_in_url(
                            source_url, secret
                        )
                        Repo.clone_from(source_url_with_auth, clone_dir, depth=1, env=git_env)
                    elif credential and credential.credential_type == "ssh_key":
                        # Use SSH key via env
                        Repo.clone_from(source_url, clone_dir, depth=1, env=git_env)
                    else:
                        # No per-source credential — check for global GitHub token
                        from sqlalchemy import select as sa_select

                        from app.models.setting import AppSetting

                        global_token_row = await session.execute(
                            sa_select(AppSetting).where(AppSetting.key == "github_token")
                        )
                        global_token = global_token_row.scalar_one_or_none()
                        if global_token and global_token.value:
                            logger.info("Using global GitHub token for clone of %s", source.id)
                            url_with_token = CredentialManager.inject_token_in_url(
                                source_url, global_token.value
                            )
                            Repo.clone_from(url_with_token, clone_dir, depth=1)
                        else:
                            Repo.clone_from(source_url, clone_dir, depth=1)
                except GitCommandError as e:
                    shutil.rmtree(clone_dir, ignore_errors=True)
                    if ssh_key_path:
                        import os as os_module

                        os_module.unlink(ssh_key_path)
                    raise PullError(f"Failed to clone {source_url}: {e}") from e
                source_url = clone_dir

            # 3. Get connector for source.type
            connector_cls = get_connector(source.type)
            connector = connector_cls(source.id, source_url, source.credentials_ref)

            # 4. Pull raw data
            await connector.connect()
            raw_data = await connector.pull()

            # 5. Parse into ConnectorResult objects
            results = await connector.parse(raw_data)

            # Deduplicate by node ID — connectors like GitConnector run
            # TerraformConnector per-directory with recursive rglob, so
            # parent and child dirs both emit the same node IDs.  Processing
            # the same ID twice in one sync creates false intra-sync drift
            # that flips the baseline and oscillates on every sync.
            # First occurrence wins (consistent with _deduplicate in connectors).
            seen_ids: set[str] = set()
            deduped: list = []
            for r in results:
                if r.id not in seen_ids:
                    seen_ids.add(r.id)
                    deduped.append(r)
            results = deduped

            # 6. Upsert InfraNodes — detect drift when hash changes
            nodes_added = 0
            nodes_updated = 0
            drift_events: list[DriftEvent] = []
            node_id_map: dict[str, str] = {}  # name -> node.id for edge resolution

            # Find existing page for this source (for linking drift events)
            existing_page = (
                (await session.execute(select(DocPage).where(DocPage.source_id == source_id)))
                .scalars()
                .first()
            )
            page_id = existing_page.id if existing_page else None

            for result in results:
                # Only set bare name if not already claimed (first writer wins)
                if result.name not in node_id_map:
                    node_id_map[result.name] = result.id

                # Terraform-specific mappings
                if result.kind.startswith("tf:"):
                    tf_kind = result.kind.replace("tf:", "")
                    node_id_map[f"{tf_kind}.{result.name}"] = result.id
                    if result.kind == "tf:variable":
                        node_id_map[f"var.{result.name}"] = result.id
                    elif result.kind.startswith("tf:data."):
                        data_type = tf_kind.replace("data.", "")
                        node_id_map[f"data.{data_type}.{result.name}"] = result.id

                # Ansible-specific mappings: prioritize core types for
                # bare-name lookup so edges like "targets: managers"
                # resolve to the group, not the group_vars node.
                if result.kind.startswith("ansible:"):
                    an_type = result.kind.replace("ansible:", "")
                    node_id_map[f"ansible:{an_type}:{result.name}"] = result.id
                    # Core types (group, host, role) take priority for bare names
                    if an_type in ("group", "host", "role", "playbook"):
                        node_id_map[result.name] = result.id

                # Docker-specific mappings
                if result.kind.startswith("docker:"):
                    dk_type = result.kind.replace("docker:", "")
                    node_id_map[f"docker:{dk_type}:{result.name}"] = result.id

                existing = await session.get(InfraNode, result.id)

                if existing and existing.hash == result.hash:
                    continue  # No change — skip

                if existing and existing.hash != result.hash:
                    # Drift detected — config changed since last sync
                    diff = _compute_diff(existing.config_json, result.config_json)
                    if diff:
                        # Check if a resolved drift event already exists for this node
                        # (pick most recent if multiple exist)
                        existing_resolved_drift = (
                            (
                                await session.execute(
                                    select(DriftEvent)
                                    .where(
                                        DriftEvent.node_id == result.id,
                                        DriftEvent.resolved == 1,
                                    )
                                    .order_by(DriftEvent.resolved_at.desc())
                                )
                            )
                            .scalars()
                            .first()
                        )

                        # Only create a new drift event if no resolved drift exists
                        if not existing_resolved_drift:
                            drift_event = DriftEvent(
                                id=uuid.uuid4().hex[:16],
                                node_id=result.id,
                                page_id=page_id,
                                detected_at=datetime.now(timezone.utc),
                                diff_json=diff,
                                resolved=0,
                                created_at=datetime.now(timezone.utc),
                            )
                            session.add(drift_event)
                            drift_events.append(drift_event)
                            logger.info(
                                "Drift detected on node %s (%s): %d changes",
                                result.name,
                                result.kind,
                                sum(len(v) for v in diff.values()),
                            )
                        else:
                            logger.info(
                                "Drift detected on node %s (%s) but already "
                                "marked resolved; skipping new event",
                                result.name,
                                result.kind,
                            )
                    nodes_updated += 1
                else:
                    nodes_added += 1

                node = InfraNode(
                    id=result.id,
                    kind=result.kind,
                    name=result.name,
                    config_json=result.config_json,
                    source_id=source_id,
                    hash=result.hash,
                )
                await session.merge(node)

            # 7. Create InfraEdges from parsed edges
            await _upsert_edges(session, results, node_id_map)

            # 8. Update source.last_synced
            source.last_synced = datetime.now(timezone.utc)

            # 9. Update SyncRun
            sync_run.status = "completed"
            sync_run.completed_at = datetime.now(timezone.utc)
            sync_run.nodes_added = nodes_added
            sync_run.nodes_updated = nodes_updated
            sync_run.drift_count = len(drift_events)

            await session.commit()

            logger.info(
                "Synced source %s: %d added, %d updated, %d drift events",
                source_id,
                nodes_added,
                nodes_updated,
                len(drift_events),
            )

            # Send Slack notification if drift was detected
            if drift_events:
                drift_payloads = []
                for de in drift_events:
                    drift_node = await session.get(InfraNode, de.node_id)
                    drift_payloads.append(
                        {
                            "node_name": drift_node.name if drift_node else de.node_id,
                            "node_kind": drift_node.kind if drift_node else "",
                            "diff": de.diff_json,
                        }
                    )
                try:
                    await send_drift_alert(source.url, drift_payloads, db=session)
                except Exception:
                    logger.exception("Slack notification failed — continuing")

            # Generate documentation if nodes changed, notes changed, or no page exists yet
            page = None
            total_changes = nodes_added + nodes_updated
            should_generate = total_changes > 0 or existing_page is None

            if existing_page is not None:
                node_ids = [result.id for result in results]
                page_updated_at = _coerce_utc(existing_page.updated_at)
                notes_updated_at = await session.scalar(
                    select(func.max(GraphNote.updated_at)).where(
                        GraphNote.organization_id == source.organization_id,
                        GraphNote.project_id == source.project_id,
                        or_(
                            GraphNote.source_id == source_id,
                            GraphNote.source_id.is_(None),
                            GraphNote.from_node_id.in_(node_ids),
                            GraphNote.to_node_id.in_(node_ids),
                        ),
                    )
                )
                manual_updated_at = await session.scalar(
                    select(func.max(GraphEdgeManual.updated_at)).where(
                        GraphEdgeManual.organization_id == source.organization_id,
                        GraphEdgeManual.project_id == source.project_id,
                        or_(
                            GraphEdgeManual.source_id == source_id,
                            GraphEdgeManual.from_node_id.in_(node_ids),
                            GraphEdgeManual.to_node_id.in_(node_ids),
                        ),
                    )
                )
                notes_updated_at = _coerce_utc(notes_updated_at)
                manual_updated_at = _coerce_utc(manual_updated_at)
                if page_updated_at and notes_updated_at and notes_updated_at > page_updated_at:
                    should_generate = True
                if page_updated_at and manual_updated_at and manual_updated_at > page_updated_at:
                    should_generate = True

            if should_generate:
                try:
                    page = await generate_doc_for_source(source_id, session)
                    if page:
                        logger.info("Generated doc page %s for source %s", page.id, source_id)
                except Exception:
                    logger.exception("Doc generation failed for source %s — continuing", source_id)

        except Exception as exc:
            sync_run.status = "failed"
            sync_run.completed_at = datetime.now(timezone.utc)
            sync_run.error_message = str(exc)[:500]
            await session.commit()
            raise
        finally:
            # Clean up SSH key if created
            if ssh_key_path:
                try:
                    import os as os_module

                    os_module.unlink(ssh_key_path)
                except Exception:
                    pass

    # Clean up cloned repo
    if clone_dir:
        shutil.rmtree(clone_dir, ignore_errors=True)

    await engine.dispose()

    return {
        "status": "completed",
        "source_id": source_id,
        "task_id": task_id,
        "nodes_added": nodes_added,
        "nodes_updated": nodes_updated,
        "drift_events": len(drift_events),
        "pages_generated": 1 if page else 0,
    }


def _is_git_url(url: str) -> bool:
    """Check if a URL looks like a git remote (not a local path)."""
    return url.startswith(("https://", "http://", "git://", "ssh://", "git@"))
