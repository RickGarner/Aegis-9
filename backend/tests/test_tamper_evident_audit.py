"""Tests for tamper-evident audit chain and artifact signing."""
import base64
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption

from app.local_audit import LocalAuditStore
from app.workflow_runner import WorkflowTestRunner, PreparedArtifact


class TestAuditChain:
    """Test tamper-evident audit chain functionality."""

    def test_chain_generates_sequence_and_hashes(self, tmp_path: Path) -> None:
        """Test that each event gets sequence number and hash linkage."""
        store = LocalAuditStore(tmp_path / "audit.jsonl")
        
        event1 = store.append("test.event", {"data": "first"})
        event2 = store.append("test.event", {"data": "second"})
        
        # Verify sequence numbers
        assert event1["sequence"] == 0
        assert event2["sequence"] == 1
        
        # Verify chain linkage
        assert event1["previousHash"] == "genesis"
        assert event2["previousHash"] == event1["currentHash"]
        
        # Verify hashes are present
        assert len(event1["currentHash"]) == 64
        assert len(event2["currentHash"]) == 64

    def test_chain_verification_intact(self, tmp_path: Path) -> None:
        """Test that chain verification passes for intact chain."""
        store = LocalAuditStore(tmp_path / "audit.jsonl")
        
        for i in range(10):
            store.append("test.event", {"index": i})
        
        result = store.verify_chain()
        assert result["valid"] is True
        assert result["message"] == "Chain intact"
        assert result["events"] == 10

    def test_chain_verification_empty(self, tmp_path: Path) -> None:
        """Test chain verification with no events."""
        store = LocalAuditStore(tmp_path / "audit.jsonl")
        result = store.verify_chain()
        assert result["valid"] is True
        assert result["events"] == 0

    def test_chain_verification_detects_tampering(self, tmp_path: Path) -> None:
        """Test that chain verification detects tampered events."""
        store = LocalAuditStore(tmp_path / "audit.jsonl")
        
        store.append("test.event", {"data": "original"})
        store.append("test.event", {"data": "second"})
        
        # Tamper with the first event
        audit_file = tmp_path / "audit.jsonl"
        lines = audit_file.read_text(encoding="utf-8").splitlines()
        tampered_line = lines[0].replace('"data": "[REDACTED]"', '"data": "tampered"')
        lines[0] = tampered_line
        audit_file.write_text("\n".join(lines), encoding="utf-8")
        
        result = store.verify_chain()
        assert result["valid"] is False
        assert "Chain broken" in result["message"]


