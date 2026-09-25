"""
Aegis-9 Authenticated Local Bridge Protocol

Version: 1.0.0
Purpose: Secure, authenticated communication between Aegis and IDE/Developer Studio

Threat Model:
- Local-only communication (127.0.0.1)
- HMAC-SHA256 authentication with shared secret
- Timestamp + nonce replay protection
- Fail-closed security model
- Read-only status queries by default
- Approval-required for write operations

Protocol Design Principles:
1. Versioned endpoints for backward compatibility
2. Signed requests with timestamp/nonce replay protection
3. Minimal privilege access (read-only unless explicitly approved)
4. Structured JSON envelope with protocol metadata
5. Fail-closed on authentication/authorization failures
"""

import hashlib
import hmac
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class BridgeVersion(str, Enum):
    """Bridge protocol versions."""
    V1_0_0 = "1.0.0"


class BridgeSource(str, Enum):
    """Bridge endpoint sources."""
    AEGIS_DEVELOPER_STUDIO = "aegis-developer-studio"
    AEGIS_WORKSTATION = "aegis-workstation"


class MessageType(str, Enum):
    """Message types in the bridge protocol."""
    STATUS = "status"
    APPROVAL_REQUEST = "approval_request"
    APPROVAL_RESPONSE = "approval_response"
    EVENT = "event"
    EVIDENCE = "evidence"
    ARTIFACT_HANDOFF = "artifact_handoff"
    
    # Workflow revision exchange (write-capable)
    WORKFLOW_REVISION_OPEN_REQUEST = "workflow_revision_open_request"
    WORKFLOW_REVISION_OPEN_RESPONSE = "workflow_revision_open_response"
    BUILD_TEST_RESULT = "build_test_result"
    WORKFLOW_REVISION_COMPLETE = "workflow_revision_complete"


class ApprovalStatus(str, Enum):
    """Approval request statuses."""
    PENDING = "pending"
    GRANTED = "granted"
    DENIED = "denied"
    EXPIRED = "expired"


class ActivityStatus(str, Enum):
    """IDE activity statuses."""
    IDLE = "idle"
    EDITING = "editing"
    BUILDING = "building"
    TESTING = "testing"
    DEBUGGING = "debugging"
    SEARCHING = "searching"
    COMPILING = "compiling"


@dataclass
class BridgeEnvelope:
    """
    Standard envelope for all bridge messages.
    
    Provides protocol versioning, source identification, and message type.
    """
    protocol_version: str
    source: BridgeSource
    message_type: MessageType
    timestamp: str
    nonce: str
    payload: dict[str, Any]
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "protocolVersion": self.protocol_version,
            "source": self.source.value,
            "type": self.message_type.value,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
            "payload": self.payload,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BridgeEnvelope":
        return cls(
            protocol_version=data["protocolVersion"],
            source=BridgeSource(data["source"]),
            message_type=MessageType(data["type"]),
            timestamp=data["timestamp"],
            nonce=data["nonce"],
            payload=data["payload"],
        )


@dataclass
class StatusPayload:
    """
    Status payload for read-only status queries.
    
    Provides version, session, repository, endpoint/model, and activity information.
    """
    product_version: str
    session_id: str
    repository_paths: list[str]
    provider: str
    model: str
    activity: ActivityStatus
    endpoint_url: str = "http://127.0.0.1:3000"
    is_local_only: bool = True
    connected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "productVersion": self.product_version,
            "sessionId": self.session_id,
            "repositoryPaths": self.repository_paths,
            "provider": self.provider,
            "model": self.model,
            "activity": self.activity.value,
            "endpointUrl": self.endpoint_url,
            "isLocalOnly": self.is_local_only,
            "connectedAt": self.connected_at,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StatusPayload":
        return cls(
            product_version=data["productVersion"],
            session_id=data["sessionId"],
            repository_paths=data.get("repositoryPaths", []),
            provider=data.get("provider", ""),
            model=data.get("model", ""),
            activity=ActivityStatus(data["activity"]),
            endpoint_url=data.get("endpointUrl", "http://127.0.0.1:3000"),
            is_local_only=data.get("isLocalOnly", True),
            connected_at=data.get("connectedAt", datetime.now(timezone.utc).isoformat()),
        )


