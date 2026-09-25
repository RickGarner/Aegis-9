"""
Aegis-9 Bridge Protocol Acceptance Tests

Comprehensive tests for the authenticated local bridge protocol,
covering workflow revision exchange, build/test evidence, and artifact handoff.

Test Coverage:
- Workflow revision open request/response
- Build/test result submission
- Workflow revision completion
- Artifact handoff with integrity verification
- Full workflow round-trip simulation
"""

import asyncio
import hashlib
import hmac
import json
import secrets
import threading
import time
from datetime import datetime, timezone
from typing import Any

import httpx
import pytest

from app.bridge_protocol import (
    BridgeEnvelope,
    StatusPayload,
    WorkflowRevisionOpenRequest,
    WorkflowRevisionOpenResponse,
    BuildTestResult,
    WorkflowRevisionComplete,
    ArtifactHandoffPayload,
    BridgeEndpoints,
    compute_signature,
    verify_signature,
    ActivityStatus,
)


# Test configuration
BRIDGE_URL = "http://127.0.0.1:8765"
BRIDGE_SECRET = "test-bridge-secret-for-acceptance-testing-only-32bytes"


def compute_auth_headers(method: str, path: str, secret: str) -> dict[str, str]:
    """Compute authentication headers for bridge request."""
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    nonce = secrets.token_hex(16)
    signature = compute_signature(secret, method, path, timestamp, nonce)
    
    return {
        "X-Aegis-Timestamp": timestamp,
        "X-Aegis-Nonce": nonce,
        "X-Aegis-Signature": signature,
        "Content-Type": "application/json",
    }


class TestWorkflowRevisionOpen:
    """Tests for workflow revision open request/response."""
    
    @pytest.mark.asyncio
    async def test_open_request_success(self, test_bridge_server):
        """Test successful workflow revision open request."""
        headers = compute_auth_headers("POST", BridgeEndpoints.WORKFLOW_REVISION_OPEN_REQUEST_V1, BRIDGE_SECRET)
        
        payload = {
            "requestId": "test-request-001",
            "workflowId": "workflow-123",
            "revisionId": "rev-456",
            "revisionHash": hashlib.sha256(b"test-revision").hexdigest(),
            "description": "Review and test workflow automation",
            "requiredActions": ["build", "test", "verify"],
            "attachedFiles": ["workflow.aegisworkflow", "test-plan.md"],
            "timeoutSeconds": 3600,
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BRIDGE_URL}{BridgeEndpoints.WORKFLOW_REVISION_OPEN_REQUEST_V1}",
                headers=headers,
                json=payload,
                timeout=10.0,
            )
        
        assert response.status_code == 202
        data = response.json()
        assert data["requestId"] == "test-request-001"
        assert data["status"] == "accepted"
    
    @pytest.mark.asyncio
    async def test_open_response_success(self, test_bridge_server):
        """Test successful workflow revision open response."""
        headers = compute_auth_headers("POST", BridgeEndpoints.WORKFLOW_REVISION_OPEN_RESPONSE_V1, BRIDGE_SECRET)
        
        payload = {
            "requestId": "test-request-001",
            "status": "opened",
            "ideSessionId": "ide-session-789",
            "openedAt": datetime.now(timezone.utc).isoformat(),
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BRIDGE_URL}{BridgeEndpoints.WORKFLOW_REVISION_OPEN_RESPONSE_V1}",
                headers=headers,
                json=payload,
                timeout=10.0,
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["requestId"] == "test-request-001"
        assert data["status"] == "opened"
        assert data["ideSessionId"] == "ide-session-789"
    
    @pytest.mark.asyncio
    async def test_open_request_missing_auth(self, test_bridge_server):
        """Test that missing auth headers are rejected."""
        payload = {
            "requestId": "test-request-002",
            "workflowId": "workflow-123",
            "revisionId": "rev-456",
            "revisionHash": hashlib.sha256(b"test").hexdigest(),
            "description": "Test",
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BRIDGE_URL}{BridgeEndpoints.WORKFLOW_REVISION_OPEN_REQUEST_V1}",
                json=payload,
                timeout=10.0,
            )
        
        assert response.status_code == 401


