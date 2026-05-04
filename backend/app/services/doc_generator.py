"""AI-powered documentation generator for IaC sources."""

import json
import logging
import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.graph_edge_manual import GraphEdgeManual
from app.models.graph_note import GraphNote
from app.models.node import InfraEdge, InfraNode
from app.models.page import DocPage
from app.models.source import Source
from app.services.capabilities import Capability, is_capability_enabled
from app.services.embeddings import get_embedding
from app.services.llm import get_llm_client

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are an infrastructure documentation expert. You generate clear, actionable \
runbook documentation for infrastructure managed by code (Terraform, Docker, etc.).

Your output is Markdown. Be precise, reference actual resource names and \
configurations, and focus on what an on-call engineer needs to know.

Do not include fenced code blocks around the entire response — write natural \
Markdown with headers, tables, and inline code where appropriate."""

MAX_CONFIG_CHARS = 500
MAX_NODES_FULL = 30


async def generate_doc_for_source(  # noqa: C901
    source_id: str,
    session: AsyncSession,
    *,
    force: bool = False,
) -> DocPage | None:
    """Generate documentation for a source from its parsed InfraNodes.

    Returns the created/updated DocPage, or None if skipped.
    """
    source = await session.get(Source, source_id)
    if not source:
        raise ValueError(f"Source not found: {source_id}")

    if not await is_capability_enabled(
        source.organization_id or "",
        Capability.AI_GENERATION,
        session,
    ):
        logger.info(
            "Skipping doc generation for %s - AI generation capability unavailable",
            source_id,
        )
        return None

    # Check for existing page — skip if manually edited
    existing = await session.execute(select(DocPage).where(DocPage.source_id == source_id))
    existing_page = existing.scalars().first()
    if existing_page and existing_page.is_manually_edited and not force:
        logger.info("Skipping doc generation for %s — manually edited", source_id)
        return None

    # Load nodes and edges
    nodes_result = await session.execute(select(InfraNode).where(InfraNode.source_id == source_id))
    nodes = list(nodes_result.scalars().all())

    if not nodes:
        logger.info("No nodes for source %s — skipping doc generation", source_id)
        return None

    edge_ids = [n.id for n in nodes]
    edges_result = await session.execute(
        select(InfraEdge).where(InfraEdge.from_node_id.in_(edge_ids))
    )
    edges = list(edges_result.scalars().all())

    node_ids = [n.id for n in nodes]
    manual_edges_result = await session.execute(
        select(GraphEdgeManual).where(
            GraphEdgeManual.project_id == source.project_id,
            GraphEdgeManual.organization_id == source.organization_id,
        )
    )
    manual_edges = [
        e
        for e in manual_edges_result.scalars().all()
        if e.source_id == source_id or (e.from_node_id in node_ids and e.to_node_id in node_ids)
    ]

    notes_result = await session.execute(
        select(GraphNote).where(
            GraphNote.project_id == source.project_id,
            GraphNote.organization_id == source.organization_id,
            (
                (GraphNote.source_id == source_id)
                | (GraphNote.source_id.is_(None))
                | (GraphNote.from_node_id.in_(node_ids))
                | (GraphNote.to_node_id.in_(node_ids))
            ),
        )
    )
    notes = list(notes_result.scalars().all())

    # Build prompt and call LLM
    user_prompt = _build_prompt(source, nodes, edges, manual_edges, notes)

    llm = await get_llm_client(db=session)
    content_md = await llm.generate(SYSTEM_PROMPT, user_prompt)

    # Build title from source
    title = f"Runbook: {source.url.rstrip('/').split('/')[-1]} ({source.type})"

    # Upsert page
    if existing_page:
        existing_page.content_md = content_md
        existing_page.title = title
        existing_page.version += 1
        if force:
            existing_page.is_manually_edited = 0
        if not existing_page.organization_id:
            existing_page.organization_id = source.organization_id
        if not existing_page.project_id:
            existing_page.project_id = source.project_id
        await session.commit()
        await session.refresh(existing_page)
        logger.info(
            "Updated doc page %s (v%d)",
            existing_page.id,
            existing_page.version,
        )
        page = existing_page
    else:
        page = DocPage(
            id=uuid.uuid4().hex[:16],
            source_id=source_id,
            organization_id=source.organization_id,
            project_id=source.project_id,
            title=title,
            content_md=content_md,
            version=1,
            is_manually_edited=0,
        )
        session.add(page)
        await session.commit()
        await session.refresh(page)
        logger.info("Created doc page %s for source %s", page.id, source_id)

    # Generate embedding
    try:
        embedding = await get_embedding(f"{page.title}\n{page.content_md[:2000]}", db=session)
        if embedding:
            page.embedding = embedding
            await session.commit()
            logger.info("Generated embedding for page %s", page.id)
    except Exception as e:
        logger.warning("Failed to generate embedding for page %s: %s", page.id, e)

    return page


def _build_prompt(
    source: Source,
    nodes: list[InfraNode],
    edges: list[InfraEdge],
    manual_edges: list[GraphEdgeManual] | None = None,
    notes: list[GraphNote] | None = None,
) -> str:
    """Build the user prompt from source data."""
    manual_edges = manual_edges or []
    notes = notes or []

    # Group nodes by kind
    grouped: dict[str, list[InfraNode]] = defaultdict(list)
    for node in nodes:
        grouped[node.kind].append(node)

    has_ci_cd = any(node.kind.startswith("ci:") for node in nodes)

    # Build node index for edge resolution
    node_by_id = {n.id: n for n in nodes}

    parts = [
        "Generate a runbook for the following infrastructure source.\n",
        "## Source",
        f"- Path: {source.url}",
        f"- Type: {source.type}",
        f"- Last synced: {source.last_synced or 'never'}\n",
        f"## Resources ({len(nodes)} total)\n",
    ]

    use_summary = len(nodes) > MAX_NODES_FULL

    _append_resource_sections(parts, grouped, use_summary)
    _append_edge_section(parts, "## Dependencies\n", edges, node_by_id)
    _append_edge_section(
        parts, "## Manual Connections\n", manual_edges, node_by_id, use_manual_label=True
    )
    _append_notes_section(parts, notes, node_by_id)

    required_sections_intro = (
        "## Required Sections\n"
        "At the very top of the document, before the Overview, include a compact Mermaid "
        "diagram in a ```mermaid fenced block that summarizes the most important service "
        "dependencies.\n"
        "- The Mermaid diagram must be wrapped in a fenced block that starts exactly with "
        "```mermaid and ends with ```.\n"
        "- Do not indent the Mermaid diagram as a plain code block.\n"
        "- Keep the Mermaid diagram intentionally small and readable.\n"
        "- Limit it to the most important resources and relationships only.\n"
        "- Prefer a shallow view with at most 2 dependency hops from the core components.\n"
        "- Cap the diagram at roughly 8-12 nodes and omit repetitive leaf nodes.\n"
        "- Do not attempt to reproduce the full infrastructure graph; the interactive graph "
        "already exists for detailed exploration.\n"
        "- Unless the source has only one isolated resource, always include the Mermaid block.\n"
        "- The Mermaid block must be syntactically valid Mermaid flowchart syntax.\n"
        "- Prefer simple labels over clever labels. Avoid special punctuation in edge labels.\n"
        "- Choose an arrangement that matches the system shape instead of defaulting blindly.\n"
        "- Prefer `flowchart LR` when showing left-to-right delivery flow or layered systems.\n"
        "- Prefer `flowchart TD` when showing stacked infrastructure layers or "
        "hierarchical groups.\n"
        "- Use a small number of meaningful subgraphs such as `Runtime`, `Data`, "
        "`Edge`, `CI/CD`, `Delivery`, or `Operations` when they improve readability.\n"
        "- Keep related nodes near each other and avoid long zig-zagging cross-links.\n"
        "- For mixed infrastructure and CI/CD sources, separate delivery pipeline elements from "
        "runtime infrastructure so the diagram reads as two cooperating layers rather than one "
        "sprawling network.\n"
        "- If you cannot produce a valid Mermaid diagram, omit the diagram rather than emitting "
        "broken Mermaid.\n"
        "\n"
        "Generate a runbook with these sections:\n"
    )

    if has_ci_cd:
        required_sections_body = (
            "1. **CI/CD Delivery Overview** — Only if CI/CD resources are present. Place this "
            "section immediately after the Mermaid diagram and before the general Overview. "
            "Summarize pipeline stages, deployment environments, release flow, and deployment "
            "targets in a concise operator-friendly way.\n"
            "2. **Overview** — What this infrastructure does, in 2-3 sentences\n"
            "3. **Resource Inventory** — Table of all resources with type, name, and key "
            "attributes\n"
            "4. **Architecture & Dependencies** — How resources relate to each other\n"
            "5. **Common Operations** — Step-by-step for: terraform plan, terraform apply, "
            "terraform destroy, with relevant flags/vars\n"
            "6. **Troubleshooting** — Common issues based on the resource types present\n"
            "7. **Variables & Outputs** — Document any variables and outputs\n"
            "8. **Operator Notes** — Include any operator notes exactly as provided"
        )
    else:
        required_sections_body = (
            "1. **Overview** — What this infrastructure does, in 2-3 sentences\n"
            "2. **Resource Inventory** — Table of all resources with type, name, and key "
            "attributes\n"
            "3. **Architecture & Dependencies** — How resources relate to each other\n"
            "4. **Common Operations** — Step-by-step for: terraform plan, terraform apply, "
            "terraform destroy, with relevant flags/vars\n"
            "5. **Troubleshooting** — Common issues based on the resource types present\n"
            "6. **Variables & Outputs** — Document any variables and outputs\n"
            "7. **Operator Notes** — Include any operator notes exactly as provided"
        )

    parts.append(required_sections_intro + required_sections_body)

    return "\n".join(parts)


def _truncate_config(config: dict, max_chars: int = MAX_CONFIG_CHARS) -> str:
    """Truncate config JSON to stay within token limits."""
    full = json.dumps(config, indent=2, default=str)
    if len(full) <= max_chars:
        return full
    return full[:max_chars] + "\n  ... (truncated)"


def _append_resource_sections(
    parts: list[str], grouped: dict[str, list[InfraNode]], use_summary: bool
) -> None:
    for kind in sorted(grouped.keys()):
        kind_nodes = grouped[kind]
        parts.append(f"### {kind} ({len(kind_nodes)})\n")

        if use_summary and not kind.startswith(("tf:variable", "tf:output")):
            names = [node.name for node in kind_nodes]
            parts.append(f"Resources: {', '.join(names)}\n")
            continue

        for node in kind_nodes:
            parts.append(f"**{node.name}**")
            config_str = _truncate_config(node.config_json)
            parts.append(f"```json\n{config_str}\n```\n")


def _append_edge_section(
    parts: list[str],
    title: str,
    edges: list[InfraEdge] | list[GraphEdgeManual],
    node_by_id: dict[str, InfraNode],
    *,
    use_manual_label: bool = False,
) -> None:
    if not edges:
        return

    parts.append(title)
    for edge in edges:
        from_node = node_by_id.get(edge.from_node_id)
        to_node = node_by_id.get(edge.to_node_id)
        if not from_node or not to_node:
            continue

        label = edge.label if use_manual_label else edge.relation_type
        parts.append(f"- {from_node.name} --[{label or 'manual'}]--> {to_node.name}")
    parts.append("")


def _append_notes_section(
    parts: list[str], notes: list[GraphNote], node_by_id: dict[str, InfraNode]
) -> None:
    if not notes:
        return

    parts.append("## Operator Notes\n")
    for note in notes:
        from_node = node_by_id.get(note.from_node_id or "")
        to_node = node_by_id.get(note.to_node_id or "")

        if from_node and to_node:
            parts.append(f"- Between {from_node.name} and {to_node.name}: {note.content}")
        elif from_node:
            parts.append(f"- Near {from_node.name}: {note.content}")
        elif to_node:
            parts.append(f"- Near {to_node.name}: {note.content}")
        else:
            parts.append(f"- {note.content}")
    parts.append("")
