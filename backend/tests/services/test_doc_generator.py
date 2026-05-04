"""Tests for the AI doc generator service"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.node import InfraEdge, InfraNode
from app.models.page import DocPage
from app.models.source import Source
from app.services.doc_generator import (
    _build_prompt,
    _truncate_config,
    generate_doc_for_source,
)


@pytest.fixture
async def db_session():
    """Create an in-memory SQLite session for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def sample_source(db_session):
    """Create a sample source."""
    source = Source(
        id="src-test-001",
        type="terraform",
        url="/tmp/my-infra/main.tf",
    )
    db_session.add(source)
    await db_session.commit()
    return source


@pytest.fixture
async def sample_nodes(db_session, sample_source):
    """Create sample InfraNodes for the source."""
    nodes = [
        InfraNode(
            id="node-vpc-001",
            kind="tf:aws_vpc",
            name="main_vpc",
            config_json={"cidr_block": "10.0.0.0/16", "enable_dns": True},
            source_id=sample_source.id,
            hash="abc123",
        ),
        InfraNode(
            id="node-subnet-001",
            kind="tf:aws_subnet",
            name="public_subnet",
            config_json={"cidr_block": "10.0.1.0/24", "vpc_id": "main_vpc"},
            source_id=sample_source.id,
            hash="def456",
        ),
        InfraNode(
            id="node-var-001",
            kind="tf:variable",
            name="region",
            config_json={"default": "us-east-1", "type": "string"},
            source_id=sample_source.id,
            hash="ghi789",
        ),
    ]
    for node in nodes:
        db_session.add(node)
    await db_session.commit()
    return nodes


@pytest.fixture
async def sample_edges(db_session, sample_nodes):
    """Create sample InfraEdges."""
    edge = InfraEdge(
        id="edge-001",
        from_node_id="node-subnet-001",
        to_node_id="node-vpc-001",
        relation_type="depends_on",
    )
    db_session.add(edge)
    await db_session.commit()
    return [edge]


class TestBuildPrompt:
    def test_basic_prompt(self, sample_source):
        """Test prompt generation with minimal data."""
        source = sample_source
        # Create mock nodes directly (sync — no DB needed)
        nodes = [
            InfraNode(
                id="n1",
                kind="tf:aws_vpc",
                name="vpc",
                config_json={"cidr": "10.0.0.0/16"},
                source_id="src-test-001",
                hash="x",
            ),
        ]
        prompt = _build_prompt(source, nodes, [])
        assert "main.tf" in prompt
        assert "terraform" in prompt
        assert "tf:aws_vpc" in prompt
        assert "vpc" in prompt
        assert "Required Sections" in prompt
        assert "```mermaid" in prompt
        assert "at most 2 dependency hops" in prompt

    def test_prompt_with_edges(self, sample_source):
        """Test prompt includes dependency section."""
        nodes = [
            InfraNode(
                id="n1",
                kind="tf:aws_vpc",
                name="vpc",
                config_json={},
                source_id="src-test-001",
                hash="x",
            ),
            InfraNode(
                id="n2",
                kind="tf:aws_subnet",
                name="subnet",
                config_json={},
                source_id="src-test-001",
                hash="y",
            ),
        ]
        edges = [
            InfraEdge(
                id="e1",
                from_node_id="n2",
                to_node_id="n1",
                relation_type="depends_on",
            ),
        ]
        prompt = _build_prompt(sample_source, nodes, edges)
        assert "Dependencies" in prompt
        assert "subnet --[depends_on]--> vpc" in prompt

    def test_prompt_requests_compact_mermaid_diagram(self, sample_source):
        """Test prompt asks for a limited Mermaid diagram at the top."""
        nodes = [
            InfraNode(
                id="n1",
                kind="docker:service",
                name="api",
                config_json={},
                source_id="src-test-001",
                hash="x",
            ),
            InfraNode(
                id="n2",
                kind="docker:service",
                name="db",
                config_json={},
                source_id="src-test-001",
                hash="y",
            ),
        ]

        prompt = _build_prompt(sample_source, nodes, [])
        assert "compact Mermaid diagram" in prompt
        assert "Cap the diagram at roughly 8-12 nodes" in prompt
        assert "Do not attempt to reproduce the full infrastructure graph" in prompt
        assert "starts exactly with ```mermaid and ends with ```" in prompt
        assert "Do not indent the Mermaid diagram as a plain code block" in prompt
        assert "always include the Mermaid block" in prompt
        assert "syntactically valid Mermaid flowchart syntax" in prompt
        assert "Choose an arrangement that matches the system shape" in prompt
        assert "Prefer `flowchart LR`" in prompt
        assert "Prefer `flowchart TD`" in prompt

    def test_prompt_requests_front_loaded_ci_cd_section(self, sample_source):
        """Test prompt adds a CI/CD section near the top when pipeline nodes exist."""
        nodes = [
            InfraNode(
                id="n1",
                kind="ci:workflow",
                name="release",
                config_json={},
                source_id="src-test-001",
                hash="x",
            ),
            InfraNode(
                id="n2",
                kind="ci:job",
                name="deploy_prod",
                config_json={},
                source_id="src-test-001",
                hash="y",
            ),
        ]

        prompt = _build_prompt(sample_source, nodes, [])
        assert "CI/CD Delivery Overview" in prompt
        assert "immediately after the Mermaid diagram and before the general Overview" in prompt
        assert "pipeline stages, deployment environments, release flow, and deployment targets" in prompt

    def test_prompt_summary_mode(self, sample_source):
        """Test that large sources use summary mode."""
        nodes = [
            InfraNode(
                id=f"n{i}",
                kind="tf:aws_instance",
                name=f"instance_{i}",
                config_json={"ami": "ami-123"},
                source_id="src-test-001",
                hash=f"h{i}",
            )
            for i in range(35)
        ]
        prompt = _build_prompt(sample_source, nodes, [])
        # Summary mode should list names, not full configs
        assert "Resources:" in prompt
        assert "instance_0" in prompt


