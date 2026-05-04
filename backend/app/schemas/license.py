"""License schema models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class LicenseInstallRequest(BaseModel):
    license_token: str


class LicenseRecordResponse(BaseModel):
    organization_id: str
    license_id: str | None = None
    plan: str
    issued_at: datetime | None = None
    expires_at: datetime | None = None
    status: str
    last_validated_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    enforcement_enabled: bool


class EntitlementsResponse(BaseModel):
    plan: str
    status: str
    enforcement_enabled: bool
    issued_at: datetime | None = None
    expires_at: datetime | None = None
    features: list[str]
    limits: dict[str, int]
    metadata: dict[str, Any] = {}
