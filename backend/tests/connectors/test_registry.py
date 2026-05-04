"""Tests for the connector registry."""

import pytest

from app.connectors.base import ConnectorResult, IaCConnector
from app.connectors.registry import _REGISTRY, get_connector, list_connectors, register


class _DummyConnector(IaCConnector):
    connector_type = "dummy"

    async def pull(self):
        return {}

    async def parse(self, raw_data):
        return []


def test_register_and_get_connector():
    register(_DummyConnector)
    assert get_connector("dummy") is _DummyConnector
    # Cleanup
    _REGISTRY.pop("dummy", None)


def test_get_connector_unknown_raises():
    with pytest.raises(KeyError, match="No connector for type 'nonexistent'"):
        get_connector("nonexistent")


def test_list_connectors_includes_builtins():
    from app.connectors import ci_cd, docker, terraform  # noqa: F401

    types = list_connectors()
    assert "terraform" in types
    assert "docker" in types
    assert "ci_cd" in types


def test_connector_result_id_is_deterministic():
    r1 = ConnectorResult(kind="tf:aws_instance", name="web", config_json={"a": 1}, source_id="s1")
    r2 = ConnectorResult(kind="tf:aws_instance", name="web", config_json={"a": 1}, source_id="s1")
    assert r1.id == r2.id


def test_connector_result_hash_changes_with_config():
    r1 = ConnectorResult(kind="tf:aws_instance", name="web", config_json={"a": 1}, source_id="s1")
    r2 = ConnectorResult(kind="tf:aws_instance", name="web", config_json={"a": 2}, source_id="s1")
    assert r1.hash != r2.hash


def test_connector_result_hash_ignores_key_order():
    r1 = ConnectorResult(kind="x", name="y", config_json={"a": 1, "b": 2}, source_id="s")
    r2 = ConnectorResult(kind="x", name="y", config_json={"b": 2, "a": 1}, source_id="s")
    assert r1.hash == r2.hash
