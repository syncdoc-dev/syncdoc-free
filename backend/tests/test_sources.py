"""Tests for Sources API endpoints"""

from pathlib import Path

import pytest


def _make_terraform_source(path: Path) -> str:
    path.mkdir(parents=True, exist_ok=True)
    (path / "main.tf").write_text('resource "null_resource" "example" {}')
    return str(path)


def _make_docker_source(path: Path) -> str:
    path.mkdir(parents=True, exist_ok=True)
    (path / "docker-compose.yml").write_text("services:\n  app:\n    image: nginx:latest\n")
    return str(path)


@pytest.mark.asyncio
async def test_create_source(async_client, auth_headers, tmp_path):
    source_path = _make_terraform_source(tmp_path / "my-infra")
    response = await async_client.post(
        "/api/sources/",
        headers=auth_headers,
        json={"type": "terraform", "url": source_path},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "terraform"
    assert data["url"] == source_path
    assert data["id"]


@pytest.mark.asyncio
async def test_create_source_invalid_type(async_client, auth_headers):
    response = await async_client.post(
        "/api/sources/",
        headers=auth_headers,
        json={"type": "invalid_type", "url": "/tmp"},
    )
    assert response.status_code == 400
    assert "Invalid source type" in response.json()["detail"]


@pytest.mark.asyncio
async def test_list_sources(async_client, auth_headers, tmp_path):
    await async_client.post(
        "/api/sources/",
        headers=auth_headers,
        json={"type": "terraform", "url": _make_terraform_source(tmp_path / "a")},
    )
    await async_client.post(
        "/api/sources/",
        headers=auth_headers,
        json={"type": "docker", "url": _make_docker_source(tmp_path / "b")},
    )
    response = await async_client.get("/api/sources/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_get_source(async_client, auth_headers, tmp_path):
    create = await async_client.post(
        "/api/sources/",
        headers=auth_headers,
        json={"type": "docker", "url": _make_docker_source(tmp_path / "x")},
    )
    source_id = create.json()["id"]

    response = await async_client.get(f"/api/sources/{source_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == source_id


@pytest.mark.asyncio
async def test_get_source_not_found(async_client, auth_headers):
    response = await async_client.get("/api/sources/nonexistent", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_source(async_client, auth_headers, tmp_path):
    create = await async_client.post(
        "/api/sources/",
        headers=auth_headers,
        json={"type": "terraform", "url": _make_terraform_source(tmp_path / "del")},
    )
    source_id = create.json()["id"]

    response = await async_client.delete(f"/api/sources/{source_id}", headers=auth_headers)
    assert response.status_code == 204

    get_resp = await async_client.get(f"/api/sources/{source_id}", headers=auth_headers)
    assert get_resp.status_code == 404
