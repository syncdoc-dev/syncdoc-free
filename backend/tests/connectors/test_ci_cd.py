"""Tests for CiCdConnector."""

from app.connectors.ci_cd import CiCdConnector
from app.connectors.registry import list_connectors


def test_ci_cd_connector_registered():
    assert "ci_cd" in list_connectors()


async def test_parse_github_actions(ci_cd_fixtures_dir):
    connector = CiCdConnector("src-ci", str(ci_cd_fixtures_dir / "github"))
    raw = await connector.pull()
    results = await connector.parse(raw)

    kinds = {result.kind for result in results}
    names = {result.name for result in results}

    assert "ci:workflow" in kinds
    assert "ci:stage" in kinds
    assert "ci:job" in kinds
    assert "ci:environment" in kinds
    assert "ci:deployment_target" in kinds
    assert "github:.github/workflows/release.yml" in names
    assert "env:production" in names
    assert "target:container_registry:ghcr.io/syncdoc-dev/syncdoc/api:latest" in names
    assert "target:argo_application:syncdoc-prod" in names


async def test_parse_gitlab_ci(ci_cd_fixtures_dir):
    connector = CiCdConnector("src-ci", str(ci_cd_fixtures_dir / "gitlab"))
    raw = await connector.pull()
    results = await connector.parse(raw)

    names = {result.name for result in results}
    deploy_job = next(
        result for result in results if result.name == "gitlab:.gitlab-ci.yml:deploy_prod"
    )

    assert "gitlab:.gitlab-ci.yml" in names
    assert "gitlab:.gitlab/deploy.yml" in names
    assert "gitlab:.gitlab-ci.yml:deploy" in names
    assert "env:production" in names
    assert any(
        edge["relation_type"] == "deploys_to" and edge["target_name"] == "env:production"
        for edge in deploy_job.edges
    )
    assert "target:kubernetes:cluster" in names
    assert (
        "target:container_registry:registry.gitlab.com/syncdoc-dev/syncdoc/frontend:$CI_COMMIT_SHA"
        in names
    )
