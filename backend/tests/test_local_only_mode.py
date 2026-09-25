"""Tests for Local-Only Mode network policy enforcement."""
import pytest

from app.network_policy import (
    LocalOnlyPolicy,
    NetworkPolicyError,
    get_local_only_policy,
    set_local_only_policy,
)


class TestLocalOnlyPolicy:
    def test_policy_defaults_to_off(self):
        policy = LocalOnlyPolicy()
        assert policy.local_only_mode is False
        assert policy.is_allowed_host("api.openai.com") is True

    def test_policy_blocks_cloud_endpoints_when_enabled(self):
        policy = LocalOnlyPolicy(local_only_mode=True)
        assert policy.is_cloud_endpoint("https://api.openai.com/v1/chat") is True
        assert policy.is_cloud_endpoint("https://api.anthropic.com/v1/messages") is True
        assert policy.is_cloud_endpoint("https://api.github.com/repos") is True

    def test_policy_allows_localhost_when_enabled(self):
        policy = LocalOnlyPolicy(local_only_mode=True)
        assert policy.is_allowed_host("127.0.0.1") is True
        assert policy.is_allowed_host("localhost") is True

    def test_policy_allows_private_ips_when_enabled(self):
        policy = LocalOnlyPolicy(local_only_mode=True, allow_private_network=True)
        assert policy.is_allowed_host("10.0.0.1") is True
        assert policy.is_allowed_host("192.168.1.1") is True
        assert policy.is_allowed_host("172.16.0.1") is True

    def test_policy_rejects_public_ips_when_enabled(self):
        policy = LocalOnlyPolicy(local_only_mode=True, allow_private_network=True)
        assert policy.is_allowed_host("8.8.8.8") is False
        assert policy.is_allowed_host("1.1.1.1") is False

    def test_policy_validates_url_allows_local(self):
        policy = LocalOnlyPolicy(local_only_mode=True)
        result = policy.validate_url("http://127.0.0.1:11434/v1/chat/completions")
        assert result["valid"] is True
        assert result["blocked"] is False

    def test_policy_validates_url_blocks_cloud(self):
        policy = LocalOnlyPolicy(local_only_mode=True)
        with pytest.raises(NetworkPolicyError) as exc_info:
            policy.validate_url("https://api.openai.com/v1/chat/completions")
        assert "Cloud endpoint blocked" in str(exc_info.value)

    def test_policy_validates_url_blocks_public_ip(self):
        policy = LocalOnlyPolicy(local_only_mode=True, allow_private_network=True)
        with pytest.raises(NetworkPolicyError) as exc_info:
            policy.validate_url("https://8.8.8.8:443/v1/chat")
        assert "not allowed" in str(exc_info.value).lower()

    def test_policy_rejects_non_http_protocols(self):
        policy = LocalOnlyPolicy(local_only_mode=True)
        with pytest.raises(NetworkPolicyError) as exc_info:
            policy.validate_url("ftp://example.com/file")
        # The error should mention either protocol or host not allowed
        error_msg = str(exc_info.value).lower()
        assert "protocol" in error_msg or "not allowed" in error_msg

    def test_policy_allows_custom_hosts(self):
        policy = LocalOnlyPolicy(
            local_only_mode=True,
            allow_private_network=False,  # Disable private network to test custom hosts only
            allowed_hosts=["10.30.75.229", "internal.company.local"],
        )
        assert policy.is_allowed_host("10.30.75.229") is True
        assert policy.is_allowed_host("internal.company.local") is True
        assert policy.is_allowed_host("192.168.1.1") is False  # Private network disabled

    def test_policy_status(self):
        policy = LocalOnlyPolicy(
            local_only_mode=True,
            allow_private_network=True,
            allowed_hosts=["127.0.0.1", "10.30.75.229"],
        )
        status = policy.get_status()
        assert status["localOnlyMode"] is True
        assert status["allowPrivateNetwork"] is True
        assert "127.0.0.1" in status["allowedHosts"]
        assert status["cloudEndpointsBlocked"] > 0


class TestGlobalPolicy:
    def test_get_policy_creates_default(self):
        # Clear any existing policy
        import app.network_policy as np
        np._default_policy = None
        
        policy = get_local_only_policy()
        assert isinstance(policy, LocalOnlyPolicy)
        assert policy.local_only_mode is False

    def test_set_policy_updates_global(self):
        import app.network_policy as np
        np._default_policy = None
        
        policy = set_local_only_policy(
            local_only_mode=True,
            allow_private_network=False,
        )
        assert policy.local_only_mode is True
        
        # Verify get_policy returns the same instance
        assert get_local_only_policy() is policy


class TestCloudEndpointDetection:
    @pytest.mark.parametrize(
        "url",
        [
            "https://api.openai.com/v1/chat",
            "https://api.anthropic.com/v1/messages",
            "https://api.cohere.ai/v1/chat",
            "https://api.mistral.ai/v1/chat",
            "https://api.groq.com/v1/chat",
            "https://*.openai.com/v1/chat",
            "https://*.azure.com/resource",
            "https://*.amazonaws.com/api",
            "https://*.googleapis.com/api",
            "https://copilot.microsoft.com/chat",
        ],
    )
    def test_detects_known_cloud_endpoints(self, url):
        policy = LocalOnlyPolicy()
        assert policy.is_cloud_endpoint(url) is True

    @pytest.mark.parametrize(
        "url",
        [
            "http://127.0.0.1:11434/v1/chat",
            "http://localhost:1234/v1/chat",
            "http://10.30.75.229:12434/engines/v1/chat",
            "http://192.168.1.100:8000/api/chat",
            "http://172.16.0.1:5000/v1/chat",
        ],
    )
    def test_does_not_flag_local_endpoints(self, url):
        policy = LocalOnlyPolicy()
        assert policy.is_cloud_endpoint(url) is False


class TestLocalOnlyIntegration:
    def test_provider_discovery_blocks_cloud_in_local_only(self):
        """Test that cloud endpoints are filtered during provider discovery."""
        policy = LocalOnlyPolicy(local_only_mode=True)
        
        # These should be blocked
        with pytest.raises(NetworkPolicyError):
            policy.validate_url("https://api.openai.com/v1/chat/completions")
        
        # These should be allowed
        assert policy.validate_url("http://127.0.0.1:11434/v1/chat/completions")["valid"] is True
        assert policy.validate_url("http://10.30.75.229:12434/engines/v1/chat/completions")["valid"] is True
