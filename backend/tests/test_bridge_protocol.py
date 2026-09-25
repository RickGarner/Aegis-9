"""
Tests for Aegis-9 Authenticated Local Bridge

Covers:
- Bridge protocol message types and envelopes
- Authentication and signature verification
- Bridge server endpoints
- Approval request/response workflow
- Event and evidence submission
"""

import json
import secrets
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import hmac
import hashlib

from app.bridge_protocol import (
    BridgeEnvelope,
    StatusPayload,
    ApprovalRequestPayload,
    ApprovalResponsePayload,
    ApprovalStatus,
    EventPayload,
    EvidencePayload,
    ArtifactHandoffPayload,
    BridgeEndpoints,
    compute_signature,
    verify_signature,
    BridgeSource,
    MessageType,
    ActivityStatus,
)


class TestBridgeEnvelope(unittest.TestCase):
    """Test bridge envelope serialization."""
    
    def test_envelope_to_dict(self):
        envelope = BridgeEnvelope(
            protocol_version="1.0.0",
            source=BridgeSource.AEGIS_DEVELOPER_STUDIO,
            message_type=MessageType.STATUS,
            timestamp=datetime.now(timezone.utc).isoformat(),
            nonce=secrets.token_hex(16),
            payload={"test": "data"},
        )
        
        data = envelope.to_dict()
        
        self.assertEqual(data["protocolVersion"], "1.0.0")
        self.assertEqual(data["source"], "aegis-developer-studio")
        self.assertEqual(data["type"], "status")
        self.assertIn("timestamp", data)
        self.assertIn("nonce", data)
        self.assertEqual(data["payload"], {"test": "data"})
    
    def test_envelope_from_dict(self):
        data = {
            "protocolVersion": "1.0.0",
            "source": "aegis-developer-studio",
            "type": "status",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "nonce": secrets.token_hex(16),
            "payload": {"test": "data"},
        }
        
        envelope = BridgeEnvelope.from_dict(data)
        
        self.assertEqual(envelope.protocol_version, "1.0.0")
        self.assertEqual(envelope.source, BridgeSource.AEGIS_DEVELOPER_STUDIO)
        self.assertEqual(envelope.message_type, MessageType.STATUS)
        self.assertEqual(envelope.payload, {"test": "data"})


class TestStatusPayload(unittest.TestCase):
    """Test status payload serialization."""
    
    def test_status_payload_to_dict(self):
        payload = StatusPayload(
            product_version="1.0.0",
            session_id=secrets.token_hex(16),
            repository_paths=["/repo1", "/repo2"],
            provider="local",
            model="test-model",
            activity=ActivityStatus.IDLE,
            is_local_only=True,
        )
        
        data = payload.to_dict()
        
        self.assertEqual(data["productVersion"], "1.0.0")
        self.assertEqual(data["sessionId"], payload.session_id)
        self.assertEqual(data["repositoryPaths"], ["/repo1", "/repo2"])
        self.assertEqual(data["provider"], "local")
        self.assertEqual(data["model"], "test-model")
        self.assertEqual(data["activity"], "idle")
        self.assertTrue(data["isLocalOnly"])
    
    def test_status_payload_from_dict(self):
        data = {
            "productVersion": "2.0.0",
            "sessionId": "test-session",
            "repositoryPaths": ["/repo1"],
            "provider": "ollama",
            "model": "llama3",
            "activity": "editing",
            "isLocalOnly": True,
            "connectedAt": datetime.now(timezone.utc).isoformat(),
        }
        
        payload = StatusPayload.from_dict(data)
        
        self.assertEqual(payload.product_version, "2.0.0")
        self.assertEqual(payload.session_id, "test-session")
        self.assertEqual(payload.provider, "ollama")
        self.assertEqual(payload.model, "llama3")
        self.assertEqual(payload.activity, ActivityStatus.EDITING)


