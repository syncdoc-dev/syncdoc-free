"""Tests for Pages API endpoints"""

from pathlib import Path

import pytest


def _make_terraform_source(path: Path) -> str:
    path.mkdir(parents=True, exist_ok=True)
    (path / "main.tf").write_text('resource "null_resource" "example" {}')
    return str(path)


@pytest.mark.asyncio
async def test_create_page(async_client, auth_headers):
    response = await async_client.post(
        "/api/pages/",
        headers=auth_headers,
        json={"title": "Test Page", "content_md": "# Hello\nWorld"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Page"
    assert data["content_md"] == "# Hello\nWorld"
    assert data["is_manually_edited"] == 1
    assert data["version"] == 1
    assert data["id"]


@pytest.mark.asyncio
async def test_create_page_with_source(async_client, auth_headers, tmp_path):
    # Create a source first
    source_path = _make_terraform_source(tmp_path / "test")
    source = await async_client.post(
        "/api/sources/", headers=auth_headers, json={"type": "terraform", "url": source_path}
    )
    source_id = source.json()["id"]

    response = await async_client.post(
        "/api/pages/",
        headers=auth_headers,
        json={
            "title": "Linked Page",
            "content_md": "# Linked",
            "source_id": source_id,
        },
    )
    assert response.status_code == 201
    assert response.json()["source_id"] == source_id


@pytest.mark.asyncio
async def test_list_pages(async_client, auth_headers):
    await async_client.post(
        "/api/pages/", headers=auth_headers, json={"title": "Page A", "content_md": "A"}
    )
    await async_client.post(
        "/api/pages/", headers=auth_headers, json={"title": "Page B", "content_md": "B"}
    )
    response = await async_client.get("/api/pages/", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) >= 2


@pytest.mark.asyncio
async def test_list_pages_filter_by_source(async_client, auth_headers, tmp_path):
    source_path = _make_terraform_source(tmp_path / "filter")
    source = await async_client.post(
        "/api/sources/", headers=auth_headers, json={"type": "terraform", "url": source_path}
    )
    source_id = source.json()["id"]

    await async_client.post(
        "/api/pages/",
        headers=auth_headers,
        json={"title": "Linked", "content_md": "x", "source_id": source_id},
    )
    await async_client.post(
        "/api/pages/", headers=auth_headers, json={"title": "Unlinked", "content_md": "y"}
    )

    response = await async_client.get(f"/api/pages/?source_id={source_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert all(p["source_id"] == source_id for p in data)


@pytest.mark.asyncio
async def test_get_page(async_client, auth_headers):
    create = await async_client.post(
        "/api/pages/", headers=auth_headers, json={"title": "Get Me", "content_md": "content"}
    )
    page_id = create.json()["id"]

    response = await async_client.get(f"/api/pages/{page_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["title"] == "Get Me"


@pytest.mark.asyncio
async def test_get_page_not_found(async_client, auth_headers):
    response = await async_client.get("/api/pages/nonexistent", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_page(async_client, auth_headers):
    create = await async_client.post(
        "/api/pages/", headers=auth_headers, json={"title": "Original", "content_md": "old"}
    )
    page_id = create.json()["id"]

    response = await async_client.put(
        f"/api/pages/{page_id}",
        headers=auth_headers,
        json={"title": "Updated", "content_md": "new content"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated"
    assert data["content_md"] == "new content"
    assert data["version"] == 2
    assert data["is_manually_edited"] == 1


@pytest.mark.asyncio
async def test_update_page_partial(async_client, auth_headers):
    create = await async_client.post(
        "/api/pages/", headers=auth_headers, json={"title": "Keep Title", "content_md": "old"}
    )
    page_id = create.json()["id"]

    response = await async_client.put(
        f"/api/pages/{page_id}", headers=auth_headers, json={"content_md": "new only"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Keep Title"
    assert data["content_md"] == "new only"


@pytest.mark.asyncio
async def test_update_page_not_found(async_client, auth_headers):
    response = await async_client.put(
        "/api/pages/nonexistent", headers=auth_headers, json={"title": "Nope"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_page(async_client, auth_headers):
    create = await async_client.post(
        "/api/pages/", headers=auth_headers, json={"title": "Delete Me", "content_md": "bye"}
    )
    page_id = create.json()["id"]

    response = await async_client.delete(f"/api/pages/{page_id}", headers=auth_headers)
    assert response.status_code == 204

    get_resp = await async_client.get(f"/api/pages/{page_id}", headers=auth_headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_page_not_found(async_client, auth_headers):
    response = await async_client.delete("/api/pages/nonexistent", headers=auth_headers)
    assert response.status_code == 404
