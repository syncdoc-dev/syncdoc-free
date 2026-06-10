"""Auth context types."""

from dataclasses import dataclass

from app.models.user import User


@dataclass(frozen=True)
class CurrentContext:
    user: User
    organization_id: str
    role: str

    @property
    def login(self) -> str:
        return self.user.login
