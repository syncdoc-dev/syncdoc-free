"""Source schema models"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SourceCreate(BaseModel):
    """Create a new source"""

    type: str  # "terraform", "docker", "ansible", "git", "ci_cd"
    url: str = Field(..., min_length=1, max_length=2048)
    credentials_ref: Optional[str] = None
    project_id: Optional[str] = None


class SourceInspectRequest(BaseModel):
    type: str
    url: str = Field(..., min_length=1, max_length=2048)


class SourceInspectionResponse(BaseModel):
    source_type: str
    ok: bool
    summary: str
    matched_files: list[str]
    detected_types: list[str]
    warnings: list[str]


class SourceResponse(BaseModel):
    """Source response model"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    type: str
    url: str
    project_id: Optional[str] = None
    last_synced: Optional[datetime] = None
    created_at: datetime
