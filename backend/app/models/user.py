"""User model"""

from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, index=True)
    github_id: Mapped[int | None] = mapped_column(
        sa.BigInteger,
        unique=True,
        index=True,
        nullable=True,
    )
    login: Mapped[str] = mapped_column(sa.String, unique=True, index=True)
    email: Mapped[str | None] = mapped_column(sa.String, nullable=True, unique=True, index=True)
    name: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(sa.String, nullable=True)  # for local auth
    github_access_token: Mapped[str | None] = mapped_column(
        sa.Text,
        nullable=True,
    )  # stored encrypted
    auth_provider: Mapped[str] = mapped_column(sa.String, default="local")  # "local" or "github"
    theme_id: Mapped[str] = mapped_column(sa.String, default="original")
    marketing_opt_in: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    marketing_opt_in_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
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
