"""Credential schema models for source authentication."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class CredentialCreate(BaseModel):
    """Create a new credential for a source."""

    credential_type: Literal["ssh_key", "token", "basic_auth"] = Field(
        ..., description="Type of credential: ssh_key, token, or basic_auth"
    )
    secret_value: str = Field(
        ...,
        description="The actual secret (key, token, or username:password)",
    )


class CredentialResponse(BaseModel):
    """Credential response model (masked for security)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    source_id: str
    credential_type: str
    created_at: datetime
    created_by: Optional[int] = None

    @property
    def masked_display(self) -> str:
        """Return a masked display of the credential type."""
        if self.credential_type == "ssh_key":
            return "SSH Key (***)"
        elif self.credential_type == "token":
            return "Token (***)"
        elif self.credential_type == "basic_auth":
            return "Basic Auth (***)"
        return "Unknown (***)"


class CredentialListResponse(BaseModel):
    """List of credentials for a source."""

    source_id: str
    credentials: list[CredentialResponse]
