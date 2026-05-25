"""Tests for product capability reporting and enforcement."""

import pytest

from app.core.config import get_settings


@pytest.mark.asyncio
async def test_read_my_capabilities(async_client, auth_headers):
    response = await async_client.get("/api/me/capabilities", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    capability_names = {item["name"] for item in data["capabilities"]}
    assert "ai_generation" in capability_names
    assert "semantic_search" in capability_names
    assert "scheduled_sync" in capability_names
    assert data["metadata"]["plan"] == "open_source"


@pytest.mark.asyncio
async def test_capability_gate_allows_all_features_when_enforced(async_client, auth_headers):
    """With open_source defaults, all features are available even when enforcement is on."""
    settings = get_settings()
    original = settings.license_enforcement_enabled
    settings.license_enforcement_enabled = True
    try:
        response = await async_client.get("/api/analytics", headers=auth_headers)
    finally:
        settings.license_enforcement_enabled = original

    assert response.status_code == 200