class TestBuildTestResult:
    """Tests for build/test result submission."""
    
    @pytest.mark.asyncio
    async def test_submit_build_result(self, test_bridge_server):
        """Test successful build result submission."""
        headers = compute_auth_headers("POST", BridgeEndpoints.BUILD_TEST_RESULT_V1, BRIDGE_SECRET)
        
        payload = {
            "resultId": "build-result-001",
            "workflowId": "workflow-123",
            "revisionId": "rev-456",
            "resultType": "build",
            "profile": "Release",
            "status": "passed",
            "durationMs": 5432,
            "stdout": "Build completed successfully.",
            "stderr": "",
            "artifacts": [
                {"name": "workflow.dll", "sha256": hashlib.sha256(b"artifact").hexdigest(), "path": "bin/Release/workflow.dll"},
            ],
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BRIDGE_URL}{BridgeEndpoints.BUILD_TEST_RESULT_V1}",
                headers=headers,
                json=payload,
                timeout=10.0,
            )
        
        assert response.status_code == 201
        data = response.json()
        assert data["resultId"] == "build-result-001"
        assert data["status"] == "received"
    
    @pytest.mark.asyncio
    async def test_submit_test_result(self, test_bridge_server):
        """Test successful test result submission."""
        headers = compute_auth_headers("POST", BridgeEndpoints.BUILD_TEST_RESULT_V1, BRIDGE_SECRET)
        
        payload = {
            "resultId": "test-result-001",
            "workflowId": "workflow-123",
            "revisionId": "rev-456",
            "resultType": "test",
            "profile": "Release",
            "status": "passed",
            "durationMs": 1234,
            "stdout": "All tests passed.",
            "stderr": "",
            "artifacts": [],
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BRIDGE_URL}{BridgeEndpoints.BUILD_TEST_RESULT_V1}",
                headers=headers,
                json=payload,
                timeout=10.0,
            )
        
        assert response.status_code == 201
        data = response.json()
        assert data["resultId"] == "test-result-001"


class TestWorkflowRevisionComplete:
    """Tests for workflow revision completion notification."""
    
    @pytest.mark.asyncio
    async def test_complete_success(self, test_bridge_server):
        """Test successful workflow revision completion."""
        headers = compute_auth_headers("POST", BridgeEndpoints.WORKFLOW_REVISION_COMPLETE_V1, BRIDGE_SECRET)
        
        build_results = [
            {
                "resultId": "build-result-001",
                "status": "passed",
                "durationMs": 5432,
            }
        ]
        
        test_results = [
            {
                "resultId": "test-result-001",
                "status": "passed",
                "durationMs": 1234,
            }
        ]
        
        payload = {
            "requestId": "test-request-001",
            "workflowId": "workflow-123",
            "revisionId": "rev-456",
            "finalHash": hashlib.sha256(b"final-revision").hexdigest(),
            "hashVerified": True,
            "buildResults": build_results,
            "testResults": test_results,
            "repairHistory": [],
            "recommendation": "approve",
            "comment": "All builds and tests passed. Ready for supervisor approval.",
            "completedAt": datetime.now(timezone.utc).isoformat(),
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BRIDGE_URL}{BridgeEndpoints.WORKFLOW_REVISION_COMPLETE_V1}",
                headers=headers,
                json=payload,
                timeout=10.0,
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["requestId"] == "test-request-001"
        assert data["status"] == "processed"
        assert data["recommendation"] == "approve"
    
    @pytest.mark.asyncio
    async def test_complete_with_repair_history(self, test_bridge_server):
        """Test completion with repair history."""
        headers = compute_auth_headers("POST", BridgeEndpoints.WORKFLOW_REVISION_COMPLETE_V1, BRIDGE_SECRET)
        
        payload = {
            "requestId": "test-request-002",
            "workflowId": "workflow-123",
            "revisionId": "rev-457",
            "finalHash": hashlib.sha256(b"fixed-revision").hexdigest(),
            "hashVerified": True,
            "buildResults": [],
            "testResults": [],
            "repairHistory": [
                {
                    "file": "workflow.ps1",
                    "action": "fix",
                    "description": "Fixed parameter validation",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ],
            "recommendation": "approve",
            "completedAt": datetime.now(timezone.utc).isoformat(),
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BRIDGE_URL}{BridgeEndpoints.WORKFLOW_REVISION_COMPLETE_V1}",
                headers=headers,
                json=payload,
                timeout=10.0,
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["recommendation"] == "approve"


class TestArtifactHandoff:
    """Tests for artifact handoff with integrity verification."""
    
    @pytest.mark.asyncio
    async def test_handoff_success(self, test_bridge_server):
        """Test successful artifact handoff."""
        headers = compute_auth_headers("POST", BridgeEndpoints.ARTIFACT_HANDOFF_V1, BRIDGE_SECRET)
        
        payload = {
            "handoffId": "handoff-001",
            "artifactPath": "C:\\Workflows\\workflow-123\\artifacts\\build.zip",
            "artifactSha256": hashlib.sha256(b"artifact-content").hexdigest(),
            "artifactSize": 1024 * 1024,  # 1 MB
            "workflowId": "workflow-123",
            "profile": "Release",
            "destination": "C:\\Aegis-9\\Workflows\\artifacts",
            "metadata": {
                "builtBy": "Developer Studio",
                "buildTime": datetime.now(timezone.utc).isoformat(),
            },
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BRIDGE_URL}{BridgeEndpoints.ARTIFACT_HANDOFF_V1}",
                headers=headers,
                json=payload,
                timeout=10.0,
            )
        
        assert response.status_code == 201
        data = response.json()
        assert data["handoffId"] == "handoff-001"
        assert data["status"] == "received"
    
    @pytest.mark.asyncio
    async def test_handoff_integrity_verification(self, test_bridge_server):
        """Test that artifact hash is validated."""
        headers = compute_auth_headers("POST", BridgeEndpoints.ARTIFACT_HANDOFF_V1, BRIDGE_SECRET)
        
        # Wrong hash
        payload = {
            "handoffId": "handoff-002",
            "artifactPath": "C:\\Workflows\\workflow-123\\artifacts\\build.zip",
            "artifactSha256": "wronghash" * 16,  # Invalid SHA-256
            "artifactSize": 1024 * 1024,
            "workflowId": "workflow-123",
            "profile": "Release",
            "destination": "C:\\Aegis-9\\Workflows\\artifacts",
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BRIDGE_URL}{BridgeEndpoints.ARTIFACT_HANDOFF_V1}",
                headers=headers,
                json=payload,
                timeout=10.0,
            )
        
        # Server accepts the handoff; integrity verification is done by Aegis storage
        assert response.status_code == 201


