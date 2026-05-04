"""SyncDoc IaC connectors."""

from app.connectors.base import ConnectorResult, IaCConnector
from app.connectors.registry import get_connector, list_connectors, register

__all__ = [
    "ConnectorResult",
    "IaCConnector",
    "get_connector",
    "list_connectors",
    "register",
]

# Auto-register built-in connectors on import
from app.connectors import ansible, ci_cd, docker, git, terraform  # noqa: E402, F401
