import json
from pathlib import Path

import pytest

from app.mcp_registry import McpRegistryError, discover_tools, load_registry, validate_registry


def valid_registry() -> dict:
    return {"schemaVersion": 1, "connectivityProfile": "airgapped", "servers": [{"id": "local.docs", "displayName": "Local Docs", "enabled": True, "transport": "loopback-http", "connectivity": "local", "version": "1.0.0", "health": "healthy", "credentialRef": None, "timeoutSeconds": 10, "concurrencyLimit": 2, "audit": True, "endpoint": "http://127.0.0.1:7777/mcp", "tools": [{"name": "docs.search", "description": "Search local documentation", "enabled": True, "risk": "R0", "allowedRoles": ["developer"], "allowedTargets": ["local-docs"], "outboundFields": ["query"], "approvalRequired": False}]}]}


def test_validates_and_discovers_healthy_local_entry(tmp_path: Path) -> None:
    value = valid_registry()
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    assert load_registry(path) == value
    assert discover_tools(value)[0]["name"] == "docs.search"


@pytest.mark.parametrize("mutate", [
    lambda value: value.update(extra=True),
    lambda value: value["servers"][0].update(endpoint="http://example.com/mcp"),
    lambda value: value["servers"][0]["tools"][0].update(risk="W2", approvalRequired=False),
    lambda value: value["servers"][0].update(credentialRef="actual secret value!"),
])
def test_registry_fails_closed_for_unknown_remote_unsafe_or_secret_like_entries(mutate) -> None:
    value = valid_registry()
    mutate(value)
    with pytest.raises(McpRegistryError):
        validate_registry(value)
