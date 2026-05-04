"""Drift event schema models"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DriftEventResponse(BaseModel):
    """Drift event response model"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    node_id: str
    node_name: Optional[str] = None
    node_kind: Optional[str] = None
    page_id: Optional[str] = None
    detected_at: datetime
    diff_json: dict
    resolved: int
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    created_at: datetime


class DriftResolve(BaseModel):
    """Resolve a drift event"""

    resolution_notes: Optional[str] = None
