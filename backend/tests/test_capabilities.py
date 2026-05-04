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
    assert "scheduled_sync" in data["disabled"]
    assert data["metadata"]["plan"] == "free"


@pytest.mark.asyncio
async def test_capability_gate_blocks_unlicensed_analytics(async_client, auth_headers):
    settings = get_settings()
    original = settings.license_enforcement_enabled
    settings.license_enforcement_enabled = True
    try:
        response = await async_client.get("/api/analytics", headers=auth_headers)
    finally:
        settings.license_enforcement_enabled = original

    assert response.status_code == 403
    detail = response.json()["detail"]
    assert detail["code"] == "feature_not_in_plan"
    assert detail["capability"] == "analytics"
