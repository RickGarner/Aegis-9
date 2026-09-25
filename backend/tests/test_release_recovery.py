"""Comprehensive tests for release and recovery discipline (Priority 0.5)."""
import gzip
import hashlib
import json
import sqlite3
import tempfile
from pathlib import Path
from unittest import TestCase

import pytest

from app.release_promotion import (
    AcceptanceCriteria,
    AcceptanceMatrix,
    ReleasePackage,
    ReleasePromotionSystem,
    ReleaseStage,
)
from app.package_validation import (
    CleanMachineValidator,
    PackageManifest,
    ValidationReport,
)
from app.database_recovery import (
    DatabaseBackupSystem,
    UpgradeRecoverySystem,
    UpgradeStatus,
    BackupMetadata,
    RestoreReport,
)


# ============================================================================
# Release Promotion Tests
# ============================================================================

class TestAcceptanceMatrix(TestCase):
    """Tests for AcceptanceMatrix."""
    
    def test_default_required_criteria(self):
        matrix = AcceptanceMatrix()
        assert len(matrix.required_criteria) == 4
    
    def test_default_optional_criteria(self):
        matrix = AcceptanceMatrix()
        assert len(matrix.optional_criteria) == 5
    
    def test_is_satisfied_all_required(self):
        matrix = AcceptanceMatrix()
        satisfied = [
            AcceptanceCriteria.ALL_TESTS_PASSED,
            AcceptanceCriteria.SECURITY_SCAN_CLEAN,
            AcceptanceCriteria.DOCUMENTATION_COMPLETE,
            AcceptanceCriteria.SUPERVISOR_APPROVAL,
        ]
        assert matrix.is_satisfied(satisfied) is True
    
    def test_is_satisfied_missing_required(self):
        matrix = AcceptanceMatrix()
        satisfied = [
            AcceptanceCriteria.ALL_TESTS_PASSED,
            AcceptanceCriteria.SECURITY_SCAN_CLEAN,
        ]
        assert matrix.is_satisfied(satisfied) is False
    
    def test_get_satisfaction_report(self):
        matrix = AcceptanceMatrix()
        satisfied = [AcceptanceCriteria.ALL_TESTS_PASSED]
        report = matrix.get_satisfaction_report(satisfied)
        
        assert report["required"]["total"] == 4
        assert report["required"]["satisfied"] == 1
        assert len(report["required"]["missing"]) == 3
        assert report["overall_ready"] is False


