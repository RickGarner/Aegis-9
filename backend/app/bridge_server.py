"""
Aegis-9 Local Bridge Server

Provides authenticated endpoints for IDE/Developer Studio to communicate with Aegis.
Runs on localhost only (127.0.0.1) for security.

Endpoints:
- GET  /aegis/bridge/v1/status       - Read-only status query
- POST /aegis/bridge/v1/approval/request - Request approval for operations
- POST /aegis/bridge/v1/approval/response - Respond to approval requests
- POST /aegis/bridge/v1/event        - Send activity events
- POST /aegis/bridge/v1/evidence     - Submit build/test evidence
- POST /aegis/bridge/v1/artifact/handoff - Handoff build artifacts
"""

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Security, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.bridge_protocol import (
    BridgeEnvelope,
    StatusPayload,
    ApprovalRequestPayload,
    ApprovalResponsePayload,
    ApprovalStatus,
    EventPayload,
    EvidencePayload,
    ArtifactHandoffPayload,
    WorkflowRevisionOpenRequest,
    WorkflowRevisionOpenResponse,
    BuildTestResult,
    WorkflowRevisionComplete,
    BridgeEndpoints,
    compute_signature,
    verify_signature,
)
from app.config import Settings, get_settings


# Security configuration
security = HTTPBearer(auto_error=False)
BRIDGE_SECRET_ENV = "AEGIS_BRIDGE_SECRET"


class BridgeServerConfig(BaseModel):
    """Bridge server configuration."""
    enabled: bool = True
    host: str = "127.0.0.1"
    port: int = 8765
    secret: str = Field(default="", min_length=32)
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://127.0.0.1"])
    request_timeout_seconds: int = 30
    approval_timeout_seconds: int = 300


class ApprovalRequestStore:
    """In-memory store for approval requests."""
    
    def __init__(self):
        self._requests: dict[str, ApprovalRequestPayload] = {}
        self._responses: dict[str, ApprovalResponsePayload] = {}
    
    def add_request(self, request: ApprovalRequestPayload) -> None:
        self._requests[request.request_id] = request
    
    def get_request(self, request_id: str) -> ApprovalRequestPayload | None:
        return self._requests.get(request_id)
    
    def add_response(self, response: ApprovalResponsePayload) -> None:
        self._responses[response.request_id] = response
    
    def get_response(self, request_id: str) -> ApprovalResponsePayload | None:
        return self._responses.get(request_id)
    
    def cleanup_expired(self) -> int:
        """Remove expired requests and responses."""
        now = datetime.now(timezone.utc)
        expired = []
        
        for request_id, request in self._requests.items():
            expiry = datetime.fromisoformat(request.timestamp.replace("Z", "+00:00")) + \
                     timedelta(seconds=request.timeout_seconds)
            if now > expiry:
                expired.append(request_id)
        
        for request_id in expired:
            del self._requests[request_id]
            if request_id in self._responses:
                del self._responses[request_id]
        
        return len(expired)


class WorkflowRevisionStore:
    """In-memory store for workflow revision exchange."""
    
    def __init__(self):
        self._open_requests: dict[str, WorkflowRevisionOpenRequest] = {}
        self._open_responses: dict[str, WorkflowRevisionOpenResponse] = {}
        self._build_results: dict[str, list[BuildTestResult]] = {}
        self._test_results: dict[str, list[BuildTestResult]] = {}
        self._completions: dict[str, WorkflowRevisionComplete] = {}
    
    def add_open_request(self, request: WorkflowRevisionOpenRequest) -> None:
        self._open_requests[request.request_id] = request
    
    def get_open_request(self, request_id: str) -> WorkflowRevisionOpenRequest | None:
        return self._open_requests.get(request_id)
    
    def add_open_response(self, response: WorkflowRevisionOpenResponse) -> None:
        self._open_responses[response.request_id] = response
    
    def get_open_response(self, request_id: str) -> WorkflowRevisionOpenResponse | None:
        return self._open_responses.get(request_id)
    
    def add_build_result(self, workflow_id: str, revision_id: str, result: BuildTestResult) -> None:
        key = f"{workflow_id}:{revision_id}"
        if key not in self._build_results:
            self._build_results[key] = []
        self._build_results[key].append(result)
    
    def get_build_results(self, workflow_id: str, revision_id: str) -> list[BuildTestResult]:
        key = f"{workflow_id}:{revision_id}"
        return self._build_results.get(key, [])
    
    def add_test_result(self, workflow_id: str, revision_id: str, result: BuildTestResult) -> None:
        key = f"{workflow_id}:{revision_id}"
        if key not in self._test_results:
            self._test_results[key] = []
        self._test_results[key].append(result)
    
    def get_test_results(self, workflow_id: str, revision_id: str) -> list[BuildTestResult]:
        key = f"{workflow_id}:{revision_id}"
        return self._test_results.get(key, [])
    
    def add_completion(self, completion: WorkflowRevisionComplete) -> None:
        self._completions[completion.request_id] = completion
    
    def get_completion(self, request_id: str) -> WorkflowRevisionComplete | None:
        return self._completions.get(request_id)
    
    def cleanup_expired(self, timeout_seconds: int = 7200) -> int:
        """Remove expired open requests (2 hour default)."""
        now = datetime.now(timezone.utc)
        expired = []
        
        for request_id, request in self._open_requests.items():
            expiry = datetime.fromisoformat(request.timestamp.replace("Z", "+00:00")) + \
                     timedelta(seconds=request.timeout_seconds)
            if now > expiry:
                expired.append(request_id)
        
        for request_id in expired:
            del self._open_requests[request_id]
            if request_id in self._open_responses:
                del self._open_responses[request_id]
        
        return len(expired)


