"""Clean-machine packaging validation with hash verification."""
from __future__ import annotations

import gzip
import hashlib
import json
import tarfile
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class PackageManifest:
    """Manifest for a release package."""
    package_id: str
    version: str
    created_at: str
    artifact_root: str
    files: dict[str, str]  # path -> sha256
    signature: str | None = None  # Optional cryptographic signature
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def compute_signature(self) -> str:
        """Compute a signature for the manifest."""
        content = json.dumps({
            "package_id": self.package_id,
            "version": self.version,
            "created_at": self.created_at,
            "artifact_root": self.artifact_root,
            "files": self.files,
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()
    
    def validate_signature(self) -> bool:
        """Validate the manifest signature."""
        if not self.signature:
            return False
        computed = self.compute_signature()
        return computed == self.signature
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "package_id": self.package_id,
            "version": self.version,
            "created_at": self.created_at,
            "artifact_root": self.artifact_root,
            "files": self.files,
            "signature": self.signature,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PackageManifest":
        """Deserialize from dictionary."""
        return cls(
            package_id=data["package_id"],
            version=data["version"],
            created_at=data["created_at"],
            artifact_root=data["artifact_root"],
            files=data["files"],
            signature=data.get("signature"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ValidationReport:
    """Report from package validation."""
    valid: bool
    package_id: str
    version: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    file_count: int = 0
    total_size_bytes: int = 0
    validation_time_ms: float = 0.0
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "valid": self.valid,
            "package_id": self.package_id,
            "version": self.version,
            "errors": self.errors,
            "warnings": self.warnings,
            "file_count": self.file_count,
            "total_size_bytes": self.total_size_bytes,
            "validation_time_ms": self.validation_time_ms,
        }


class CleanMachineValidator:
    """Validates packages for clean-machine deployment."""
    
    # Files that should never be in a release package
    FORBIDDEN_PATTERNS = [
        r"\.git",
        r"\.venv",
        r"__pycache__",
        r"\.pyc$",
        r"\.pyo$",
        r"\.pytest_cache",
        r"\.idea",
        r"\.vscode",
        r"node_modules",
        r"bin/",
        r"obj/",
        r"\.build",
        r"\.artifacts",
        r"test_debug",
        r"\.env$",
        r"secret",
        r"credential",
        r"token",
    ]
    
    # Required files for a valid release package
    REQUIRED_FILES = [
        "README.md",
        "MANIFEST.json",
    ]
    
    def __init__(self, artifact_root: Path):
        self.artifact_root = artifact_root
    
    def validate_package(
        self,
        package_path: Path,
        manifest: PackageManifest | None = None,
    ) -> ValidationReport:
        """
        Validate a package for clean-machine deployment.
        
        Checks:
        1. Manifest integrity
        2. File hash verification
        3. Forbidden patterns
        4. Required files
        5. Package structure
        """
        import time
        start_time = time.time()
        
        report = ValidationReport(
            valid=True,
            package_id=manifest.package_id if manifest else "unknown",
            version=manifest.version if manifest else "unknown",
        )
        
        # Load manifest if not provided
        if manifest is None:
            manifest_path = package_path / "MANIFEST.json"
            if not manifest_path.exists():
                report.valid = False
                report.errors.append("Missing MANIFEST.json")
                return report
            try:
                manifest = PackageManifest.from_dict(json.loads(manifest_path.read_text()))
            except (json.JSONDecodeError, KeyError) as e:
                report.valid = False
                report.errors.append(f"Invalid MANIFEST.json: {e}")
                return report
        
        # Validate manifest signature
        if not manifest.validate_signature():
            report.valid = False
            report.errors.append("Manifest signature validation failed")
        
        # Check for forbidden patterns
        forbidden_found = []
        for rel_path in manifest.files.keys():
            for pattern in self.FORBIDDEN_PATTERNS:
                import re
                if re.search(pattern, rel_path, re.IGNORECASE):
                    forbidden_found.append(rel_path)
                    break
        
        if forbidden_found:
            report.valid = False
            report.errors.append(f"Forbidden patterns found: {forbidden_found[:5]}")
        
        # Check required files
        missing_required = []
        for required in self.REQUIRED_FILES:
            if required not in manifest.files:
                missing_required.append(required)
        
        if missing_required:
            report.warnings.append(f"Missing recommended files: {missing_required}")
        
        # Verify file hashes
        hash_mismatches = []
        total_size = 0
        for rel_path, expected_hash in manifest.files.items():
            file_path = self.artifact_root / rel_path
            if not file_path.exists():
                report.errors.append(f"Missing file: {rel_path}")
                continue
            
            content = file_path.read_bytes()
            actual_hash = hashlib.sha256(content).hexdigest()
            total_size += len(content)
            
            if actual_hash != expected_hash:
                hash_mismatches.append({
                    "path": rel_path,
                    "expected": expected_hash,
                    "actual": actual_hash,
                })
        
        if hash_mismatches:
            report.valid = False
            report.errors.append(f"Hash mismatches: {len(hash_mismatches)} files")
        
        report.file_count = len(manifest.files)
        report.total_size_bytes = total_size
        report.validation_time_ms = (time.time() - start_time) * 1000
        
        return report
    
    def create_package(
        self,
        package_id: str,
        version: str,
        source_root: Path,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
    ) -> tuple[Path, PackageManifest]:
        """
        Create a release package from a source root.
        
        Returns:
            Tuple of (package_path, manifest)
        """
        import re
        
        package_root = self.artifact_root / package_id / version
        package_root.mkdir(parents=True, exist_ok=True)
        
        files = {}
        
        # Walk source root and collect files
        for file_path in source_root.rglob("*"):
            if file_path.is_file():
                rel_path = file_path.relative_to(source_root)
                rel_str = str(rel_path).replace("\\", "/")
                
                # Check exclude patterns
                if exclude_patterns:
                    skip = False
                    for pattern in exclude_patterns:
                        if re.search(pattern, rel_str, re.IGNORECASE):
                            skip = True
                            break
                    if skip:
                        continue
                
                # Check include patterns (if specified, all must match)
                if include_patterns:
                    match = False
                    for pattern in include_patterns:
                        if re.search(pattern, rel_str, re.IGNORECASE):
                            match = True
                            break
                    if not match:
                        continue
                
                # Copy file to package
                dest_path = package_root / rel_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                dest_path.write_bytes(file_path.read_bytes())
                
                # Compute hash
                content = file_path.read_bytes()
                files[rel_str] = hashlib.sha256(content).hexdigest()
        
        # Create manifest
        manifest = PackageManifest(
            package_id=package_id,
            version=version,
            created_at=datetime.now(timezone.utc).isoformat(),
            artifact_root=str(package_root),
            files=files,
        )
        manifest.signature = manifest.compute_signature()
        
        # Write manifest
        manifest_path = package_root / "MANIFEST.json"
        manifest_path.write_text(json.dumps(manifest.to_dict(), indent=2))
        
        return package_root, manifest
    
    def export_package(
        self,
        package_id: str,
        version: str,
        output_path: Path,
    ) -> Path:
        """
        Export a package as a tar.gz archive for distribution.
        
        Returns:
            Path to the archive
        """
        package_root = self.artifact_root / package_id / version
        if not package_root.exists():
            raise ValueError(f"Package not found: {package_id}/{version}")
        
        archive_path = output_path / f"{package_id}-{version}.tar.gz"
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        
        with tarfile.open(archive_path, "w:gz") as tar:
            for file_path in package_root.rglob("*"):
                if file_path.is_file():
                    rel_path = file_path.relative_to(package_root)
                    tar.add(file_path, arcname=rel_path)
        
        return archive_path
    
    def import_package(
        self,
        archive_path: Path,
        package_id: str | None = None,
        version: str | None = None,
    ) -> tuple[Path, PackageManifest]:
        """
        Import a package from a tar.gz archive.
        
        Returns:
            Tuple of (package_root, manifest)
        """
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(self.artifact_root)
        
        # Find the extracted package
        extracted_dirs = [
            d for d in self.artifact_root.iterdir()
            if d.is_dir() and (d / "MANIFEST.json").exists()
        ]
        
        if not extracted_dirs:
            raise ValueError("No package found in archive")
        
        package_root = extracted_dirs[0]
        manifest_path = package_root / "MANIFEST.json"
        manifest = PackageManifest.from_dict(json.loads(manifest_path.read_text()))
        
        # Override package_id and version if provided
        if package_id:
            manifest.package_id = package_id
        if version:
            manifest.version = version
        
        return package_root, manifest


_default_validator: CleanMachineValidator | None = None


def get_clean_machine_validator(artifact_root: Path | None = None) -> CleanMachineValidator:
    """Get the global clean machine validator instance."""
    global _default_validator
    if _default_validator is None:
        if artifact_root is None:
            artifact_root = Path(__file__).resolve().parents[2] / "storage" / "artifacts"
        _default_validator = CleanMachineValidator(artifact_root)
    return _default_validator