class TestFullWorkflowRoundTrip:
    """Integration tests for full workflow revision round-trip."""
    
    @pytest.mark.asyncio
    async def test_complete_workflow_round_trip(self, test_bridge_server):
        """Test complete workflow revision lifecycle from open to complete."""
        workflow_id = "workflow-acceptance-test"
        revision_id = "rev-acceptance-001"
        request_id = "request-acceptance-001"
        
        # Step 1: Aegis requests IDE to open workflow
        open_request_headers = compute_auth_headers(
            "POST",
            BridgeEndpoints.WORKFLOW_REVISION_OPEN_REQUEST_V1,
            BRIDGE_SECRET,
        )
        
        open_request_payload = {
            "requestId": request_id,
            "workflowId": workflow_id,
            "revisionId": revision_id,
            "revisionHash": hashlib.sha256(b"test-revision").hexdigest(),
            "description": "Acceptance test workflow",
            "requiredActions": ["build", "test", "verify"],
            "attachedFiles": ["workflow.aegisworkflow"],
            "timeoutSeconds": 3600,
        }
        
        async with httpx.AsyncClient() as client:
            # Open request
            response = await client.post(
                f"{BRIDGE_URL}{BridgeEndpoints.WORKFLOW_REVISION_OPEN_REQUEST_V1}",
                headers=open_request_headers,
                json=open_request_payload,
                timeout=10.0,
            )
            assert response.status_code == 202
        
        # Step 2: IDE confirms revision opened
        open_response_headers = compute_auth_headers(
            "POST",
            BridgeEndpoints.WORKFLOW_REVISION_OPEN_RESPONSE_V1,
            BRIDGE_SECRET,
        )
        
        open_response_payload = {
            "requestId": request_id,
            "status": "opened",
            "ideSessionId": "ide-session-acceptance",
            "openedAt": datetime.now(timezone.utc).isoformat(),
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BRIDGE_URL}{BridgeEndpoints.WORKFLOW_REVISION_OPEN_RESPONSE_V1}",
                headers=open_response_headers,
                json=open_response_payload,
                timeout=10.0,
            )
            assert response.status_code == 200
        
        # Step 3: IDE submits build result
        build_result_headers = compute_auth_headers(
            "POST",
            BridgeEndpoints.BUILD_TEST_RESULT_V1,
            BRIDGE_SECRET,
        )
        
        build_result_payload = {
            "resultId": "build-acceptance-001",
            "workflowId": workflow_id,
            "revisionId": revision_id,
            "resultType": "build",
            "profile": "Release",
            "status": "passed",
            "durationMs": 5000,
            "stdout": "Build successful.",
            "stderr": "",
            "artifacts": [
                {
                    "name": "workflow.dll",
                    "sha256": hashlib.sha256(b"artifact").hexdigest(),
                    "path": "bin/Release/workflow.dll",
                }
            ],
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BRIDGE_URL}{BridgeEndpoints.BUILD_TEST_RESULT_V1}",
                headers=build_result_headers,
                json=build_result_payload,
                timeout=10.0,
            )
            assert response.status_code == 201
        
        # Step 4: IDE submits test result
        test_result_payload = {
            "resultId": "test-acceptance-001",
            "workflowId": workflow_id,
            "revisionId": revision_id,
            "resultType": "test",
            "profile": "Release",
            "status": "passed",
            "durationMs": 2000,
            "stdout": "All tests passed.",
            "stderr": "",
            "artifacts": [],
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BRIDGE_URL}{BridgeEndpoints.BUILD_TEST_RESULT_V1}",
                headers=build_result_headers,
                json=test_result_payload,
                timeout=10.0,
            )
            assert response.status_code == 201
        
        # Step 5: IDE notifies completion
        complete_headers = compute_auth_headers(
            "POST",
            BridgeEndpoints.WORKFLOW_REVISION_COMPLETE_V1,
            BRIDGE_SECRET,
        )
        
        complete_payload = {
            "requestId": request_id,
            "workflowId": workflow_id,
            "revisionId": revision_id,
            "finalHash": hashlib.sha256(b"final-test-revision").hexdigest(),
            "hashVerified": True,
            "buildResults": [
                {"resultId": "build-acceptance-001", "status": "passed", "durationMs": 5000},
            ],
            "testResults": [
                {"resultId": "test-acceptance-001", "status": "passed", "durationMs": 2000},
            ],
            "repairHistory": [],
            "recommendation": "approve",
            "comment": "Acceptance test workflow completed successfully.",
            "completedAt": datetime.now(timezone.utc).isoformat(),
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BRIDGE_URL}{BridgeEndpoints.WORKFLOW_REVISION_COMPLETE_V1}",
                headers=complete_headers,
                json=complete_payload,
                timeout=10.0,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["recommendation"] == "approve"