class TestApprovalPayloads(unittest.TestCase):
    """Test approval request/response payloads."""
    
    def test_approval_request_to_dict(self):
        payload = ApprovalRequestPayload(
            request_id="req-123",
            operation="file.create",
            description="Create new file",
            target_path="/path/to/file",
            requires_supervisor=True,
            timeout_seconds=300,
            metadata={"key": "value"},
        )
        
        data = payload.to_dict()
        
        self.assertEqual(data["requestId"], "req-123")
        self.assertEqual(data["operation"], "file.create")
        self.assertEqual(data["description"], "Create new file")
        self.assertEqual(data["targetPath"], "/path/to/file")
        self.assertTrue(data["requiresSupervisor"])
        self.assertEqual(data["timeoutSeconds"], 300)
    
    def test_approval_response_to_dict(self):
        payload = ApprovalResponsePayload(
            request_id="req-123",
            status=ApprovalStatus.GRANTED,
            approver="supervisor@example.com",
            comment="Approved for production",
        )
        
        data = payload.to_dict()
        
        self.assertEqual(data["requestId"], "req-123")
        self.assertEqual(data["status"], "granted")
        self.assertEqual(data["approver"], "supervisor@example.com")
        self.assertEqual(data["comment"], "Approved for production")


class TestEventPayload(unittest.TestCase):
    """Test event payload serialization."""
    
    def test_event_payload_to_dict(self):
        payload = EventPayload(
            event_id="evt-123",
            event_type="build.started",
            data={"workflow_id": "wf-1", "profile": "release"},
        )
        
        data = payload.to_dict()
        
        self.assertEqual(data["eventId"], "evt-123")
        self.assertEqual(data["eventType"], "build.started")
        self.assertEqual(data["data"], {"workflow_id": "wf-1", "profile": "release"})


class TestEvidencePayload(unittest.TestCase):
    """Test evidence payload serialization."""
    
    def test_evidence_payload_to_dict(self):
        payload = EvidencePayload(
            evidence_id="evd-123",
            workflow_id="wf-1",
            profile="release",
            status="passed",
            artifact_sha256=secrets.token_hex(32),
            summary="All tests passed",
            duration_ms=1234,
            stdout="Test output",
            stderr="",
        )
        
        data = payload.to_dict()
        
        self.assertEqual(data["evidenceId"], "evd-123")
        self.assertEqual(data["workflowId"], "wf-1")
        self.assertEqual(data["profile"], "release")
        self.assertEqual(data["status"], "passed")
        self.assertEqual(data["summary"], "All tests passed")
        self.assertEqual(data["durationMs"], 1234)


class TestArtifactHandoffPayload(unittest.TestCase):
    """Test artifact handoff payload serialization."""
    
    def test_artifact_handoff_to_dict(self):
        payload = ArtifactHandoffPayload(
            handoff_id="hof-123",
            artifact_path="/build/output.jar",
            artifact_sha256=secrets.token_hex(32),
            artifact_size=123456,
            workflow_id="wf-1",
            profile="release",
            destination="storage",
            metadata={"build_number": "42"},
        )
        
        data = payload.to_dict()
        
        self.assertEqual(data["handoffId"], "hof-123")
        self.assertEqual(data["artifactPath"], "/build/output.jar")
        self.assertEqual(data["artifactSize"], 123456)
        self.assertEqual(data["destination"], "storage")


