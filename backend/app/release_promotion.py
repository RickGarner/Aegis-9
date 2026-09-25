"""Release promotion and merge criteria system with acceptance matrix."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class ReleaseStage(Enum):
    """Release promotion stages."""
    DRAFT = "draft"
    TESTED = "tested"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    PROMOTED = "promoted"
    REJECTED = "rejected"


class AcceptanceCriteria(Enum):
    """Required acceptance criteria for release promotion."""
    ALL_TESTS_PASSED = "all_tests_passed"
    SECURITY_SCAN_CLEAN = "security_scan_clean"
    DOCUMENTATION_COMPLETE = "documentation_complete"
    BACKUP_VERIFIED = "backup_verified"
    ROLLBACK_TESTED = "rollback_tested"
    PERFORMANCE_BENCHMARKS_MET = "performance_benchmarks_met"
    DEPENDENCY_CHECKS_PASSED = "dependency_checks_passed"
    CHANGE_LOG_UPDATED = "change_log_updated"
    SUPERVISOR_APPROVAL = "supervisor_approval"


@dataclass
class AcceptanceMatrix:
    """Combined release acceptance matrix."""
    required_criteria: list[AcceptanceCriteria] = field(
        default_factory=lambda: [
            AcceptanceCriteria.ALL_TESTS_PASSED,
            AcceptanceCriteria.SECURITY_SCAN_CLEAN,
            AcceptanceCriteria.DOCUMENTATION_COMPLETE,
            AcceptanceCriteria.SUPERVISOR_APPROVAL,
        ]
    )
    optional_criteria: list[AcceptanceCriteria] = field(
        default_factory=lambda: [
            AcceptanceCriteria.BACKUP_VERIFIED,
            AcceptanceCriteria.ROLLBACK_TESTED,
            AcceptanceCriteria.PERFORMANCE_BENCHMARKS_MET,
            AcceptanceCriteria.DEPENDENCY_CHECKS_PASSED,
            AcceptanceCriteria.CHANGE_LOG_UPDATED,
        ]
    )
    
    def is_satisfied(self, satisfied: list[AcceptanceCriteria]) -> bool:
        """Check if all required criteria are satisfied."""
        return all(c in satisfied for c in self.required_criteria)
    
    def get_satisfaction_report(self, satisfied: list[AcceptanceCriteria]) -> dict[str, Any]:
        """Generate a satisfaction report."""
        return {
            "required": {
                "total": len(self.required_criteria),
                "satisfied": len([c for c in self.required_criteria if c in satisfied]),
                "missing": [c.value for c in self.required_criteria if c not in satisfied],
                "all_satisfied": self.is_satisfied(satisfied),
            },
            "optional": {
                "total": len(self.optional_criteria),
                "satisfied": len([c for c in self.optional_criteria if c in satisfied]),
                "remaining": [c.value for c in self.optional_criteria if c not in satisfied],
            },
            "overall_ready": self.is_satisfied(satisfied),
        }


@dataclass
class ReleasePackage:
    """Represents a release package with metadata and hashes."""
    package_id: str
    version: str
    created_at: str
    artifact_root: Path
    files: dict[str, str] = field(default_factory=dict)  # path -> sha256
    acceptance_matrix: AcceptanceMatrix = field(default_factory=AcceptanceMatrix)
    satisfied_criteria: list[AcceptanceCriteria] = field(default_factory=list)
    stage: ReleaseStage = ReleaseStage.DRAFT
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def compute_file_hashes(self) -> dict[str, str]:
        """Compute SHA-256 hashes for all files in the package."""
        hashes = {}
        for rel_path in self.files.keys():
            file_path = self.artifact_root / rel_path
            if file_path.exists():
                content = file_path.read_bytes()
                hashes[rel_path] = hashlib.sha256(content).hexdigest()
        return hashes
    
    def validate_integrity(self) -> bool:
        """Validate package integrity against stored hashes."""
        computed = self.compute_file_hashes()
        return computed == self.files
    
    def mark_tested(self) -> None:
        """Mark package as tested."""
        self.satisfied_criteria.append(AcceptanceCriteria.ALL_TESTS_PASSED)
        self.stage = ReleaseStage.TESTED
    
    def mark_reviewed(self, approver: str) -> None:
        """Mark package as reviewed and approved."""
        self.satisfied_criteria.append(AcceptanceCriteria.SUPERVISOR_APPROVAL)
        self.metadata["reviewed_by"] = approver
        self.metadata["reviewed_at"] = datetime.now(timezone.utc).isoformat()
        self.stage = ReleaseStage.REVIEWED
    
    def mark_approved(self) -> None:
        """Mark package as approved for promotion."""
        self.stage = ReleaseStage.APPROVED
    
    def mark_promoted(self) -> None:
        """Mark package as promoted to production."""
        self.stage = ReleaseStage.PROMOTED
        self.metadata["promoted_at"] = datetime.now(timezone.utc).isoformat()
    
    def can_promote(self) -> tuple[bool, list[str]]:
        """Check if package can be promoted and return any blockers."""
        blockers = []
        
        if not self.validate_integrity():
            blockers.append("Package integrity validation failed")
        
        if not self.acceptance_matrix.is_satisfied(self.satisfied_criteria):
            report = self.acceptance_matrix.get_satisfaction_report(self.satisfied_criteria)
            blockers.extend(report["required"]["missing"])
        
        return len(blockers) == 0, blockers
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "package_id": self.package_id,
            "version": self.version,
            "created_at": self.created_at,
            "files": self.files,
            "satisfied_criteria": [c.value for c in self.satisfied_criteria],
            "stage": self.stage.value,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any], artifact_root: Path) -> "ReleasePackage":
        """Deserialize from dictionary."""
        return cls(
            package_id=data["package_id"],
            version=data["version"],
            created_at=data["created_at"],
            artifact_root=artifact_root,
            files=data.get("files", {}),
            satisfied_criteria=[
                AcceptanceCriteria(c) for c in data.get("satisfied_criteria", [])
            ],
            stage=ReleaseStage(data.get("stage", "draft")),
            metadata=data.get("metadata", {}),
        )


class ReleasePromotionSystem:
    """Manages release promotion and merge criteria."""
    
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._packages: dict[str, ReleasePackage] = {}
        self._load_packages()
    
    def _load_packages(self) -> None:
        """Load existing packages from storage."""
        storage_file = self.storage_path / "release-packages.json"
        if storage_file.exists():
            try:
                data = json.loads(storage_file.read_text())
                for pkg_data in data.get("packages", []):
                    pkg = ReleasePackage.from_dict(
                        pkg_data,
                        Path(data.get("artifact_root", "."))
                    )
                    self._packages[pkg.package_id] = pkg
            except (json.JSONDecodeError, KeyError):
                self._packages = {}
    
    def _save_packages(self) -> None:
        """Save packages to storage."""
        storage_file = self.storage_path / "release-packages.json"
        data = {
            "artifact_root": str(self.storage_path / "artifacts"),
            "packages": [pkg.to_dict() for pkg in self._packages.values()],
        }
        storage_file.write_text(json.dumps(data, indent=2))
    
    def create_package(
        self,
        package_id: str,
        version: str,
        artifact_root: Path,
        files: dict[str, str],
    ) -> ReleasePackage:
        """Create a new release package."""
        pkg = ReleasePackage(
            package_id=package_id,
            version=version,
            created_at=datetime.now(timezone.utc).isoformat(),
            artifact_root=artifact_root,
            files=files,
        )
        self._packages[package_id] = pkg
        self._save_packages()
        return pkg
    
    def get_package(self, package_id: str) -> ReleasePackage | None:
        """Get a release package by ID."""
        return self._packages.get(package_id)
    
    def promote_package(
        self,
        package_id: str,
        action: str,
        actor: str,
    ) -> tuple[bool, str]:
        """
        Promote a package through stages.
        
        Actions: "test", "review", "approve", "promote"
        """
        pkg = self._packages.get(package_id)
        if not pkg:
            return False, f"Package {package_id} not found"
        
        if action == "test":
            pkg.mark_tested()
        elif action == "review":
            pkg.mark_reviewed(actor)
        elif action == "approve":
            can_promote, blockers = pkg.can_promote()
            if not can_promote:
                return False, f"Cannot promote: {', '.join(blockers)}"
            pkg.mark_approved()
        elif action == "promote":
            if pkg.stage != ReleaseStage.APPROVED:
                return False, "Package must be approved before promotion"
            pkg.mark_promoted()
        else:
            return False, f"Unknown action: {action}"
        
        self._save_packages()
        return True, f"Package {package_id} promoted to {pkg.stage.value}"
    
    def get_acceptance_matrix(self) -> dict[str, Any]:
        """Get the current acceptance matrix configuration."""
        matrix = AcceptanceMatrix()
        return matrix.get_satisfaction_report([])
    
    def update_acceptance_matrix(
        self,
        required: list[str] | None = None,
        optional: list[str] | None = None,
    ) -> AcceptanceMatrix:
        """Update the acceptance matrix configuration."""
        matrix = AcceptanceMatrix()
        if required:
            matrix.required_criteria = [
                AcceptanceCriteria(c) for c in required
                if c in [c.value for c in AcceptanceCriteria]
            ]
        if optional:
            matrix.optional_criteria = [
                AcceptanceCriteria(c) for c in optional
                if c in [c.value for c in AcceptanceCriteria]
            ]
        return matrix
    
    def list_packages(self) -> list[dict[str, Any]]:
        """List all release packages."""
        return [
            {
                "package_id": pkg.package_id,
                "version": pkg.version,
                "stage": pkg.stage.value,
                "created_at": pkg.created_at,
                "satisfied_criteria": len(pkg.satisfied_criteria),
            }
            for pkg in self._packages.values()
        ]


_default_system: ReleasePromotionSystem | None = None


def get_release_promotion_system(storage_path: Path | None = None) -> ReleasePromotionSystem:
    """Get the global release promotion system instance."""
    global _default_system
    if _default_system is None:
        if storage_path is None:
            storage_path = Path(__file__).resolve().parents[2] / "storage" / "release"
        _default_system = ReleasePromotionSystem(storage_path)
    return _default_system