class TestReleasePackage(TestCase):
    """Tests for ReleasePackage."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_create_package(self):
        pkg = ReleasePackage(
            package_id="test-pkg",
            version="1.0.0",
            created_at="2026-09-21T00:00:00Z",
            artifact_root=self.temp_path,
            files={"README.md": "abc123"},
        )
        
        assert pkg.package_id == "test-pkg"
        assert pkg.version == "1.0.0"
        assert pkg.stage == ReleaseStage.DRAFT
    
    def test_mark_tested(self):
        pkg = ReleasePackage(
            package_id="test-pkg",
            version="1.0.0",
            created_at="2026-09-21T00:00:00Z",
            artifact_root=self.temp_path,
        )
        
        pkg.mark_tested()
        
        assert pkg.stage == ReleaseStage.TESTED
        assert AcceptanceCriteria.ALL_TESTS_PASSED in pkg.satisfied_criteria
    
    def test_mark_reviewed(self):
        pkg = ReleasePackage(
            package_id="test-pkg",
            version="1.0.0",
            created_at="2026-09-21T00:00:00Z",
            artifact_root=self.temp_path,
        )
        
        pkg.mark_reviewed("supervisor@example.com")
        
        assert pkg.stage == ReleaseStage.REVIEWED
        assert "supervisor@example.com" in pkg.metadata.get("reviewed_by", "")
    
    def test_can_promote_without_requirements(self):
        pkg = ReleasePackage(
            package_id="test-pkg",
            version="1.0.0",
            created_at="2026-09-21T00:00:00Z",
            artifact_root=self.temp_path,
        )
        
        can_promote, blockers = pkg.can_promote()
        assert can_promote is False
        assert len(blockers) > 0
    
    def test_can_promote_with_requirements(self):
        pkg = ReleasePackage(
            package_id="test-pkg",
            version="1.0.0",
            created_at="2026-09-21T00:00:00Z",
            artifact_root=self.temp_path,
        )
        
        pkg.satisfied_criteria = [
            AcceptanceCriteria.ALL_TESTS_PASSED,
            AcceptanceCriteria.SECURITY_SCAN_CLEAN,
            AcceptanceCriteria.DOCUMENTATION_COMPLETE,
            AcceptanceCriteria.SUPERVISOR_APPROVAL,
        ]
        
        can_promote, blockers = pkg.can_promote()
        assert can_promote is True
        assert len(blockers) == 0
    
    def test_to_dict_and_from_dict(self):
        pkg = ReleasePackage(
            package_id="test-pkg",
            version="1.0.0",
            created_at="2026-09-21T00:00:00Z",
            artifact_root=self.temp_path,
            files={"README.md": "abc123"},
            satisfied_criteria=[AcceptanceCriteria.ALL_TESTS_PASSED],
        )
        
        data = pkg.to_dict()
        restored = ReleasePackage.from_dict(data, self.temp_path)
        
        assert restored.package_id == pkg.package_id
        assert restored.version == pkg.version
        assert restored.files == pkg.files


class TestReleasePromotionSystem(TestCase):
    """Tests for ReleasePromotionSystem."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        self.system = ReleasePromotionSystem(self.temp_path)
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_create_package(self):
        # Create the README.md file first to get the correct hash
        readme_path = self.temp_path / "README.md"
        readme_path.write_text("test content")
        import hashlib
        correct_hash = hashlib.sha256(readme_path.read_bytes()).hexdigest()
        
        pkg = self.system.create_package(
            package_id="test-pkg",
            version="1.0.0",
            artifact_root=self.temp_path,
            files={"README.md": correct_hash},
        )
        
        assert pkg.package_id == "test-pkg"
        assert pkg.version == "1.0.0"
        assert len(self.system.list_packages()) == 1
    
    def test_promote_package_through_stages(self):
        # Create the README.md file first to get the correct hash
        readme_path = self.temp_path / "README.md"
        readme_path.write_text("test content")
        import hashlib
        correct_hash = hashlib.sha256(readme_path.read_bytes()).hexdigest()
        
        pkg = self.system.create_package(
            package_id="test-pkg",
            version="1.0.0",
            artifact_root=self.temp_path,
            files={"README.md": correct_hash},
        )
        
        # Mark as tested
        success, _ = self.system.promote_package(pkg.package_id, "test", "operator")
        assert success is True
        assert pkg.stage == ReleaseStage.TESTED
        
        # Mark as reviewed
        success, _ = self.system.promote_package(pkg.package_id, "review", "supervisor@example.com")
        assert success is True
        assert pkg.stage == ReleaseStage.REVIEWED
        
        # Cannot approve yet (missing requirements)
        success, _ = self.system.promote_package(pkg.package_id, "approve", "supervisor")
        assert success is False
        
        # Add requirements
        pkg.satisfied_criteria = [
            AcceptanceCriteria.ALL_TESTS_PASSED,
            AcceptanceCriteria.SECURITY_SCAN_CLEAN,
            AcceptanceCriteria.DOCUMENTATION_COMPLETE,
            AcceptanceCriteria.SUPERVISOR_APPROVAL,
        ]
        
        # Approve
        success, msg = self.system.promote_package(pkg.package_id, "approve", "supervisor")
        assert success is True
        assert pkg.stage == ReleaseStage.APPROVED
        
        # Promote
        success, msg = self.system.promote_package(pkg.package_id, "promote", "operator")
        assert success is True
        assert pkg.stage == ReleaseStage.PROMOTED
    
    def test_get_acceptance_matrix(self):
        matrix = self.system.get_acceptance_matrix()
        assert "required" in matrix
        assert "optional" in matrix
        assert "overall_ready" in matrix