class TestTruncateConfig:
    def test_short_config(self):
        config = {"key": "value"}
        result = _truncate_config(config)
        assert "truncated" not in result

    def test_long_config(self):
        config = {"key": "x" * 1000}
        result = _truncate_config(config, max_chars=100)
        assert "truncated" in result
        assert len(result) < 1100


class TestGenerateDocForSource:
    @pytest.mark.asyncio
    async def test_generates_page(self, db_session, sample_source, sample_nodes):
        """Test that generate_doc_for_source creates a DocPage."""
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = "# Runbook\n\nGenerated documentation."

        with patch("app.services.doc_generator.get_llm_client", return_value=mock_llm):
            page = await generate_doc_for_source(sample_source.id, db_session)

        assert page is not None
        assert page.title.startswith("Runbook:")
        assert page.content_md == "# Runbook\n\nGenerated documentation."
        assert page.version == 1
        assert page.is_manually_edited == 0
        assert page.source_id == sample_source.id
        mock_llm.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_manually_edited(self, db_session, sample_source, sample_nodes):
        """Test that manually edited pages are not overwritten."""
        existing = DocPage(
            id=uuid.uuid4().hex[:16],
            source_id=sample_source.id,
            title="Manual Page",
            content_md="Hand-written docs",
            version=1,
            is_manually_edited=1,
        )
        db_session.add(existing)
        await db_session.commit()

        result = await generate_doc_for_source(sample_source.id, db_session)
        assert result is None

    @pytest.mark.asyncio
    async def test_updates_existing_page(self, db_session, sample_source, sample_nodes):
        """Test that re-generation updates an existing auto-generated page."""
        existing = DocPage(
            id=uuid.uuid4().hex[:16],
            source_id=sample_source.id,
            title="Old Title",
            content_md="Old content",
            version=1,
            is_manually_edited=0,
        )
        db_session.add(existing)
        await db_session.commit()

        mock_llm = AsyncMock()
        mock_llm.generate.return_value = "# Updated Runbook"

        with patch("app.services.doc_generator.get_llm_client", return_value=mock_llm):
            page = await generate_doc_for_source(sample_source.id, db_session)

        assert page is not None
        assert page.id == existing.id
        assert page.content_md == "# Updated Runbook"
        assert page.version == 2

    @pytest.mark.asyncio
    async def test_skips_no_nodes(self, db_session, sample_source):
        """Test that sources with no nodes return None."""
        mock_llm = AsyncMock()

        with patch("app.services.doc_generator.get_llm_client", return_value=mock_llm):
            result = await generate_doc_for_source(sample_source.id, db_session)

        assert result is None
        mock_llm.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_for_missing_source(self, db_session):
        """Test that missing source raises ValueError."""
        with pytest.raises(ValueError, match="Source not found"):
            await generate_doc_for_source("nonexistent", db_session)