@dataclass
class ApprovalRequestPayload:
    """
    Approval request for operations requiring user/supervisor approval.
    
    Used for file operations, build triggers, and other privileged actions.
    """
    request_id: str
    operation: str
    description: str
    target_path: Optional[str] = None
    requires_supervisor: bool = False
    timeout_seconds: int = 300
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "requestId": self.request_id,
            "operation": self.operation,
            "description": self.description,
            "targetPath": self.target_path,
            "requiresSupervisor": self.requires_supervisor,
            "timeoutSeconds": self.timeout_seconds,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ApprovalRequestPayload":
        return cls(
            request_id=data["requestId"],
            operation=data["operation"],
            description=data["description"],
            target_path=data.get("targetPath"),
            requires_supervisor=data.get("requiresSupervisor", False),
            timeout_seconds=data.get("timeoutSeconds", 300),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ApprovalResponsePayload:
    """
    Response to an approval request.
    """
    request_id: str
    status: ApprovalStatus
    approver: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    comment: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "requestId": self.request_id,
            "status": self.status.value,
            "approver": self.approver,
            "timestamp": self.timestamp,
            "comment": self.comment,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ApprovalResponsePayload":
        return cls(
            request_id=data["requestId"],
            status=ApprovalStatus(data["status"]),
            approver=data["approver"],
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            comment=data.get("comment"),
        )


@dataclass
class EventPayload:
    """
    Event message for IDE activity notifications.
    """
    event_id: str
    event_type: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    data: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "eventId": self.event_id,
            "eventType": self.event_type,
            "timestamp": self.timestamp,
            "data": self.data,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EventPayload":
        return cls(
            event_id=data["eventId"],
            event_type=data["eventType"],
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            data=data.get("data", {}),
        )


@dataclass
class EvidencePayload:
    """
    Build/test evidence for workflow artifact handoff.
    """
    evidence_id: str
    workflow_id: str
    profile: str
    status: str
    artifact_sha256: str
    summary: str
    duration_ms: int
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "evidenceId": self.evidence_id,
            "workflowId": self.workflow_id,
            "profile": self.profile,
            "status": self.status,
            "artifactSha256": self.artifact_sha256,
            "summary": self.summary,
            "durationMs": self.duration_ms,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "timestamp": self.timestamp,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidencePayload":
        return cls(
            evidence_id=data["evidenceId"],
            workflow_id=data["workflowId"],
            profile=data["profile"],
            status=data["status"],
            artifact_sha256=data["artifactSha256"],
            summary=data["summary"],
            duration_ms=data["durationMs"],
            stdout=data.get("stdout"),
            stderr=data.get("stderr"),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
        )


@dataclass
class ArtifactHandoffPayload:
    """
    Artifact handoff for build/test outputs.
    """
    handoff_id: str
    artifact_path: str
    artifact_sha256: str
    artifact_size: int
    workflow_id: str
    profile: str
    destination: str
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "handoffId": self.handoff_id,
            "artifactPath": self.artifact_path,
            "artifactSha256": self.artifact_sha256,
            "artifactSize": self.artifact_size,
            "workflowId": self.workflow_id,
            "profile": self.profile,
            "destination": self.destination,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ArtifactHandoffPayload":
        return cls(
            handoff_id=data["handoffId"],
            artifact_path=data["artifactPath"],
            artifact_sha256=data["artifactSha256"],
            artifact_size=data["artifactSize"],
            workflow_id=data["workflowId"],
            profile=data["profile"],
            destination=data["destination"],
            metadata=data.get("metadata", {}),
        )


@dataclass
class WorkflowRevisionOpenRequest:
    """
    Request to open a workflow revision in Developer Studio.
    
    Used by Aegis to request IDE to open a specific workflow revision
    for review, repair, build, and testing.
    """
    request_id: str
    workflow_id: str
    revision_id: str
    revision_hash: str
    description: str
    required_actions: list[str] = field(default_factory=list)
    attached_files: list[str] = field(default_factory=list)
    timeout_seconds: int = 3600
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "requestId": self.request_id,
            "workflowId": self.workflow_id,
            "revisionId": self.revision_id,
            "revisionHash": self.revision_hash,
            "description": self.description,
            "requiredActions": self.required_actions,
            "attachedFiles": self.attached_files,
            "timeoutSeconds": self.timeout_seconds,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkflowRevisionOpenRequest":
        return cls(
            request_id=data["requestId"],
            workflow_id=data["workflowId"],
            revision_id=data["revisionId"],
            revision_hash=data["revisionHash"],
            description=data["description"],
            required_actions=data.get("requiredActions", []),
            attached_files=data.get("attachedFiles", []),
            timeout_seconds=data.get("timeoutSeconds", 3600),
        )


@dataclass
class WorkflowRevisionOpenResponse:
    """
    Response to workflow revision open request.
    
    Confirms the revision was opened and provides initial status.
    """
    request_id: str
    status: str
    ide_session_id: str
    opened_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "requestId": self.request_id,
            "status": self.status,
            "ideSessionId": self.ide_session_id,
            "openedAt": self.opened_at,
            "error": self.error,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkflowRevisionOpenResponse":
        return cls(
            request_id=data["requestId"],
            status=data["status"],
            ide_session_id=data["ideSessionId"],
            opened_at=data.get("openedAt", datetime.now(timezone.utc).isoformat()),
            error=data.get("error"),
        )


@dataclass
class BuildTestResult:
    """
    Build or test result from Developer Studio.
    
    Submitted as evidence for workflow revision validation.
    """
    result_id: str
    workflow_id: str
    revision_id: str
    result_type: str  # "build" or "test"
    profile: str
    status: str  # "passed", "failed", "error"
    duration_ms: int
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    artifacts: list[dict[str, str]] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "resultId": self.result_id,
            "workflowId": self.workflow_id,
            "revisionId": self.revision_id,
            "resultType": self.result_type,
            "profile": self.profile,
            "status": self.status,
            "durationMs": self.duration_ms,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "artifacts": self.artifacts,
            "timestamp": self.timestamp,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BuildTestResult":
        return cls(
            result_id=data["resultId"],
            workflow_id=data["workflowId"],
            revision_id=data["revisionId"],
            result_type=data["resultType"],
            profile=data["profile"],
            status=data["status"],
            duration_ms=data["durationMs"],
            stdout=data.get("stdout"),
            stderr=data.get("stderr"),
            artifacts=data.get("artifacts", []),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
        )


@dataclass
class WorkflowRevisionComplete:
    """
    Final completion notification for workflow revision.
    
    Submitted when review, build, test, and repair are complete.
    Includes final hash verification and approval recommendation.
    """
    request_id: str
    workflow_id: str
    revision_id: str
    final_hash: str
    hash_verified: bool
    build_results: list[BuildTestResult] = field(default_factory=list)
    test_results: list[BuildTestResult] = field(default_factory=list)
    repair_history: list[dict[str, Any]] = field(default_factory=list)
    recommendation: str = "approve"  # "approve", "reject", "needs_revision"
    comment: Optional[str] = None
    completed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "requestId": self.request_id,
            "workflowId": self.workflow_id,
            "revisionId": self.revision_id,
            "finalHash": self.final_hash,
            "hashVerified": self.hash_verified,
            "buildResults": [r.to_dict() for r in self.build_results],
            "testResults": [r.to_dict() for r in self.test_results],
            "repairHistory": self.repair_history,
            "recommendation": self.recommendation,
            "comment": self.comment,
            "completedAt": self.completed_at,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkflowRevisionComplete":
        return cls(
            request_id=data["requestId"],
            workflow_id=data["workflowId"],
            revision_id=data["revisionId"],
            final_hash=data["finalHash"],
            hash_verified=data["hashVerified"],
            build_results=[BuildTestResult.from_dict(r) for r in data.get("buildResults", [])],
            test_results=[BuildTestResult.from_dict(r) for r in data.get("testResults", [])],
            repair_history=data.get("repairHistory", []),
            recommendation=data.get("recommendation", "approve"),
            comment=data.get("comment"),
            completed_at=data.get("completedAt", datetime.now(timezone.utc).isoformat()),
        )


# Endpoint definitions
class BridgeEndpoints:
    """Bridge API endpoint definitions."""
    
    # Status endpoints (read-only)
    STATUS_V1 = "/aegis/bridge/v1/status"
    
    # Approval endpoints
    APPROVAL_REQUEST_V1 = "/aegis/bridge/v1/approval/request"
    APPROVAL_RESPONSE_V1 = "/aegis/bridge/v1/approval/response"
    
    # Event endpoints
    EVENT_V1 = "/aegis/bridge/v1/event"
    
    # Evidence endpoints
    EVIDENCE_V1 = "/aegis/bridge/v1/evidence"
    
    # Artifact handoff endpoints
    ARTIFACT_HANDOFF_V1 = "/aegis/bridge/v1/artifact/handoff"
    
    # Workflow revision exchange endpoints (write-capable)
    WORKFLOW_REVISION_OPEN_REQUEST_V1 = "/aegis/bridge/v1/workflow/revision/open/request"
    WORKFLOW_REVISION_OPEN_RESPONSE_V1 = "/aegis/bridge/v1/workflow/revision/open/response"
    BUILD_TEST_RESULT_V1 = "/aegis/bridge/v1/workflow/revision/build-test-result"
    WORKFLOW_REVISION_COMPLETE_V1 = "/aegis/bridge/v1/workflow/revision/complete"


# Authentication helpers
def compute_signature(token: str, method: str, path: str, timestamp: str, nonce: str) -> str:
    """
    Compute HMAC-SHA256 signature for request authentication.
    
    Canonical format: "METHOD\nPATH\nTIMESTAMP\nNONCE"
    """
    canonical = f"{method}\n{path}\n{timestamp}\n{nonce}".encode()
    return hmac.new(token.encode(), canonical, hashlib.sha256).hexdigest()


def verify_signature(token: str, method: str, path: str, timestamp: str, nonce: str, signature: str) -> bool:
    """Verify HMAC-SHA256 signature for request authentication."""
    expected = compute_signature(token, method, path, timestamp, nonce)
    return hmac.compare_digest(expected, signature)
