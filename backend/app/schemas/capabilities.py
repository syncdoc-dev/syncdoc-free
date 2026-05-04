"""Capability schema models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CapabilityResponse(BaseModel):
    name: str
    enabled: bool
    source: str
    reason: str | None = None
    feature: str | None = None


class CapabilitiesResponse(BaseModel):
    capabilities: list[CapabilityResponse]
    enabled: list[str]
    disabled: list[str]
    metadata: dict[str, object] = Field(default_factory=dict)
