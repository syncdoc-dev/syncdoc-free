"""Tests for GitConnector."""

import pytest

from app.connectors.exceptions import PullError
from app.connectors.git import GitConnector
from app.connectors.registry import list_connectors


def test_git_connector_registered():
    assert "git" in list_connectors()


async def test_pull_invalid_url_raises():
    c = GitConnector(source_id="x", url="https://invalid.example/no-repo.git")
    with pytest.raises(PullError, match="Failed to clone"):
        await c.pull()


async def test_parse_empty_data():
    c = GitConnector(source_id="x", url="/tmp")
    results = await c.parse({"terraform_dirs": [], "docker_dirs": [], "ci_cd_root": None})
    assert results == []


async def test_parse_delegates_to_terraform(terraform_fixtures_dir):
    """GitConnector should delegate terraform dirs to TerraformConnector."""
    c = GitConnector(source_id="test-src", url=str(terraform_fixtures_dir))
    raw = {
        "repo_path": str(terraform_fixtures_dir),
        "terraform_dirs": [str(terraform_fixtures_dir)],
        "docker_dirs": [],
        "ci_cd_root": None,
    }
    results = await c.parse(raw)
    kinds = {r.kind for r in results}
    assert any(k.startswith("tf:") for k in kinds)


async def test_parse_delegates_to_docker(docker_fixtures_dir):
    """GitConnector should delegate docker dirs to DockerConnector."""
    c = GitConnector(source_id="test-src", url=str(docker_fixtures_dir))
    raw = {
        "repo_path": str(docker_fixtures_dir),
        "terraform_dirs": [],
        "docker_dirs": [str(docker_fixtures_dir)],
        "ci_cd_root": None,
    }
    results = await c.parse(raw)
    kinds = {r.kind for r in results}
    assert any(k.startswith("docker:") for k in kinds)


async def test_parse_delegates_to_ci_cd(ci_cd_fixtures_dir):
    c = GitConnector(source_id="test-src", url=str(ci_cd_fixtures_dir / "github"))
    raw = {
        "repo_path": str(ci_cd_fixtures_dir / "github"),
        "terraform_dirs": [],
        "docker_dirs": [],
        "ci_cd_root": str(ci_cd_fixtures_dir / "github"),
    }
    results = await c.parse(raw)
    kinds = {r.kind for r in results}
    assert any(k.startswith("ci:") for k in kinds)
