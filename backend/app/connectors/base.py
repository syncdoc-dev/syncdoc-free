"""Base connector interface and result dataclass."""

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


def _make_id(source_id: str, kind: str, name: str) -> str:
    """Generate a deterministic node ID from source, kind, and name."""
    raw = f"{source_id}:{kind}:{name}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _normalize_for_hash(value: Any) -> Any:
    """Recursively normalize data for order-insensitive hashing."""
    if isinstance(value, list):
        normalized = [_normalize_for_hash(item) for item in value]
        if normalized and isinstance(normalized[0], dict):
            normalized.sort(key=lambda d: json.dumps(d, sort_keys=True, default=str))
        else:
            try:
                normalized.sort()
            except TypeError:
                pass
        return normalized
    if isinstance(value, dict):
        return {k: _normalize_for_hash(v) for k, v in sorted(value.items())}
    return value


def _make_hash(config: dict[str, Any]) -> str:
    """Generate a content hash for drift detection (order-insensitive for lists)."""
    normalized = _normalize_for_hash(config)
    serialized = json.dumps(normalized, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()


@dataclass
class ConnectorResult:
    """Output of a connector's parse() method. Maps to InfraNode fields."""

    kind: str
    name: str
    config_json: dict[str, Any]
    source_id: str
    edges: list[dict[str, str]] = field(default_factory=list)

    @property
    def id(self) -> str:
        return _make_id(self.source_id, self.kind, self.name)

    @property
    def hash(self) -> str:
        return _make_hash(self.config_json)


class IaCConnector(ABC):
    """Base class all IaC connectors must implement."""

    connector_type: str  # Must match Source.type values

    def __init__(self, source_id: str, url: str, credentials_ref: str | None = None):
        self.source_id = source_id
        self.url = url
        self.credentials_ref = credentials_ref

    async def connect(self) -> None:
        """Optional setup (authentication, etc). Default is no-op."""

    @abstractmethod
    async def pull(self) -> dict[str, Any]:
        """Fetch raw data from the source. Returns parsed file contents."""
        ...

    @abstractmethod
    async def parse(self, raw_data: dict[str, Any]) -> list[ConnectorResult]:
        """Transform raw data into ConnectorResult objects."""
        ...
