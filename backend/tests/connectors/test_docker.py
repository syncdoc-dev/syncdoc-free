"""Tests for DockerConnector."""

from pathlib import Path

import pytest

from app.connectors.docker import DockerConnector
from app.connectors.exceptions import PullError

FIXTURES = Path(__file__).parent / "fixtures" / "docker"


@pytest.fixture
def connector():
    return DockerConnector(source_id="test-src", url=str(FIXTURES))


async def test_pull_reads_compose_and_dockerfile(connector):
    raw = await connector.pull()
    assert len(raw["compose"]) >= 1
    assert "Dockerfile" in raw["dockerfiles"]


async def test_pull_invalid_dir_raises():
    c = DockerConnector(source_id="x", url="/nonexistent/path")
    with pytest.raises(PullError, match="not a directory"):
        await c.pull()


async def test_parse_services(connector):
    raw = await connector.pull()
    results = await connector.parse(raw)

    services = [r for r in results if r.kind == "docker:service"]
    names = {s.name for s in services}
    assert "api" in names
    assert "db" in names
    assert "cache" in names


async def test_parse_volumes(connector):
    raw = await connector.pull()
    results = await connector.parse(raw)

    volumes = [r for r in results if r.kind == "docker:volume"]
    names = {v.name for v in volumes}
    assert "app-data" in names
    assert "pg-data" in names


async def test_parse_networks(connector):
    raw = await connector.pull()
    results = await connector.parse(raw)

    networks = [r for r in results if r.kind == "docker:network"]
    assert any(n.name == "backend" for n in networks)


async def test_parse_service_depends_on_edges(connector):
    raw = await connector.pull()
    results = await connector.parse(raw)

    api_service = next(r for r in results if r.kind == "docker:service" and r.name == "api")
    dep_targets = [
        e["target_name"] for e in api_service.edges if e["relation_type"] == "depends_on"
    ]
    assert "db" in dep_targets
    assert "cache" in dep_targets


async def test_parse_service_volume_edges(connector):
    raw = await connector.pull()
    results = await connector.parse(raw)

    api_service = next(r for r in results if r.kind == "docker:service" and r.name == "api")
    vol_targets = [
        e["target_name"] for e in api_service.edges if e["relation_type"] == "mounts_volume"
    ]
    assert "app-data" in vol_targets


async def test_parse_service_network_edges(connector):
    raw = await connector.pull()
    results = await connector.parse(raw)

    api_service = next(r for r in results if r.kind == "docker:service" and r.name == "api")
    net_targets = [
        e["target_name"] for e in api_service.edges if e["relation_type"] == "joins_network"
    ]
    assert "backend" in net_targets


async def test_parse_dockerfile_image(connector):
    raw = await connector.pull()
    results = await connector.parse(raw)

    images = [r for r in results if r.kind == "docker:image"]
    assert len(images) >= 1

    image = images[0]
    assert len(image.config_json["stages"]) == 2  # multi-stage build
    assert "8000" in image.config_json["ports"]
    assert image.config_json["healthcheck"] is not None


async def test_parse_dockerfile_multistage_edges(connector):
    raw = await connector.pull()
    results = await connector.parse(raw)

    image = next(r for r in results if r.kind == "docker:image")
    copy_edges = [e for e in image.edges if e["relation_type"] == "copies_from"]
    assert any(e["target_name"] == "builder" for e in copy_edges)


async def test_parse_empty_data():
    c = DockerConnector(source_id="x", url="/tmp")
    results = await c.parse({"compose": [], "dockerfiles": {}})
    assert results == []


async def test_result_ids_deterministic(connector):
    raw = await connector.pull()
    r1 = await connector.parse(raw)
    r2 = await connector.parse(raw)

    ids1 = sorted(r.id for r in r1)
    ids2 = sorted(r.id for r in r2)
    assert ids1 == ids2
