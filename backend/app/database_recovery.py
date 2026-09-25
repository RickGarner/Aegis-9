"""Database backup and restore with integrity verification and schema validation."""
from __future__ import annotations

import gzip
import hashlib
import json
import sqlite3
import tempfile
import zlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


@dataclass
class BackupMetadata:
    """Metadata for a database backup."""
    backup_id: str
    database_path: str
    created_at: str
    schema_version: int
    record_counts: dict[str, int]
    database_size_bytes: int
    checksum: str
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "backup_id": self.backup_id,
            "database_path": self.database_path,
            "created_at": self.created_at,
            "schema_version": self.schema_version,
            "record_counts": self.record_counts,
            "database_size_bytes": self.database_size_bytes,
            "checksum": self.checksum,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BackupMetadata":
        """Deserialize from dictionary."""
        return cls(
            backup_id=data["backup_id"],
            database_path=data["database_path"],
            created_at=data["created_at"],
            schema_version=data["schema_version"],
            record_counts=data["record_counts"],
            database_size_bytes=data["database_size_bytes"],
            checksum=data["checksum"],
            metadata=data.get("metadata", {}),
        )


@dataclass
class RestoreReport:
    """Report from database restore operation."""
    success: bool
    backup_id: str
    target_path: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    restored_tables: list[str] = field(default_factory=list)
    record_counts: dict[str, int] = field(default_factory=dict)
    restore_time_ms: float = 0.0
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "success": self.success,
            "backup_id": self.backup_id,
            "target_path": self.target_path,
            "errors": self.errors,
            "warnings": self.warnings,
            "restored_tables": self.restored_tables,
            "record_counts": self.record_counts,
            "restore_time_ms": self.restore_time_ms,
        }


