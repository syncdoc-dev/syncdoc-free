"""Source credential model for storing encrypted secrets."""

from datetime import datetime, timezone
from typing import Literal

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

CredentialType = Literal["ssh_key", "token", "basic_auth"]


class SourceCredential(Base):
    """Encrypted credentials for accessing private IaC sources."""

    __tablename__ = "source_credentials"

    id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    source_id: Mapped[str] = mapped_column(
        sa.String, sa.ForeignKey("sources.id", ondelete="CASCADE"), index=True
    )
    credential_type: Mapped[str] = mapped_column(
        sa.String, nullable=False
    )  # "ssh_key", "token", "basic_auth"
    encrypted_value: Mapped[str] = mapped_column(sa.Text, nullable=False)  # Fernet-encrypted secret
    created_by: Mapped[int | None] = mapped_column(
        sa.Integer,
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