class TestArtifactSigning:
    """Test artifact signing functionality."""

    def test_artifact_signed_when_key_provided(self, tmp_path: Path) -> None:
        """Test that artifacts are signed when signing key is configured."""
        # Generate Ed25519 key
        private_key = Ed25519PrivateKey.generate()
        key_path = tmp_path / "signing-key.pem"
        private_key_bytes = private_key.private_bytes(
            encoding=Encoding.PEM,
            format=PrivateFormat.PKCS8,
            encryption_algorithm=NoEncryption(),
        )
        key_path.write_bytes(private_key_bytes)
        
        # Create runner with signing key
        artifact_root = tmp_path / "artifacts"
        runner = WorkflowTestRunner(artifact_root, signing_key_path=key_path)
        
        # Prepare artifact with valid PowerShell code
        artifact = runner.prepare(
            transfer_id="test-transfer",
            revision=1,
            language="powershell",
            implementation="```powershell\nWrite-Host 'Hello'\n```",
        )
        
        # Verify signature exists
        assert artifact.signature is not None
        assert len(artifact.signature) > 0
        
        # Verify signature is base64 encoded
        try:
            decoded = base64.b64decode(artifact.signature)
            assert len(decoded) == 64  # Ed25519 signature is 64 bytes
        except Exception:
            pytest.fail("Signature is not valid base64")

    def test_artifact_unsigned_when_no_key(self, tmp_path: Path) -> None:
        """Test that artifacts are not signed when no key is provided."""
        artifact_root = tmp_path / "artifacts"
        runner = WorkflowTestRunner(artifact_root)
        
        artifact = runner.prepare(
            transfer_id="test-transfer",
            revision=1,
            language="powershell",
            implementation="```powershell\nWrite-Host 'Hello'\n```",
        )
        
        assert artifact.signature is None

    def test_artifact_chain_linkage(self, tmp_path: Path) -> None:
        """Test that artifacts can be chained via previous_hash."""
        artifact_root = tmp_path / "artifacts"
        runner = WorkflowTestRunner(artifact_root)
        
        # Prepare first artifact
        artifact1 = runner.prepare(
            transfer_id="test-transfer",
            revision=1,
            language="powershell",
            implementation="```powershell\nWrite-Host 'First'\n```",
        )
        
        # Prepare second artifact with chain linkage
        artifact2 = runner.prepare(
            transfer_id="test-transfer",
            revision=2,
            language="powershell",
            implementation="```powershell\nWrite-Host 'Second'\n```",
            previous_hash=artifact1.sha256,
        )
        
        assert artifact2.previous_hash == artifact1.sha256
        assert artifact2.sha256 != artifact1.sha256

    def test_evidence_includes_signature_and_chain(self, tmp_path: Path) -> None:
        """Test that workflow evidence includes signature and chain info."""
        private_key = Ed25519PrivateKey.generate()
        key_path = tmp_path / "signing-key.pem"
        private_key_bytes = private_key.private_bytes(
            encoding=Encoding.PEM,
            format=PrivateFormat.PKCS8,
            encryption_algorithm=NoEncryption(),
        )
        key_path.write_bytes(private_key_bytes)
        
        artifact_root = tmp_path / "artifacts"
        runner = WorkflowTestRunner(artifact_root, signing_key_path=key_path)
        
        artifact = runner.prepare(
            transfer_id="test-transfer",
            revision=1,
            language="powershell",
            implementation="```powershell\nWrite-Host 'Hello'\n```",
        )
        
        # Run test to generate evidence
        evidence = runner.run(artifact, "powershell", "static")
        
        # Verify evidence includes signature and chain info
        assert evidence.artifact_signature is not None
        assert evidence.previous_hash is None  # First artifact has no previous


class TestIntegration:
    """Integration tests for tamper-evident workflow."""

    def test_full_workflow_with_signing_and_audit(self, tmp_path: Path) -> None:
        """Test complete workflow with artifact signing and audit logging."""
        # Setup signing key
        private_key = Ed25519PrivateKey.generate()
        key_path = tmp_path / "signing-key.pem"
        private_key_bytes = private_key.private_bytes(
            encoding=Encoding.PEM,
            format=PrivateFormat.PKCS8,
            encryption_algorithm=NoEncryption(),
        )
        key_path.write_bytes(private_key_bytes)
        
        # Setup audit store
        audit_store = LocalAuditStore(tmp_path / "audit.jsonl")
        
        # Setup artifact runner
        artifact_root = tmp_path / "artifacts"
        runner = WorkflowTestRunner(artifact_root, signing_key_path=key_path)
        
        # Log workflow start
        audit_store.append("workflow.started", {"transfer_id": "test-001", "revision": 1})
        
        # Prepare and sign artifact
        artifact = runner.prepare(
            transfer_id="test-001",
            revision=1,
            language="powershell",
            implementation="```powershell\nWrite-Host 'Test Workflow'\n```",
        )
        
        # Log artifact creation
        audit_store.append("workflow.artifact.created", {
            "transfer_id": "test-001",
            "revision": 1,
            "sha256": artifact.sha256,
            "signed": artifact.signature is not None,
        })
        
        # Run test
        evidence = runner.run(artifact, "powershell", "static")
        
        # Log test completion
        audit_store.append("workflow.test.completed", {
            "transfer_id": "test-001",
            "revision": 1,
            "status": evidence.status,
            "artifact_sha256": evidence.artifact_sha256,
        })
        
        # Verify chain
        chain_result = audit_store.verify_chain()
        assert chain_result["valid"] is True
        assert chain_result["events"] == 3
        
        # Verify artifact was signed
        assert artifact.signature is not None
        assert evidence.artifact_signature is not None
