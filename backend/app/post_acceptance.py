"""Offline-only post-acceptance services shared by A.E.G.I.S.-9 workflows."""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import os
import re
import uuid
from io import BytesIO
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def local_embedding(text: str, dimensions: int = 192) -> list[float]:
    size = min(max(dimensions, 32), 1024)
    values = [0.0] * size
    for token in re.findall(r"[a-z_][a-z0-9_.-]{1,63}", text.casefold()):
        digest = hashlib.sha256(token.encode()).digest()
        values[int.from_bytes(digest[:2], "big") % size] += 1 if digest[2] & 1 == 0 else -1
    magnitude = math.sqrt(sum(value * value for value in values)) or 1
    return [value / magnitude for value in values]


def semantic_similarity(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=False))


class EncryptedSemanticStore:
    MAGIC = b"AEGISIDX1"

    def __init__(self, path: Path, key: bytes) -> None:
        if len(key) != 32:
            raise ValueError("Semantic index encryption key must be 32 bytes.")
        self.path, self.key = path, key

    def save(self, records: list[dict[str, Any]]) -> None:
        if len(records) > 50_000:
            raise ValueError("Semantic index exceeds its record limit.")
        nonce = os.urandom(12)
        payload = json.dumps({"schemaVersion": 1, "records": records}, separators=(",", ":")).encode()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_bytes(self.MAGIC + nonce + AESGCM(self.key).encrypt(nonce, payload, self.MAGIC))

    def load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        value = self.path.read_bytes()
        if not value.startswith(self.MAGIC) or len(value) > 100_000_000:
            raise ValueError("Semantic index is invalid.")
        payload = json.loads(AESGCM(self.key).decrypt(value[9:21], value[21:], self.MAGIC))
        if payload.get("schemaVersion") != 1 or not isinstance(payload.get("records"), list) or len(payload["records"]) > 50_000:
            raise ValueError("Semantic index schema is invalid.")
        return payload["records"]

    def clear(self) -> None:
        self.path.unlink(missing_ok=True)


class ReviewHistoryStore:
    def __init__(self, path: Path, maximum: int = 5000) -> None:
        self.path, self.maximum = path, min(max(maximum, 10), 50_000)

    def append(self, summary: str, findings: int, validation: str, approved: bool) -> dict[str, Any]:
        record = {"id": str(uuid.uuid4()), "timestamp": datetime.now(timezone.utc).isoformat(), "summary": summary[:2000], "findings": max(findings, 0), "validation": validation[:2000], "approved": approved}
        records = (self.list(self.maximum) + [record])[-self.maximum:]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("".join(json.dumps(item) + "\n" for item in records), encoding="utf-8")
        return record

    def list(self, limit: int = 100) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        records = [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line]
        return records[-min(max(limit, 1), self.maximum):]


def scan_dependencies(files: dict[str, str]) -> list[dict[str, str]]:
    found: dict[str, dict[str, str]] = {}
    def add(ecosystem: str, name: str, version: str, license_name: str = "") -> None:
        if name and version:
            found[f"{ecosystem}:{name.casefold()}:{version}"] = {"ecosystem": ecosystem, "name": name, "version": version, **({"license": license_name} if license_name else {})}
    for name, content in files.items():
        if re.search(r"package(?:-lock)?\.json$", name, re.I):
            try:
                manifest = json.loads(content)
                for dependency, raw in manifest.get("dependencies", {}).items():
                    add("npm", dependency, raw if isinstance(raw, str) else raw.get("version", ""))
                for package_path, raw in manifest.get("packages", {}).items():
                    match = re.search(r"node_modules/(.+)$", package_path)
                    if match:
                        add("npm", match.group(1), raw.get("version", ""), raw.get("license", ""))
            except (json.JSONDecodeError, AttributeError):
                pass
        elif re.search(r"requirements[^/]*\.txt$", name, re.I):
            for dependency, version in re.findall(r"^([A-Za-z0-9_.-]+)==([^\s;]+)$", content, re.M):
                add("pypi", dependency, version)
        elif re.search(r"\.(?:csproj|props)$", name, re.I):
            for dependency, version in re.findall(r'<PackageReference\s+Include="([^"]+)"\s+Version="([^"]+)"[^>]*/?>', content, re.I):
                add("nuget", dependency, version)
    return sorted(found.values(), key=lambda item: (item["ecosystem"], item["name"].casefold()))


def create_cyclonedx(dependencies: list[dict[str, str]]) -> dict[str, Any]:
    components = []
    for item in dependencies:
        component = {"type": "library", "name": item["name"], "version": item["version"], "purl": f'pkg:{item["ecosystem"]}/{item["name"]}@{item["version"]}'}
        if item.get("license"):
            component["licenses"] = [{"license": {"id": item["license"]}}]
        components.append(component)
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1, "components": components}


def match_offline_vulnerabilities(dependencies: list[dict[str, str]], database: list[dict[str, str]]) -> list[dict[str, str]]:
    keys = {(item["ecosystem"], item["name"].casefold(), item["version"]) for item in dependencies}
    return [item for item in database if (item.get("ecosystem"), item.get("name", "").casefold(), item.get("version")) in keys]


def export_migration(path: Path, files: dict[str, str]) -> None:
    safe = {name: content for name, content in files.items() if _safe_name(name) and not re.search(r"secret|credential|token|(?:^|/)\.env", name, re.I)}
    payload = {"schemaVersion": 1, "createdAt": datetime.now(timezone.utc).isoformat(), "files": safe, "hashes": {name: hashlib.sha256(content.encode()).hexdigest() for name, content in safe.items()}}
    encoded = json.dumps(payload).encode()
    if len(encoded) > 100_000_000:
        raise ValueError("Migration bundle exceeds the uncompressed size limit.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(encoded))


def import_migration(path: Path) -> dict[str, Any]:
    with gzip.GzipFile(fileobj=BytesIO(path.read_bytes())) as archive:
        decoded = archive.read(100_000_001)
    if len(decoded) > 100_000_000:
        raise ValueError("Migration bundle exceeds the uncompressed size limit.")
    payload = json.loads(decoded)
    if payload.get("schemaVersion") != 1 or not isinstance(payload.get("files"), dict) or len(payload["files"]) > 1000:
        raise ValueError("Migration bundle schema is invalid.")
    for name, content in payload["files"].items():
        if not _safe_name(name) or hashlib.sha256(content.encode()).hexdigest() != payload.get("hashes", {}).get(name):
            raise ValueError("Migration bundle integrity validation failed.")
    return payload


def _safe_name(name: str) -> bool:
    value = PurePosixPath(name.replace("\\", "/"))
    return not value.is_absolute() and ".." not in value.parts
