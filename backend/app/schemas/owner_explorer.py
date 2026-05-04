"""Schema models for the owner explorer."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class OwnerExplorerResource(BaseModel):
    """Metadata for an owner explorer resource."""

    key: str
    label: str


class OwnerExplorerListResponse(BaseModel):
    """Paginated list response for an owner explorer resource."""

    resource: str
    label: str
    columns: list[str]
    total: int
    limit: int
    offset: int
    items: list[dict[str, Any]]


class OwnerExplorerDetailResponse(BaseModel):
    """Detail response for a single owner explorer record."""

    resource: str
    label: str
    item: dict[str, Any]
