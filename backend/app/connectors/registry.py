"""Plugin registry for IaC connectors."""

from app.connectors.base import IaCConnector

_REGISTRY: dict[str, type[IaCConnector]] = {}


def register(connector_cls: type[IaCConnector]) -> type[IaCConnector]:
    """Class decorator to register a connector by its connector_type."""
    _REGISTRY[connector_cls.connector_type] = connector_cls
    return connector_cls


def get_connector(source_type: str) -> type[IaCConnector]:
    """Look up a connector class by source type string."""
    if source_type not in _REGISTRY:
        available = ", ".join(sorted(_REGISTRY.keys()))
        raise KeyError(f"No connector for type '{source_type}'. Available: {available}")
    return _REGISTRY[source_type]


def list_connectors() -> list[str]:
    """Return all registered connector type names."""
    return sorted(_REGISTRY.keys())
