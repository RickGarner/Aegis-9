"""Network policy enforcement for Local-Only Mode."""
from __future__ import annotations

import re
from ipaddress import IPv4Address, AddressValueError
from pathlib import Path
from typing import Any


class NetworkPolicyError(Exception):
    """Raised when a network operation violates policy."""
    pass


class LocalOnlyPolicy:
    """Enforces network restrictions for Local-Only Mode."""
    
    # Cloud endpoints that must be blocked in Local-Only Mode
    CLOUD_ENDPOINTS = [
        r"api\.openai\.com",
        r"api\.anthropic\.com",
        r"api\.cohere\.ai",
        r"api\.mistral\.ai",
        r"api\.groq\.com",
        r"\.openai\.com",
        r"\.anthropic\.com",
        r"\.azure\.com",
        r"\.amazonaws\.com",
        r"\.googleapis\.com",
        r"\.microsoft\.com",
        r"copilot\.microsoft\.com",
        r"api\.github\.com",
    ]
    
    # Private IP ranges that are allowed
    PRIVATE_RANGES = [
        "127.0.0.0/8",      # Loopback
        "10.0.0.0/8",       # Private A
        "172.16.0.0/12",    # Private B
        "192.168.0.0/16",   # Private C
        "169.254.0.0/16",   # Link-local
    ]
    
    def __init__(
        self,
        local_only_mode: bool = False,
        allow_private_network: bool = True,
        allowed_hosts: list[str] | None = None,
    ) -> None:
        self.local_only_mode = local_only_mode
        self.allow_private_network = allow_private_network
        self.allowed_hosts = set(allowed_hosts or ["127.0.0.1", "localhost"])
        self._cloud_pattern = re.compile(
            "|".join(self.CLOUD_ENDPOINTS),
            re.IGNORECASE,
        )
        self._private_networks = [
            net for net in self.PRIVATE_RANGES
        ]
    
    def is_cloud_endpoint(self, url: str) -> bool:
        """Check if a URL is a known cloud endpoint."""
        return bool(self._cloud_pattern.search(url))
    
    def is_allowed_host(self, host: str) -> bool:
        """Check if a host is allowed under current policy."""
        if not self.local_only_mode:
            return True
        
        # Normalize host
        host = host.lower().strip()
        if host in ("localhost", "127.0.0.1"):
            return True
        
        # Check against explicit allowlist
        if host in self.allowed_hosts:
            return True
        
        # Check if private network is allowed
        if self.allow_private_network:
            try:
                ip = IPv4Address(host.split(":")[0])  # Remove port if present
                for network in self._private_networks:
                    import ipaddress
                    if ip in ipaddress.ip_network(network, strict=False):
                        return True
            except AddressValueError:
                # Not an IP address, could be hostname
                pass
        
        return False
    
    def validate_url(self, url: str) -> dict[str, Any]:
        """Validate a URL against the network policy.
        
        Args:
            url: The URL to validate
            
        Returns:
            Dictionary with validation result and details
            
        Raises:
            NetworkPolicyError: If the URL violates policy
        """
        import urllib.parse
        
        result = {
            "valid": True,
            "blocked": False,
            "reason": None,
        }
        
        if not self.local_only_mode:
            return result
        
        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname or ""
        
        # Check if it's a cloud endpoint
        if self.is_cloud_endpoint(url):
            result["valid"] = False
            result["blocked"] = True
            result["reason"] = "Cloud endpoint blocked in Local-Only Mode"
            raise NetworkPolicyError(result["reason"])
        
        # Check if host is allowed
        if not self.is_allowed_host(host):
            result["valid"] = False
            result["blocked"] = True
            result["reason"] = f"Host '{host}' not allowed in Local-Only Mode"
            raise NetworkPolicyError(result["reason"])
        
        # Check protocol
        if parsed.scheme not in ("http", "https"):
            result["valid"] = False
            result["blocked"] = True
            result["reason"] = f"Protocol '{parsed.scheme}' not allowed"
            raise NetworkPolicyError(result["reason"])
        
        return result
    
    def get_status(self) -> dict[str, Any]:
        """Get the current policy status."""
        return {
            "localOnlyMode": self.local_only_mode,
            "allowPrivateNetwork": self.allow_private_network,
            "allowedHosts": list(self.allowed_hosts),
            "cloudEndpointsBlocked": len(self.CLOUD_ENDPOINTS),
        }


# Global policy instance (can be reconfigured at runtime)
_default_policy: LocalOnlyPolicy | None = None


def get_local_only_policy() -> LocalOnlyPolicy:
    """Get the global Local-Only policy instance."""
    global _default_policy
    if _default_policy is None:
        _default_policy = LocalOnlyPolicy()
    return _default_policy


def set_local_only_policy(
    local_only_mode: bool = False,
    allow_private_network: bool = True,
    allowed_hosts: list[str] | None = None,
) -> LocalOnlyPolicy:
    """Set the global Local-Only policy instance."""
    global _default_policy
    _default_policy = LocalOnlyPolicy(
        local_only_mode=local_only_mode,
        allow_private_network=allow_private_network,
        allowed_hosts=allowed_hosts,
    )
    return _default_policy
