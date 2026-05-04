"""Organization schema models"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    created_at: datetime


class OrganizationUpdate(BaseModel):
    name: str


class OrgMemberResponse(BaseModel):
    user_id: int
    login: str
    email: Optional[str] = None
    role: str
    created_at: datetime


class OrgUserCreate(BaseModel):
    login: str
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    password: str = Field(..., min_length=8, max_length=72)
    role: Literal["viewer", "member", "admin", "owner"] = "member"


class OrgMemberRoleUpdate(BaseModel):
    role: Literal["viewer", "member", "admin", "owner"]
