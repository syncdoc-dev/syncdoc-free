"""Page schema models"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PageCreate(BaseModel):
    """Create a new page"""

    title: str
    content_md: str
    source_id: Optional[str] = None
    project_id: Optional[str] = None


class PageUpdate(BaseModel):
    """Update an existing page"""

    title: Optional[str] = None
    content_md: Optional[str] = None


class PageResponse(BaseModel):
    """Page response model"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    source_id: Optional[str] = None
    project_id: Optional[str] = None
    title: str
    content_md: str
    version: int
    is_manually_edited: int
    created_at: datetime
    updated_at: datetime
    workflow: Optional[dict] = None
