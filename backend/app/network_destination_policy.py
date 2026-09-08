"""Fail-closed destination policy shared by future MCP/network transports."""

import ipaddress
import os
import socket
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urlparse


class NetworkPolicyError(ValueError):
    pass


@dataclass(frozen=True)
class ApprovedDestination:
    url: str
    host: str
    port: int
    addresses: tuple[str, ...]
    classification: str


def classify_address(value: str) -> str:
    address = ipaddress.ip_address(value)
    if address.is_loopback:
        return "loopback"
    if address.is_private and not address.is_link_local:
        return "private"
    if address.is_global:
        return "public"
    return "restricted"


class NetworkDestinationPolicy:
    def __init__(self, *, profile: str, allowed_hosts: dict[str, set[int]], resolver: Callable[[str], list[str]] | None = None, allow_proxy: bool = False) -> None:
        if profile not in {"airgapped", "local-network", "online"}:
            raise NetworkPolicyError("Unknown connectivity profile.")
        self.profile = profile
        self.allowed_hosts = {host.casefold().rstrip("."): set(ports) for host, ports in allowed_hosts.items()}
        self.resolver = resolver or self._resolve
        self.allow_proxy = allow_proxy

    @staticmethod
    def _resolve(host: str) -> list[str]:
        return sorted({item[4][0] for item in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)})

    def approve(self, url: str, *, previous: ApprovedDestination | None = None) -> ApprovedDestination:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
            raise NetworkPolicyError("Destination URL is malformed or contains credentials/fragments.")
        host = parsed.hostname.casefold().rstrip(".")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if host not in self.allowed_hosts or port not in self.allowed_hosts[host]:
            raise NetworkPolicyError("Destination host and port are not exactly allowlisted.")
        if not self.allow_proxy and any(os.environ.get(name) for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy")):
            raise NetworkPolicyError("Proxy environment variables are prohibited for governed transport.")
        addresses = tuple(self.resolver(host))
        if not addresses:
            raise NetworkPolicyError("Destination DNS produced no addresses.")
        classes = {classify_address(address) for address in addresses}
        if len(classes) != 1 or "restricted" in classes:
            raise NetworkPolicyError("Destination resolves to mixed or restricted address classes.")
        classification = next(iter(classes))
        allowed = {"airgapped": {"loopback"}, "local-network": {"loopback", "private"}, "online": {"loopback", "private", "public"}}[self.profile]
        if classification not in allowed:
            raise NetworkPolicyError("Destination address class is prohibited by the active profile.")
        if classification != "loopback" and parsed.scheme != "https":
            raise NetworkPolicyError("Non-loopback destinations require TLS.")
        if previous is not None and (host != previous.host or port != previous.port or addresses != previous.addresses):
            raise NetworkPolicyError("Redirect or DNS revalidation changed the approved destination.")
        return ApprovedDestination(url, host, port, addresses, classification)

    def approve_redirect(self, previous: ApprovedDestination, location: str) -> ApprovedDestination:
        return self.approve(location, previous=previous)