class BridgeServer:
    """
    Aegis Local Bridge Server.
    
    Manages authenticated communication between IDE and Aegis.
    """
    
    def __init__(self, config: BridgeServerConfig, settings: Settings):
        self.config = config
        self.settings = settings
        self.app = FastAPI(
            title="Aegis Local Bridge",
            version="1.0.0",
            docs_url=None,
            redoc_url=None,
            openapi_url=None,
        )
        self._approval_store = ApprovalRequestStore()
        self._workflow_store = WorkflowRevisionStore()
        self._setup_routes()
    
    def _setup_routes(self) -> None:
        """Set up FastAPI routes."""
        
        @self.app.get(
            BridgeEndpoints.STATUS_V1,
            response_model=dict,
            status_code=status.HTTP_200_OK,
            summary="Get IDE status",
            description="Read-only status query for Aegis to monitor IDE state.",
        )
        async def get_status(request: Request) -> dict[str, Any]:
            """
            Get current IDE status.
            
            Provides version, session, repository, model, and activity information.
            Requires authentication via HMAC signature.
            """
            # Extract and verify signature
            timestamp = request.headers.get("X-Aegis-Timestamp")
            nonce = request.headers.get("X-Aegis-Nonce")
            signature = request.headers.get("X-Aegis-Signature")
            
            if not all([timestamp, nonce, signature]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing authentication headers",
                )
            
            if not verify_signature(
                self.config.secret,
                "GET",
                BridgeEndpoints.STATUS_V1,
                timestamp,
                nonce,
                signature,
            ):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid signature",
                )
            
            # Check timestamp freshness (prevent replay attacks)
            try:
                request_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                if abs((now - request_time).total_seconds()) > 60:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Request timestamp expired",
                    )
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid timestamp format",
                )
            
            # Generate status payload
            # In production, this would query actual IDE state
            status_payload = StatusPayload(
                product_version="1.0.0",
                session_id=secrets.token_hex(16),
                repository_paths=[],
                provider=self.settings.model_provider or "local",
                model=self.settings.model_name or "unknown",
                activity="idle",
                endpoint_url=f"http://{self.config.host}:{self.config.port}",
                is_local_only=True,
            )
            
            envelope = BridgeEnvelope(
                protocol_version="1.0.0",
                source="aegis-developer-studio",
                message_type="status",
                timestamp=datetime.now(timezone.utc).isoformat(),
                nonce=secrets.token_hex(16),
                payload=status_payload.to_dict(),
            )
            
            return envelope.to_dict()
        
        @self.app.post(
            BridgeEndpoints.APPROVAL_REQUEST_V1,
            response_model=dict,
            status_code=status.HTTP_201_CREATED,
            summary="Request approval",
            description="Request user/supervisor approval for an operation.",
        )
        async def request_approval(
            request: Request,
            credentials: HTTPAuthorizationCredentials | None = Security(security),
        ) -> dict[str, Any]:
            """
            Request approval for an operation.
            
            Creates an approval request that must be responded to before
            the operation can proceed.
            """
            # Extract and verify signature
            timestamp = request.headers.get("X-Aegis-Timestamp")
            nonce = request.headers.get("X-Aegis-Nonce")
            signature = request.headers.get("X-Aegis-Signature")
            
            if not all([timestamp, nonce, signature]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing authentication headers",
                )
            
            if not verify_signature(
                self.config.secret,
                "POST",
                BridgeEndpoints.APPROVAL_REQUEST_V1,
                timestamp,
                nonce,
                signature,
            ):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid signature",
                )
            
            # Parse request body
            try:
                body = await request.json()
                payload = ApprovalRequestPayload.from_dict(body)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid request body: {e}",
                )
            
            # Store approval request
            self._approval_store.add_request(payload)
            
            # Return success with request ID
            response = {
                "requestId": payload.request_id,
                "status": "pending",
                "expiresAt": datetime.fromisoformat(
                    payload.timestamp.replace("Z", "+00:00")
                ) + timedelta(seconds=payload.timeout_seconds),
            }
            
            return response
        
        @self.app.post(
            BridgeEndpoints.APPROVAL_RESPONSE_V1,
            response_model=dict,
            status_code=status.HTTP_200_OK,
            summary="Respond to approval request",
            description="Respond to an approval request with granted/denied status.",
        )
        async def respond_to_approval(
            request: Request,
            credentials: HTTPAuthorizationCredentials | None = Security(security),
        ) -> dict[str, Any]:
            """
            Respond to an approval request.
            
            Must reference a valid pending approval request.
            """
            # Extract and verify signature
            timestamp = request.headers.get("X-Aegis-Timestamp")
            nonce = request.headers.get("X-Aegis-Nonce")
            signature = request.headers.get("X-Aegis-Signature")
            
            if not all([timestamp, nonce, signature]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing authentication headers",
                )
            
            if not verify_signature(
                self.config.secret,
                "POST",
                BridgeEndpoints.APPROVAL_RESPONSE_V1,
                timestamp,
                nonce,
                signature,
            ):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid signature",
                )
            
            # Parse request body
            try:
                body = await request.json()
                payload = ApprovalResponsePayload.from_dict(body)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid request body: {e}",
                )
            
            # Find and update approval request
            approval_request = self._approval_store.get_request(payload.request_id)
            if not approval_request:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Approval request not found",
                )
            
            # Store response
            self._approval_store.add_response(payload)
            
            return {
                "requestId": payload.request_id,
                "status": payload.status.value,
                "processedAt": payload.timestamp,
            }
        
        @self.app.post(
            BridgeEndpoints.EVENT_V1,
            response_model=dict,
            status_code=status.HTTP_201_CREATED,
            summary="Send event",
            description="Send an activity event to Aegis.",
        )
        async def send_event(
            request: Request,
            credentials: HTTPAuthorizationCredentials | None = Security(security),
        ) -> dict[str, Any]:
            """
            Send an activity event.
            
            Events can include build started, test completed, file saved, etc.
            """
            # Extract and verify signature
            timestamp = request.headers.get("X-Aegis-Timestamp")
            nonce = request.headers.get("X-Aegis-Nonce")
            signature = request.headers.get("X-Aegis-Signature")
            
            if not all([timestamp, nonce, signature]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing authentication headers",
                )
            
            if not verify_signature(
                self.config.secret,
                "POST",
                BridgeEndpoints.EVENT_V1,
                timestamp,
                nonce,
                signature,
            ):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid signature",
                )
            
            # Parse request body
            try:
                body = await request.json()
                payload = EventPayload.from_dict(body)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid request body: {e}",
                )
            
            # In production, this would persist the event to Aegis
            return {
                "eventId": payload.event_id,
                "status": "received",
                "timestamp": payload.timestamp,
            }
        
        @self.app.post(
            BridgeEndpoints.EVIDENCE_V1,
            response_model=dict,
            status_code=status.HTTP_201_CREATED,
            summary="Submit evidence",
            description="Submit build/test evidence for workflow audit.",
        )
        async def submit_evidence(
            request: Request,
            credentials: HTTPAuthorizationCredentials | None = Security(security),
        ) -> dict[str, Any]:
            """
            Submit build/test evidence.
            
            Evidence includes test results, build outputs, and artifact hashes.
            """
            # Extract and verify signature
            timestamp = request.headers.get("X-Aegis-Timestamp")
            nonce = request.headers.get("X-Aegis-Nonce")
            signature = request.headers.get("X-Aegis-Signature")
            
            if not all([timestamp, nonce, signature]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing authentication headers",
                )
            
            if not verify_signature(
                self.config.secret,
                "POST",
                BridgeEndpoints.EVIDENCE_V1,
                timestamp,
                nonce,
                signature,
            ):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid signature",
                )
            
            # Parse request body
            try:
                body = await request.json()
                payload = EvidencePayload.from_dict(body)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid request body: {e}",
                )
            
            # In production, this would persist evidence to Aegis storage
            return {
                "evidenceId": payload.evidence_id,
                "status": "received",
                "timestamp": payload.timestamp,
            }
        
        @self.app.post(
            BridgeEndpoints.ARTIFACT_HANDOFF_V1,
            response_model=dict,
            status_code=status.HTTP_201_CREATED,
            summary="Handoff artifact",
            description="Handoff build artifacts to Aegis for storage and audit.",
        )
        async def handoff_artifact(
            request: Request,
            credentials: HTTPAuthorizationCredentials | None = Security(security),
        ) -> dict[str, Any]:
            """
            Handoff build artifacts.
            
            Artifacts are transferred with integrity verification via SHA-256.
            """
            # Extract and verify signature
            timestamp = request.headers.get("X-Aegis-Timestamp")
            nonce = request.headers.get("X-Aegis-Nonce")
            signature = request.headers.get("X-Aegis-Signature")
            
            if not all([timestamp, nonce, signature]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing authentication headers",
                )
            
            if not verify_signature(
                self.config.secret,
                "POST",
                BridgeEndpoints.ARTIFACT_HANDOFF_V1,
                timestamp,
                nonce,
                signature,
            ):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid signature",
                )
            
            # Parse request body
            try:
                body = await request.json()
                payload = ArtifactHandoffPayload.from_dict(body)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid request body: {e}",
                )
            
            # In production, this would initiate artifact transfer
            return {
                "handoffId": payload.handoff_id,
                "status": "received",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        
        # Workflow revision exchange endpoints (write-capable)
        
        @self.app.post(
            BridgeEndpoints.WORKFLOW_REVISION_OPEN_REQUEST_V1,
            response_model=dict,
            status_code=status.HTTP_202_ACCEPTED,
            summary="Request workflow revision open",
            description="Request Developer Studio to open a workflow revision for review, repair, build, and testing.",
        )
        async def request_workflow_revision_open(
            request: Request,
            credentials: HTTPAuthorizationCredentials | None = Security(security),
        ) -> dict[str, Any]:
            """
            Request to open a workflow revision in Developer Studio.
            
            Aegis sends this to request the IDE to open a specific workflow revision.
            """
            # Extract and verify signature
            timestamp = request.headers.get("X-Aegis-Timestamp")
            nonce = request.headers.get("X-Aegis-Nonce")
            signature = request.headers.get("X-Aegis-Signature")
            
            if not all([timestamp, nonce, signature]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing authentication headers",
                )
            
            if not verify_signature(
                self.config.secret,
                "POST",
                BridgeEndpoints.WORKFLOW_REVISION_OPEN_REQUEST_V1,
                timestamp,
                nonce,
                signature,
            ):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid signature",
                )
            
            # Parse request body
            try:
                body = await request.json()
                payload = WorkflowRevisionOpenRequest.from_dict(body)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid request body: {e}",
                )
            
            # Store the request for IDE to respond
            self._workflow_store.add_open_request(payload)
            
            return {
                "requestId": payload.request_id,
                "status": "accepted",
                "message": "Workflow revision open request accepted. IDE should respond with WORKFLOW_REVISION_OPEN_RESPONSE.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        
        @self.app.post(
            BridgeEndpoints.WORKFLOW_REVISION_OPEN_RESPONSE_V1,
            response_model=dict,
            status_code=status.HTTP_200_OK,
            summary="Respond to workflow revision open request",
            description="IDE responds to Aegis with confirmation that the revision was opened.",
        )
        async def respond_workflow_revision_open(
            request: Request,
            credentials: HTTPAuthorizationCredentials | None = Security(security),
        ) -> dict[str, Any]:
            """
            IDE responds to workflow revision open request.
            
            Confirms the revision was opened in Developer Studio.
            """
            # Extract and verify signature
            timestamp = request.headers.get("X-Aegis-Timestamp")
            nonce = request.headers.get("X-Aegis-Nonce")
            signature = request.headers.get("X-Aegis-Signature")
            
            if not all([timestamp, nonce, signature]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing authentication headers",
                )
            
            if not verify_signature(
                self.config.secret,
                "POST",
                BridgeEndpoints.WORKFLOW_REVISION_OPEN_RESPONSE_V1,
                timestamp,
                nonce,
                signature,
            ):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid signature",
                )
            
            # Parse request body
            try:
                body = await request.json()
                payload = WorkflowRevisionOpenResponse.from_dict(body)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid request body: {e}",
                )
            
            # Find and update the open request
            open_request = self._workflow_store.get_open_request(payload.request_id)
            if not open_request:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Workflow revision open request not found",
                )
            
            # Store response
            self._workflow_store.add_open_response(payload)
            
            return {
                "requestId": payload.request_id,
                "status": payload.status,
                "ideSessionId": payload.ide_session_id,
                "timestamp": payload.opened_at,
            }
        
        @self.app.post(
            BridgeEndpoints.BUILD_TEST_RESULT_V1,
            response_model=dict,
            status_code=status.HTTP_201_CREATED,
            summary="Submit build/test result",
            description="Submit build or test results for workflow revision validation.",
        )
        async def submit_build_test_result(
            request: Request,
            credentials: HTTPAuthorizationCredentials | None = Security(security),
        ) -> dict[str, Any]:
            """
            Submit build or test result.
            
            Developer Studio sends build/test results as evidence for workflow revision.
            """
            # Extract and verify signature
            timestamp = request.headers.get("X-Aegis-Timestamp")
            nonce = request.headers.get("X-Aegis-Nonce")
            signature = request.headers.get("X-Aegis-Signature")
            
            if not all([timestamp, nonce, signature]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing authentication headers",
                )
            
            if not verify_signature(
                self.config.secret,
                "POST",
                BridgeEndpoints.BUILD_TEST_RESULT_V1,
                timestamp,
                nonce,
                signature,
            ):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid signature",
                )
            
            # Parse request body
            try:
                body = await request.json()
                payload = BuildTestResult.from_dict(body)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid request body: {e}",
                )
            
            # Store the result
            if payload.result_type == "build":
                self._workflow_store.add_build_result(
                    payload.workflow_id,
                    payload.revision_id,
                    payload,
                )
            elif payload.result_type == "test":
                self._workflow_store.add_test_result(
                    payload.workflow_id,
                    payload.revision_id,
                    payload,
                )
            
            return {
                "resultId": payload.result_id,
                "status": "received",
                "timestamp": payload.timestamp,
            }
        
        @self.app.post(
            BridgeEndpoints.WORKFLOW_REVISION_COMPLETE_V1,
            response_model=dict,
            status_code=status.HTTP_200_OK,
            summary="Workflow revision complete",
            description="Notify Aegis that workflow revision review, build, test, and repair are complete.",
        )
        async def workflow_revision_complete(
            request: Request,
            credentials: HTTPAuthorizationCredentials | None = Security(security),
        ) -> dict[str, Any]:
            """
            Notify completion of workflow revision work.
            
            Developer Studio sends final results, hash verification, and approval recommendation.
            """
            # Extract and verify signature
            timestamp = request.headers.get("X-Aegis-Timestamp")
            nonce = request.headers.get("X-Aegis-Nonce")
            signature = request.headers.get("X-Aegis-Signature")
            
            if not all([timestamp, nonce, signature]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing authentication headers",
                )
            
            if not verify_signature(
                self.config.secret,
                "POST",
                BridgeEndpoints.WORKFLOW_REVISION_COMPLETE_V1,
                timestamp,
                nonce,
                signature,
            ):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid signature",
                )
            
            # Parse request body
            try:
                body = await request.json()
                payload = WorkflowRevisionComplete.from_dict(body)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid request body: {e}",
                )
            
            # Verify hash if requested
            if payload.hash_verified:
                # In production, verify the hash against stored revision hash
                # For now, we trust the IDE's verification
                pass
            
            # Store the completion
            self._workflow_store.add_completion(payload)
            
            return {
                "requestId": payload.request_id,
                "status": "processed",
                "recommendation": payload.recommendation,
                "timestamp": payload.completed_at,
            }
    
    def start(self) -> None:
        """Start the bridge server."""
        import uvicorn
        uvicorn.run(
            self.app,
            host=self.config.host,
            port=self.config.port,
            log_level="info",
        )


def get_bridge_server(settings: Settings) -> BridgeServer:
    """Get or create bridge server instance."""
    secret = settings.aegis_bridge_secret or secrets.token_hex(32)
    
    config = BridgeServerConfig(
        enabled=True,
        host="127.0.0.1",
        port=8765,
        secret=secret,
    )
    
    return BridgeServer(config, settings)