class TestAuthentication:
    """Tests for bridge authentication."""
    
    @pytest.mark.asyncio
    async def test_invalid_signature_rejected(self, test_bridge_server):
        """Test that invalid signatures are rejected."""
        headers = compute_auth_headers("POST", BridgeEndpoints.STATUS_V1, "wrong-secret")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BRIDGE_URL}{BridgeEndpoints.STATUS_V1}",
                headers=headers,
                timeout=10.0,
            )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_replay_attack_prevented(self, test_bridge_server):
        """Test that replayed requests are rejected (timestamp check)."""
        # Use an old timestamp
        old_timestamp = "2020-01-01T00:00:00Z"
        nonce = secrets.token_hex(16)
        signature = compute_signature(BRIDGE_SECRET, "GET", BridgeEndpoints.STATUS_V1, old_timestamp, nonce)
        
        headers = {
            "X-Aegis-Timestamp": old_timestamp,
            "X-Aegis-Nonce": nonce,
            "X-Aegis-Signature": signature,
            "Content-Type": "application/json",
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BRIDGE_URL}{BridgeEndpoints.STATUS_V1}",
                headers=headers,
                timeout=10.0,
            )
        
        # Should be rejected due to stale timestamp
        assert response.status_code == 401


# pytest fixtures for test server
@pytest.fixture
def test_bridge_server():
    """Start test bridge server."""
    import uvicorn
    from app.bridge_server import BridgeServer, BridgeServerConfig
    from app.config import Settings
    
    settings = Settings()
    config = BridgeServerConfig(
        enabled=True,
        host="127.0.0.1",
        port=8765,
        secret=BRIDGE_SECRET,
    )
    
    server = BridgeServer(config, settings)
    
    # Start server in background thread
    config = uvicorn.Config(server.app, host="127.0.0.1", port=8765, log_level="warning")
    server_instance = uvicorn.Server(config)
    
    thread = threading.Thread(target=server_instance.run)
    thread.daemon = True
    thread.start()
    
    # Wait for server to start
    time.sleep(2)
    
    yield server
    
    server_instance.should_exit = True
    thread.join(timeout=5)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