class DatabaseBackupSystem:
    """Manages database backup and restore operations."""
    
    # Tables to exclude from backup (temporary/internal tables)
    EXCLUDED_TABLES = [
        "sqlite_sequence",
    ]
    
    def __init__(self, backup_root: Path):
        self.backup_root = backup_root
        self.backup_root.mkdir(parents=True, exist_ok=True)
        self._backup_index: dict[str, BackupMetadata] = {}
        self._load_backup_index()
    
    def _load_backup_index(self) -> None:
        """Load backup index from storage."""
        index_path = self.backup_root / "backup-index.json"
        if index_path.exists():
            try:
                data = json.loads(index_path.read_text())
                for backup_data in data.get("backups", []):
                    metadata = BackupMetadata.from_dict(backup_data)
                    self._backup_index[metadata.backup_id] = metadata
            except (json.JSONDecodeError, KeyError):
                self._backup_index = {}
    
    def _save_backup_index(self) -> None:
        """Save backup index to storage."""
        index_path = self.backup_root / "backup-index.json"
        data = {
            "backups": [m.to_dict() for m in self._backup_index.values()],
        }
        index_path.write_text(json.dumps(data, indent=2))
    
    def _get_schema_version(self, db_path: Path) -> int:
        """Get the schema version from the database."""
        try:
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.execute(
                    "SELECT value FROM metadata WHERE key = 'schema_version'"
                )
                row = cursor.fetchone()
                return row[0] if row else 1
        except sqlite3.OperationalError:
            return 1
    
    def _get_record_counts(self, db_path: Path) -> dict[str, int]:
        """Get record counts for all tables."""
        counts = {}
        try:
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
                tables = [row[0] for row in cursor.fetchall() 
                         if row[0] not in self.EXCLUDED_TABLES]
                
                for table in tables:
                    cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                    counts[table] = cursor.fetchone()[0]
        except sqlite3.Error:
            pass
        
        return counts
    
    def create_backup(
        self,
        database_path: Path,
        backup_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[str, BackupMetadata]:
        """
        Create a backup of the database.
        
        Returns:
            Tuple of (backup_path, metadata)
        """
        import time
        
        if not database_path.exists():
            raise ValueError(f"Database not found: {database_path}")
        
        backup_id = backup_id or f"backup-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        backup_path = self.backup_root / f"{backup_id}.db.gz"
        
        # Read database
        db_content = database_path.read_bytes()
        database_size = len(db_content)
        
        # Compute checksum
        checksum = hashlib.sha256(db_content).hexdigest()
        
        # Compress and write
        compressed = gzip.compress(db_content, compresslevel=9)
        backup_path.write_bytes(compressed)
        
        # Get metadata
        schema_version = self._get_schema_version(database_path)
        record_counts = self._get_record_counts(database_path)
        
        # Create metadata
        backup_metadata = BackupMetadata(
            backup_id=backup_id,
            database_path=str(database_path),
            created_at=datetime.now(timezone.utc).isoformat(),
            schema_version=schema_version,
            record_counts=record_counts,
            database_size_bytes=database_size,
            checksum=checksum,
            metadata=metadata or {},
        )
        
        # Save metadata
        self._backup_index[backup_id] = backup_metadata
        self._save_backup_index()
        
        return str(backup_path), backup_metadata
    
    def restore_backup(
        self,
        backup_path: str | Path,
        target_path: Path,
        verify_integrity: bool = True,
    ) -> RestoreReport:
        """
        Restore a database from backup.
        
        Args:
            backup_path: Path to the backup file (.db.gz)
            target_path: Path to restore the database to
            verify_integrity: Whether to verify backup integrity before restore
        
        Returns:
            RestoreReport with details of the operation
        """
        import time
        start_time = time.time()
        
        report = RestoreReport(
            success=True,
            backup_id="",
            target_path=str(target_path),
        )
        
        backup_path = Path(backup_path)
        if not backup_path.exists():
            report.success = False
            report.errors.append(f"Backup file not found: {backup_path}")
            return report
        
        # Load backup metadata
        backup_id = backup_path.stem
        metadata = self._backup_index.get(backup_id)
        if metadata:
            report.backup_id = backup_id
        
        # Verify integrity
        if verify_integrity and metadata:
            compressed = backup_path.read_bytes()
            decompressed = gzip.decompress(compressed)
            actual_checksum = hashlib.sha256(decompressed).hexdigest()
            
            if actual_checksum != metadata.checksum:
                report.success = False
                report.errors.append("Backup integrity verification failed")
                return report
        
        # Decompress and restore
        try:
            compressed = backup_path.read_bytes()
            decompressed = gzip.decompress(compressed)
            
            # Ensure target directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write restored database
            target_path.write_bytes(decompressed)
            
            # Get restored record counts
            report.record_counts = self._get_record_counts(target_path)
            report.restored_tables = list(report.record_counts.keys())
            
        except (gzip.BadGzipFile, OSError) as e:
            report.success = False
            report.errors.append(f"Failed to decompress backup: {e}")
        except Exception as e:
            report.success = False
            report.errors.append(f"Failed to restore database: {e}")
        
        report.restore_time_ms = (time.time() - start_time) * 1000
        
        return report
    
    def list_backups(self) -> list[dict[str, Any]]:
        """List all available backups."""
        return [
            {
                "backup_id": m.backup_id,
                "created_at": m.created_at,
                "schema_version": m.schema_version,
                "database_size_bytes": m.database_size_bytes,
                "record_counts": m.record_counts,
            }
            for m in self._backup_index.values()
        ]
    
    def get_backup(self, backup_id: str) -> BackupMetadata | None:
        """Get backup metadata by ID."""
        return self._backup_index.get(backup_id)
    
    def delete_backup(self, backup_id: str) -> bool:
        """Delete a backup and its metadata."""
        backup_path = self.backup_root / f"{backup_id}.db.gz"
        if backup_path.exists():
            backup_path.unlink()
        
        if backup_id in self._backup_index:
            del self._backup_index[backup_id]
            self._save_backup_index()
            return True
        
        return False
    
    def validate_backup(self, backup_id: str) -> tuple[bool, list[str]]:
        """
        Validate a backup's integrity.
        
        Returns:
            Tuple of (is_valid, errors)
        """
        errors = []
        backup_path = self.backup_root / f"{backup_id}.db.gz"
        
        if not backup_path.exists():
            return False, [f"Backup file not found: {backup_path}"]
        
        metadata = self._backup_index.get(backup_id)
        if not metadata:
            return False, ["Backup metadata not found"]
        
        try:
            compressed = backup_path.read_bytes()
            decompressed = gzip.decompress(compressed)
            actual_checksum = hashlib.sha256(decompressed).hexdigest()
            
            if actual_checksum != metadata.checksum:
                errors.append("Checksum mismatch")
            
            # Try to open as SQLite database
            # Write to temp file since sqlite3.connect() doesn't accept BytesIO on Windows
            import tempfile
            import os
            with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
                f.write(decompressed)
                temp_db_path = f.name
            
            try:
                conn = sqlite3.connect(temp_db_path)
                try:
                    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = [row[0] for row in cursor.fetchall()]
                    
                    if not tables:
                        errors.append("No tables found in database")
                finally:
                    conn.close()
            finally:
                os.unlink(temp_db_path)
        
        except gzip.BadGzipFile as e:
            errors.append(f"Invalid gzip file: {e}")
        except sqlite3.DatabaseError as e:
            errors.append(f"Invalid SQLite database: {e}")
        except Exception as e:
            errors.append(f"Validation failed: {e}")
        
        return len(errors) == 0, errors


class UpgradeRecoverySystem:
    """Manages interrupted upgrade recovery with state machine."""
    
    def __init__(self, state_path: Path):
        self.state_path = state_path
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state: UpgradeState | None = None
        self._load_state()
    
    def _load_state(self) -> None:
        """Load current upgrade state."""
        state_file = self.state_path / "upgrade-state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                self._state = UpgradeState.from_dict(data)
            except (json.JSONDecodeError, KeyError):
                self._state = None
    
    def _save_state(self) -> None:
        """Save current upgrade state."""
        if self._state:
            state_file = self.state_path / "upgrade-state.json"
            state_file.write_text(json.dumps(self._state.to_dict(), indent=2))
    
    def begin_upgrade(
        self,
        upgrade_id: str,
        source_database: Path,
        target_database: Path,
        schema_version_from: int,
        schema_version_to: int,
    ) -> UpgradeState:
        """Begin a new upgrade operation."""
        self._state = UpgradeState(
            upgrade_id=upgrade_id,
            status=UpgradeStatus.INITIALIZING,
            source_database=str(source_database),
            target_database=str(target_database),
            schema_version_from=schema_version_from,
            schema_version_to=schema_version_to,
            started_at=datetime.now(timezone.utc).isoformat(),
            progress_percent=0,
            last_action="Upgrade initialized",
            rollback_available=False,
        )
        self._save_state()
        return self._state
    
    def update_progress(
        self,
        progress_percent: int,
        action: str,
        error: str | None = None,
    ) -> UpgradeState:
        """Update upgrade progress."""
        if not self._state:
            raise ValueError("No upgrade in progress")
        
        self._state.progress_percent = progress_percent
        self._state.last_action = action
        self._state.last_error = error
        self._state.updated_at = datetime.now(timezone.utc).isoformat()
        
        if progress_percent >= 100:
            self._state.status = UpgradeStatus.COMPLETED
        elif error:
            self._state.status = UpgradeStatus.FAILED
        
        self._save_state()
        return self._state
    
    def mark_rollback_available(self, rollback_path: Path) -> UpgradeState:
        """Mark that a rollback is available."""
        if not self._state:
            raise ValueError("No upgrade in progress")
        
        self._state.rollback_path = str(rollback_path)
        self._state.rollback_available = True
        self._save_state()
        return self._state
    
    def recover_interrupted_upgrade(self) -> UpgradeState | None:
        """
        Recover from an interrupted upgrade.
        
        Returns:
            UpgradeState if recovery is possible, None otherwise
        """
        if not self._state:
            return None
        
        if self._state.status not in {
            UpgradeStatus.INITIALIZING,
            UpgradeStatus.IN_PROGRESS,
            UpgradeStatus.FAILED,
        }:
            return None
        
        # Check if rollback is available
        if not self._state.rollback_available:
            return None
        
        # Return state for manual recovery
        return self._state
    
    def get_current_state(self) -> UpgradeState | None:
        """Get the current upgrade state."""
        return self._state
    
    def clear_state(self) -> None:
        """Clear the current upgrade state."""
        self._state = None
        self._save_state()


@dataclass
class UpgradeState:
    """State of an upgrade operation."""
    upgrade_id: str
    status: UpgradeStatus
    source_database: str
    target_database: str
    schema_version_from: int
    schema_version_to: int
    started_at: str
    progress_percent: int
    last_action: str
    last_error: str | None = None
    rollback_path: str | None = None
    rollback_available: bool = False
    completed_at: str | None = None
    updated_at: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "upgrade_id": self.upgrade_id,
            "status": self.status.value,
            "source_database": self.source_database,
            "target_database": self.target_database,
            "schema_version_from": self.schema_version_from,
            "schema_version_to": self.schema_version_to,
            "started_at": self.started_at,
            "progress_percent": self.progress_percent,
            "last_action": self.last_action,
            "last_error": self.last_error,
            "rollback_path": self.rollback_path,
            "rollback_available": self.rollback_available,
            "completed_at": self.completed_at,
            "updated_at": self.updated_at,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UpgradeState":
        """Deserialize from dictionary."""
        return cls(
            upgrade_id=data["upgrade_id"],
            status=UpgradeStatus(data["status"]),
            source_database=data["source_database"],
            target_database=data["target_database"],
            schema_version_from=data["schema_version_from"],
            schema_version_to=data["schema_version_to"],
            started_at=data["started_at"],
            progress_percent=data["progress_percent"],
            last_action=data["last_action"],
            last_error=data.get("last_error"),
            rollback_path=data.get("rollback_path"),
            rollback_available=data.get("rollback_available", False),
            completed_at=data.get("completed_at"),
            updated_at=data.get("updated_at"),
        )


class UpgradeStatus(Enum):
    """Upgrade operation status."""
    INITIALIZING = "initializing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLBACK_PENDING = "rollback_pending"
    ROLLBACK_COMPLETED = "rollback_completed"


_default_backup_system: DatabaseBackupSystem | None = None
_default_upgrade_system: UpgradeRecoverySystem | None = None


def get_database_backup_system(backup_root: Path | None = None) -> DatabaseBackupSystem:
    """Get the global database backup system instance."""
    global _default_backup_system
    if _default_backup_system is None:
        if backup_root is None:
            backup_root = Path(__file__).resolve().parents[2] / "storage" / "backups"
        _default_backup_system = DatabaseBackupSystem(backup_root)
    return _default_backup_system


def get_upgrade_recovery_system(state_path: Path | None = None) -> UpgradeRecoverySystem:
    """Get the global upgrade recovery system instance."""
    global _default_upgrade_system
    if _default_upgrade_system is None:
        if state_path is None:
            state_path = Path(__file__).resolve().parents[2] / "storage" / "upgrade-state"
        _default_upgrade_system = UpgradeRecoverySystem(state_path)
    return _default_upgrade_system
