import os

import pytest

from app.network_destination_policy import NetworkDestinationPolicy, NetworkPolicyError


def clear_proxies(monkeypatch) -> None:
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        monkeypatch.delenv(name, raising=False)


def test_airgapped_allows_exact_loopback_and_revalidates_redirect(monkeypatch) -> None:
    clear_proxies(monkeypatch)
    policy = NetworkDestinationPolicy(profile="airgapped", allowed_hosts={"localhost": {7777}}, resolver=lambda _: ["127.0.0.1"])
    approved = policy.approve("http://localhost:7777/mcp")
    assert approved.classification == "loopback"
    assert policy.approve_redirect(approved, "http://localhost:7777/next").host == "localhost"


def test_blocks_public_airgap_mixed_dns_cleartext_private_and_proxy(monkeypatch) -> None:
    clear_proxies(monkeypatch)
    with pytest.raises(NetworkPolicyError):
        NetworkDestinationPolicy(profile="airgapped", allowed_hosts={"public.test": {443}}, resolver=lambda _: ["8.8.8.8"]).approve("https://public.test")
    with pytest.raises(NetworkPolicyError):
        NetworkDestinationPolicy(profile="online", allowed_hosts={"mixed.test": {443}}, resolver=lambda _: ["10.0.0.1", "8.8.8.8"]).approve("https://mixed.test")
    with pytest.raises(NetworkPolicyError):
        NetworkDestinationPolicy(profile="local-network", allowed_hosts={"internal.test": {80}}, resolver=lambda _: ["10.0.0.1"]).approve("http://internal.test")
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.test")
    with pytest.raises(NetworkPolicyError, match="Proxy"):
        NetworkDestinationPolicy(profile="airgapped", allowed_hosts={"localhost": {1}}, resolver=lambda _: ["127.0.0.1"]).approve("http://localhost:1")