# ============================================================================
# Package Validation Tests
# ============================================================================

class TestPackageManifest(TestCase):
    """Tests for PackageManifest."""
    
    def test_compute_signature(self):
        manifest = PackageManifest(
            package_id="test-pkg",
            version="1.0.0",
            created_at="2026-09-21T00:00:00Z",
            artifact_root="/artifacts",
            files={"README.md": "abc123"},
        )
        
        signature = manifest.compute_signature()
        assert len(signature) == 64  # SHA-256 hex length
    
    def test_validate_signature(self):
        manifest = PackageManifest(
            package_id="test-pkg",
            version="1.0.0",
            created_at="2026-09-21T00:00:00Z",
            artifact_root="/artifacts",
            files={"README.md": "abc123"},
        )
        
        manifest.signature = manifest.compute_signature()
        assert manifest.validate_signature() is True
    
    def test_validate_signature_invalid(self):
        manifest = PackageManifest(
            package_id="test-pkg",
            version="1.0.0",
            created_at="2026-09-21T00:00:00Z",
            artifact_root="/artifacts",
            files={"README.md": "abc123"},
        )
        
        manifest.signature = "invalid_signature"
        assert manifest.validate_signature() is False


class TestCleanMachineValidator(TestCase):
    """Tests for CleanMachineValidator."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        self.validator = CleanMachineValidator(self.temp_path)
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_validate_package_missing_manifest(self):
        package_path = self.temp_path / "test-pkg" / "1.0.0"
        package_path.mkdir(parents=True)
        
        report = self.validator.validate_package(package_path)
        
        assert report.valid is False
        assert any("MANIFEST.json" in err for err in report.errors)
    
    def test_validate_package_hash_mismatch(self):
        package_path = self.temp_path / "test-pkg" / "1.0.0"
        package_path.mkdir(parents=True)
        
        # Create a file
        test_file = package_path / "README.md"
        test_file.write_text("test content")
        
        # Create validator with the package path as artifact root
        validator = CleanMachineValidator(package_path)
        
        # Create manifest with wrong hash
        manifest = PackageManifest(
            package_id="test-pkg",
            version="1.0.0",
            created_at="2026-09-21T00:00:00Z",
            artifact_root=str(package_path),
            files={"README.md": "wronghash"},
        )
        manifest.signature = manifest.compute_signature()
        (package_path / "MANIFEST.json").write_text(json.dumps(manifest.to_dict()))
        
        report = validator.validate_package(package_path, manifest)
        
        assert report.valid is False
        assert any("Hash mismatch" in err or "mismatch" in err.lower() for err in report.errors)
    
    def test_validate_package_forbidden_patterns(self):
        package_path = self.temp_path / "test-pkg" / "1.0.0"
        package_path.mkdir(parents=True)
        
        # Create manifest with forbidden pattern
        manifest = PackageManifest(
            package_id="test-pkg",
            version="1.0.0",
            created_at="2026-09-21T00:00:00Z",
            artifact_root=str(package_path),
            files={".git/config": "abc123", "src/main.py": "def456"},
        )
        manifest.signature = manifest.compute_signature()
        (package_path / "MANIFEST.json").write_text(json.dumps(manifest.to_dict()))
        
        report = self.validator.validate_package(package_path, manifest)
        
        assert report.valid is False
        assert any("Forbidden" in err for err in report.errors)
    
    def test_validate_package_valid(self):
        package_path = self.temp_path / "test-pkg" / "1.0.0"
        package_path.mkdir(parents=True)
        
        # Create files
        (package_path / "README.md").write_text("# Test")
        (package_path / "src").mkdir()
        (package_path / "src" / "main.py").write_text("print('hello')")
        
        # Create manifest with correct hashes
        files = {}
        for file_path in package_path.rglob("*"):
            if file_path.is_file():
                rel_path = file_path.relative_to(package_path)
                content = file_path.read_bytes()
                files[str(rel_path).replace("\\", "/")] = hashlib.sha256(content).hexdigest()
        
        manifest = PackageManifest(
            package_id="test-pkg",
            version="1.0.0",
            created_at="2026-09-21T00:00:00Z",
            artifact_root=str(package_path),
            files=files,
        )
        manifest.signature = manifest.compute_signature()
        (package_path / "MANIFEST.json").write_text(json.dumps(manifest.to_dict()))
        
        report = self.validator.validate_package(package_path, manifest)
        
        assert report.valid is True
        assert report.file_count == len(files)
    
    def test_create_package(self):
        source_root = self.temp_path / "source"
        source_root.mkdir()
        (source_root / "README.md").write_text("# Test")
        (source_root / "src").mkdir()
        (source_root / "src" / "main.py").write_text("print('hello')")
        
        package_path, manifest = self.validator.create_package(
            package_id="test-pkg",
            version="1.0.0",
            source_root=source_root,
        )
        
        assert package_path.exists()
        assert (package_path / "MANIFEST.json").exists()
        assert manifest.package_id == "test-pkg"
        assert manifest.version == "1.0.0"
    
    def test_export_package(self):
        source_root = self.temp_path / "source"
        source_root.mkdir()
        (source_root / "README.md").write_text("# Test")
        
        package_path, manifest = self.validator.create_package(
            package_id="test-pkg",
            version="1.0.0",
            source_root=source_root,
        )
        
        archive_path = self.validator.export_package(
            package_id="test-pkg",
            version="1.0.0",
            output_path=self.temp_path,
        )
        
        assert archive_path.exists()
        # Archive should be .tar.gz
        assert archive_path.suffix == ".gz"
        assert ".tar" in archive_path.name


# ============================================================================
# Database Recovery Tests
# ============================================================================

class TestDatabaseBackupSystem(TestCase):
    """Tests for DatabaseBackupSystem."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        self.backup_system = DatabaseBackupSystem(self.temp_path)
        
        # Create a test database
        self.db_path = self.temp_path / "test.db"
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT)")
            conn.execute("INSERT INTO test_table (name) VALUES ('test1'), ('test2')")
            # Create metadata table if it doesn't exist
            conn.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT)")
            conn.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES ('schema_version', '1')")
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_create_backup(self):
        backup_path, metadata = self.backup_system.create_backup(
            database_path=self.db_path,
            backup_id="test-backup",
        )
        
        assert Path(backup_path).exists()
        assert metadata.backup_id == "test-backup"
        assert int(metadata.schema_version) == 1
        assert "test_table" in metadata.record_counts
        assert metadata.record_counts["test_table"] == 2
    
    def test_restore_backup(self):
        backup_path, _ = self.backup_system.create_backup(
            database_path=self.db_path,
            backup_id="test-backup",
        )
        
        # Create a new database path
        restore_path = self.temp_path / "restored.db"
        
        report = self.backup_system.restore_backup(
            backup_path=backup_path,
            target_path=restore_path,
            verify_integrity=True,
        )
        
        assert report.success is True
        assert restore_path.exists()
        assert "test_table" in report.restored_tables
    
    def test_restore_backup_integrity_failure(self):
        backup_path, metadata = self.backup_system.create_backup(
            database_path=self.db_path,
            backup_id="test-backup",
        )
        
        # Corrupt the backup
        import gzip
        compressed = gzip.decompress(Path(backup_path).read_bytes())
        corrupted = compressed[:-10]  # Remove last 10 bytes
        
        Path(backup_path).write_bytes(corrupted)
        
        restore_path = self.temp_path / "restored.db"
        report = self.backup_system.restore_backup(
            backup_path=backup_path,
            target_path=restore_path,
            verify_integrity=True,
        )
        
        assert report.success is False
        # Check for either integrity failure or decompression error
        assert report.success is False or any("integrity" in err.lower() or "decompress" in err.lower() for err in report.errors)
    
    def test_list_backups(self):
        self.backup_system.create_backup(
            database_path=self.db_path,
            backup_id="backup-1",
        )
        self.backup_system.create_backup(
            database_path=self.db_path,
            backup_id="backup-2",
        )
        
        backups = self.backup_system.list_backups()
        assert len(backups) == 2
    
    def test_validate_backup(self):
        backup_path, metadata = self.backup_system.create_backup(
            database_path=self.db_path,
            backup_id="test-backup",
        )
        
        valid, errors = self.backup_system.validate_backup("test-backup")
        assert valid is True
        assert len(errors) == 0
        
        # Also verify schema version is correct
        assert int(metadata.schema_version) == 1
    
    def test_delete_backup(self):
        self.backup_system.create_backup(
            database_path=self.db_path,
            backup_id="test-backup",
        )
        
        assert self.backup_system.delete_backup("test-backup") is True
        assert self.backup_system.get_backup("test-backup") is None