class TestAuthentication(unittest.TestCase):
    """Test HMAC-SHA256 authentication."""
    
    def test_compute_signature(self):
        token = secrets.token_hex(32)
        signature = compute_signature(
            token,
            "GET",
            "/aegis/bridge/v1/status",
            "2026-09-22T00:00:00Z",
            "nonce123",
        )
        
        self.assertEqual(len(signature), 64)  # SHA-256 hex
        self.assertTrue(all(c in "0123456789abcdef" for c in signature))
    
    def test_verify_signature_valid(self):
        token = secrets.token_hex(32)
        signature = compute_signature(
            token,
            "GET",
            "/aegis/bridge/v1/status",
            "2026-09-22T00:00:00Z",
            "nonce123",
        )
        
        self.assertTrue(verify_signature(
            token,
            "GET",
            "/aegis/bridge/v1/status",
            "2026-09-22T00:00:00Z",
            "nonce123",
            signature,
        ))
    
    def test_verify_signature_invalid(self):
        token = secrets.token_hex(32)
        wrong_signature = "invalid" * 8
        
        self.assertFalse(verify_signature(
            token,
            "GET",
            "/aegis/bridge/v1/status",
            "2026-09-22T00:00:00Z",
            "nonce123",
            wrong_signature,
        ))
    
    def test_verify_signature_wrong_method(self):
        token = secrets.token_hex(32)
        signature = compute_signature(
            token,
            "GET",
            "/aegis/bridge/v1/status",
            "2026-09-22T00:00:00Z",
            "nonce123",
        )
        
        # Wrong method should fail
        self.assertFalse(verify_signature(
            token,
            "POST",  # Wrong method
            "/aegis/bridge/v1/status",
            "2026-09-22T00:00:00Z",
            "nonce123",
            signature,
        ))
    
    def test_verify_signature_wrong_path(self):
        token = secrets.token_hex(32)
        signature = compute_signature(
            token,
            "GET",
            "/aegis/bridge/v1/status",
            "2026-09-22T00:00:00Z",
            "nonce123",
        )
        
        # Wrong path should fail
        self.assertFalse(verify_signature(
            token,
            "GET",
            "/aegis/bridge/v1/approval",  # Wrong path
            "2026-09-22T00:00:00Z",
            "nonce123",
            signature,
        ))


class TestBridgeEndpoints(unittest.TestCase):
    """Test bridge endpoint definitions."""
    
    def test_status_endpoint(self):
        self.assertEqual(BridgeEndpoints.STATUS_V1, "/aegis/bridge/v1/status")
    
    def test_approval_request_endpoint(self):
        self.assertEqual(BridgeEndpoints.APPROVAL_REQUEST_V1, "/aegis/bridge/v1/approval/request")
    
    def test_approval_response_endpoint(self):
        self.assertEqual(BridgeEndpoints.APPROVAL_RESPONSE_V1, "/aegis/bridge/v1/approval/response")
    
    def test_event_endpoint(self):
        self.assertEqual(BridgeEndpoints.EVENT_V1, "/aegis/bridge/v1/event")
    
    def test_evidence_endpoint(self):
        self.assertEqual(BridgeEndpoints.EVIDENCE_V1, "/aegis/bridge/v1/evidence")
    
    def test_artifact_handoff_endpoint(self):
        self.assertEqual(BridgeEndpoints.ARTIFACT_HANDOFF_V1, "/aegis/bridge/v1/artifact/handoff")


class TestActivityStatus(unittest.TestCase):
    """Test activity status enum."""
    
    def test_activity_status_values(self):
        self.assertEqual(ActivityStatus.IDLE.value, "idle")
        self.assertEqual(ActivityStatus.EDITING.value, "editing")
        self.assertEqual(ActivityStatus.BUILDING.value, "building")
        self.assertEqual(ActivityStatus.TESTING.value, "testing")
        self.assertEqual(ActivityStatus.DEBUGGING.value, "debugging")
        self.assertEqual(ActivityStatus.SEARCHING.value, "searching")
        self.assertEqual(ActivityStatus.COMPILING.value, "compiling")


class TestApprovalStatus(unittest.TestCase):
    """Test approval status enum."""
    
    def test_approval_status_values(self):
        self.assertEqual(ApprovalStatus.PENDING.value, "pending")
        self.assertEqual(ApprovalStatus.GRANTED.value, "granted")
        self.assertEqual(ApprovalStatus.DENIED.value, "denied")
        self.assertEqual(ApprovalStatus.EXPIRED.value, "expired")


if __name__ == "__main__":
    unittest.main()