class TestUpgradeRecoverySystem(TestCase):
    """Tests for UpgradeRecoverySystem."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        self.upgrade_system = UpgradeRecoverySystem(self.temp_path)
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_begin_upgrade(self):
        source_db = self.temp_path / "source.db"
        target_db = self.temp_path / "target.db"
        source_db.write_text("dummy")
        target_db.write_text("dummy")
        
        state = self.upgrade_system.begin_upgrade(
            upgrade_id="upgrade-1",
            source_database=source_db,
            target_database=target_db,
            schema_version_from=1,
            schema_version_to=2,
        )
        
        assert state.upgrade_id == "upgrade-1"
        assert state.status == UpgradeStatus.INITIALIZING
        assert state.schema_version_from == 1
        assert state.schema_version_to == 2
    
    def test_update_progress(self):
        source_db = self.temp_path / "source.db"
        target_db = self.temp_path / "target.db"
        source_db.write_text("dummy")
        target_db.write_text("dummy")
        
        self.upgrade_system.begin_upgrade(
            upgrade_id="upgrade-1",
            source_database=source_db,
            target_database=target_db,
            schema_version_from=1,
            schema_version_to=2,
        )
        
        state = self.upgrade_system.update_progress(50, "Migrating tables")
        
        assert state.progress_percent == 50
        assert state.last_action == "Migrating tables"
    
    def test_mark_rollback_available(self):
        source_db = self.temp_path / "source.db"
        target_db = self.temp_path / "target.db"
        rollback_db = self.temp_path / "rollback.db"
        source_db.write_text("dummy")
        target_db.write_text("dummy")
        rollback_db.write_text("dummy")
        
        self.upgrade_system.begin_upgrade(
            upgrade_id="upgrade-1",
            source_database=source_db,
            target_database=target_db,
            schema_version_from=1,
            schema_version_to=2,
        )
        
        state = self.upgrade_system.mark_rollback_available(rollback_db)
        
        assert state.rollback_available is True
        assert state.rollback_path == str(rollback_db)
    
    def test_recover_interrupted_upgrade(self):
        source_db = self.temp_path / "source.db"
        target_db = self.temp_path / "target.db"
        rollback_db = self.temp_path / "rollback.db"
        source_db.write_text("dummy")
        target_db.write_text("dummy")
        rollback_db.write_text("dummy")
        
        self.upgrade_system.begin_upgrade(
            upgrade_id="upgrade-1",
            source_database=source_db,
            target_database=target_db,
            schema_version_from=1,
            schema_version_to=2,
        )
        
        self.upgrade_system.mark_rollback_available(rollback_db)
        
        # Simulate failure
        self.upgrade_system.update_progress(50, "Migrating tables", "Connection lost")
        
        recovered = self.upgrade_system.recover_interrupted_upgrade()
        
        assert recovered is not None
        assert recovered.upgrade_id == "upgrade-1"
    
    def test_get_current_state(self):
        assert self.upgrade_system.get_current_state() is None
        
        source_db = self.temp_path / "source.db"
        target_db = self.temp_path / "target.db"
        source_db.write_text("dummy")
        target_db.write_text("dummy")
        
        self.upgrade_system.begin_upgrade(
            upgrade_id="upgrade-1",
            source_database=source_db,
            target_database=target_db,
            schema_version_from=1,
            schema_version_to=2,
        )
        
        state = self.upgrade_system.get_current_state()
        assert state is not None
        assert state.upgrade_id == "upgrade-1"


# ============================================================================
# Integration Tests
# ============================================================================

class TestReleaseRecoveryIntegration(TestCase):
    """Integration tests for release and recovery systems."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Create required directories
        (self.temp_path / "release").mkdir()
        (self.temp_path / "artifacts").mkdir()
        (self.temp_path / "backups").mkdir()
        (self.temp_path / "upgrade-state").mkdir()
        
        # Initialize all systems
        self.release_system = ReleasePromotionSystem(self.temp_path / "release")
        self.validator = CleanMachineValidator(self.temp_path / "artifacts")
        self.backup_system = DatabaseBackupSystem(self.temp_path / "backups")
        self.upgrade_system = UpgradeRecoverySystem(self.temp_path / "upgrade-state")
        
        # Create test database
        self.db_path = self.temp_path / "test.db"
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT)")
            conn.execute("INSERT INTO test_table (name) VALUES ('test1')")
            conn.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT)")
            conn.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES ('schema_version', '1')")
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_full_release_workflow(self):
        """Test complete release workflow from creation to promotion."""
        # Create source files
        source_root = self.temp_path / "source"
        source_root.mkdir()
        (source_root / "README.md").write_text("# Release Test")
        (source_root / "app.py").write_text("print('hello')")
        
        # Create package
        package_path, manifest = self.validator.create_package(
            package_id="release-test",
            version="1.0.0",
            source_root=source_root,
        )
        
        # Validate package
        report = self.validator.validate_package(package_path, manifest)
        assert report.valid is True
        
        # Create release package using the package_path as artifact_root
        pkg = self.release_system.create_package(
            package_id="release-test",
            version="1.0.0",
            artifact_root=package_path,
            files=manifest.files,
        )
        
        # Promote through stages
        success, _ = self.release_system.promote_package(pkg.package_id, "test", "operator")
        pkg.satisfied_criteria.append(AcceptanceCriteria.ALL_TESTS_PASSED)
        
        success, _ = self.release_system.promote_package(pkg.package_id, "review", "supervisor@example.com")
        pkg.satisfied_criteria.append(AcceptanceCriteria.SUPERVISOR_APPROVAL)
        
        # Add remaining requirements
        pkg.satisfied_criteria.extend([
            AcceptanceCriteria.SECURITY_SCAN_CLEAN,
            AcceptanceCriteria.DOCUMENTATION_COMPLETE,
        ])
        
        success, _ = self.release_system.promote_package(pkg.package_id, "approve", "supervisor")
        assert success is True
        
        success, _ = self.release_system.promote_package(pkg.package_id, "promote", "operator")
        assert success is True
        assert pkg.stage == ReleaseStage.PROMOTED
    
    def test_full_backup_restore_workflow(self):
        """Test complete backup and restore workflow."""
        # Create backup
        backup_path, metadata = self.backup_system.create_backup(
            database_path=self.db_path,
            backup_id="pre-upgrade-backup",
        )
        
        # Validate backup
        valid, errors = self.backup_system.validate_backup("pre-upgrade-backup")
        assert valid is True
        
        # Begin upgrade
        source_db = self.temp_path / "source.db"
        target_db = self.temp_path / "target.db"
        source_db.write_text("dummy")
        target_db.write_text("dummy")
        
        self.upgrade_system.begin_upgrade(
            upgrade_id="upgrade-1",
            source_database=source_db,
            target_database=target_db,
            schema_version_from=1,
            schema_version_to=2,
        )
        
        # Mark rollback available
        self.upgrade_system.mark_rollback_available(backup_path)
        
        # Simulate upgrade progress
        self.upgrade_system.update_progress(50, "Migrating data")
        
        # Recover interrupted upgrade
        recovered = self.upgrade_system.recover_interrupted_upgrade()
        assert recovered is not None
        
        # Restore from backup
        restore_path = self.temp_path / "restored.db"
        report = self.backup_system.restore_backup(
            backup_path=backup_path,
            target_path=restore_path,
            verify_integrity=True,
        )
        
        assert report.success is True
        assert restore_path.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
