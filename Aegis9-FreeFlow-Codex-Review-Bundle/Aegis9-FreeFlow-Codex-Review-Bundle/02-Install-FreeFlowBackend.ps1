[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$RepoPath,
    [switch]$Apply,
    [switch]$ForceReplace
)

. (Join-Path $PSScriptRoot "Aegis9-FreeFlow.Common.ps1")

$repo = Resolve-AegisRepoPath -RepoPath $RepoPath
$appDir = Get-AegisBackendAppDir -RepoPath $repo
$target = Join-Path $appDir "integrations\freeflow"

Write-AegisStep ($(if ($Apply) { "Installing backend FreeFlow module" } else { "Dry-run: backend FreeFlow module" }))
Write-Host "Target: $target"

$files = @{}

$files["__init__.py"] = @'
# AEGIS_FREEFLOW_GENERATED_V1
"""AEGIS 9 Xerox FreeFlow Core integration."""
'@

$files["config.py"] = @'
# AEGIS_FREEFLOW_GENERATED_V1
from __future__ import annotations

from dataclasses import dataclass
import os


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class FreeFlowSettings:
    enabled: bool
    base_url: str
    timeout_seconds: float
    verify_tls: bool
    enable_status_query: bool
    allow_mutations: bool

    @classmethod
    def from_env(cls) -> "FreeFlowSettings":
        return cls(
            enabled=_env_bool("AEGIS_FREEFLOW_ENABLED", False),
            base_url=os.getenv(
                "AEGIS_FREEFLOW_BASE_URL",
                "http://localhost:7751/FreeFlowCore",
            ).rstrip("/"),
            timeout_seconds=float(os.getenv("AEGIS_FREEFLOW_TIMEOUT_SECONDS", "10")),
            verify_tls=_env_bool("AEGIS_FREEFLOW_VERIFY_TLS", True),
            # Status/QueueInfo is intentionally disabled until the installed
            # FreeFlow Core SDK/version is validated by Codex/operations.
            enable_status_query=_env_bool("AEGIS_FREEFLOW_ENABLE_STATUS_QUERY", False),
            # Mutations are intentionally disabled in v1.
            allow_mutations=_env_bool("AEGIS_FREEFLOW_ALLOW_MUTATIONS", False),
        )
'@

$files["models.py"] = @'
# AEGIS_FREEFLOW_GENERATED_V1
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class FreeFlowDevice:
    device_id: str | None = None
    descriptive_name: str | None = None
    device_type: str | None = None
    device_class: str | None = None
    status: str | None = None
    attributes: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FreeFlowQueueEntry:
    queue_entry_id: str | None = None
    job_id: str | None = None
    job_name: str | None = None
    status: str | None = None
    device_id: str | None = None
    attributes: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
'@

$files["jmf.py"] = @'
# AEGIS_FREEFLOW_GENERATED_V1
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import ssl
from typing import Iterable
from urllib import request
from uuid import uuid4
import xml.etree.ElementTree as ET

from .config import FreeFlowSettings
from .models import FreeFlowDevice, FreeFlowQueueEntry


JDF_NS = "http://www.CIP4.org/JDFSchema_1_1"
ET.register_namespace("", JDF_NS)


class FreeFlowJmfError(RuntimeError):
    pass


@dataclass
class JmfResponse:
    status_code: int
    body: str


def _q(tag: str) -> str:
    return f"{{{JDF_NS}}}{tag}"


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class FreeFlowJmfClient:
    """Small read-only JMF client.

    Xerox publicly documents KnownDevices against the FreeFlow Core JMF gateway.
    The optional Status/QueueInfo query is feature-flagged because exact support
    must be validated against the installed FreeFlow Core SDK/version.
    """

    def __init__(self, settings: FreeFlowSettings):
        self.settings = settings

    def _post(self, xml_text: str) -> JmfResponse:
        data = xml_text.encode("utf-8")
        req = request.Request(
            self.settings.base_url,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/vnd.cip4-jmf+xml",
                "Accept": "application/vnd.cip4-jmf+xml, application/xml, text/xml",
                "User-Agent": "AEGIS9-FreeFlow/1.0",
            },
        )

        context = None
        if self.settings.base_url.lower().startswith("https://"):
            context = ssl.create_default_context()
            if not self.settings.verify_tls:
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE

        try:
            with request.urlopen(
                req,
                timeout=self.settings.timeout_seconds,
                context=context,
            ) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                return JmfResponse(status_code=int(resp.status), body=body)
        except Exception as exc:
            raise FreeFlowJmfError(
                f"FreeFlow JMF request failed for {self.settings.base_url}: {exc}"
            ) from exc

    def build_known_devices(self) -> str:
        root = ET.Element(
            _q("JMF"),
            {
                "SenderID": "AEGIS9",
                "TimeStamp": _timestamp(),
                "Version": "1.3",
            },
        )
        ET.SubElement(
            root,
            _q("Query"),
            {
                "ID": f"AEGIS-{uuid4().hex}",
                "Type": "KnownDevices",
            },
        )
        return ET.tostring(root, encoding="unicode", xml_declaration=True)

    def known_devices_raw(self) -> JmfResponse:
        return self._post(self.build_known_devices())

    def known_devices(self) -> list[FreeFlowDevice]:
        response = self.known_devices_raw()
        return parse_known_devices(response.body)

    def build_status_queue_info(self) -> str:
        if not self.settings.enable_status_query:
            raise FreeFlowJmfError(
                "Status/QueueInfo job enumeration is disabled. "
                "Set AEGIS_FREEFLOW_ENABLE_STATUS_QUERY=true only after SDK validation."
            )

        root = ET.Element(
            _q("JMF"),
            {
                "SenderID": "AEGIS9",
                "TimeStamp": _timestamp(),
                "Version": "1.3",
            },
        )
        query = ET.SubElement(
            root,
            _q("Query"),
            {
                "ID": f"AEGIS-{uuid4().hex}",
                "Type": "Status",
            },
        )
        ET.SubElement(query, _q("StatusQuParams"), {"QueueInfo": "true"})
        return ET.tostring(root, encoding="unicode", xml_declaration=True)

    def queue_entries(self) -> list[FreeFlowQueueEntry]:
        response = self._post(self.build_status_queue_info())
        return parse_queue_entries(response.body)


def _iter_by_local_name(root: ET.Element, names: Iterable[str]):
    wanted = set(names)
    for elem in root.iter():
        local = elem.tag.rsplit("}", 1)[-1]
        if local in wanted:
            yield elem


def parse_known_devices(xml_text: str) -> list[FreeFlowDevice]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise FreeFlowJmfError(f"Invalid JMF XML returned by FreeFlow Core: {exc}") from exc

    devices: list[FreeFlowDevice] = []
    seen: set[tuple[str | None, str | None]] = set()

    # DeviceInfo is defined by JMF. Some implementations expose useful
    # workflow/queue identity on Device or nested elements, so both are accepted.
    for elem in _iter_by_local_name(root, {"DeviceInfo", "Device"}):
        attrs = {str(k): str(v) for k, v in elem.attrib.items()}
        device_id = (
            attrs.get("DeviceID")
            or attrs.get("ID")
            or attrs.get("DeviceIdentifier")
        )
        name = (
            attrs.get("DescriptiveName")
            or attrs.get("DeviceName")
            or attrs.get("Name")
        )
        key = (device_id, name)
        if key in seen:
            continue
        seen.add(key)

        devices.append(
            FreeFlowDevice(
                device_id=device_id,
                descriptive_name=name,
                device_type=attrs.get("DeviceType"),
                device_class=attrs.get("DeviceClass"),
                status=attrs.get("DeviceStatus") or attrs.get("Status"),
                attributes=attrs,
            )
        )

    return devices


def parse_queue_entries(xml_text: str) -> list[FreeFlowQueueEntry]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise FreeFlowJmfError(f"Invalid JMF XML returned by FreeFlow Core: {exc}") from exc

    entries: list[FreeFlowQueueEntry] = []
    for elem in _iter_by_local_name(root, {"QueueEntry"}):
        attrs = {str(k): str(v) for k, v in elem.attrib.items()}
        entries.append(
            FreeFlowQueueEntry(
                queue_entry_id=attrs.get("QueueEntryID") or attrs.get("ID"),
                job_id=attrs.get("JobID"),
                job_name=attrs.get("JobName") or attrs.get("DescriptiveName"),
                status=attrs.get("QueueEntryStatus") or attrs.get("Status"),
                device_id=attrs.get("DeviceID"),
                attributes=attrs,
            )
        )
    return entries
'@

$files["service.py"] = @'
# AEGIS_FREEFLOW_GENERATED_V1
from __future__ import annotations

from time import perf_counter
from typing import Any

from .config import FreeFlowSettings
from .jmf import FreeFlowJmfClient, FreeFlowJmfError


class FreeFlowService:
    def __init__(self, settings: FreeFlowSettings | None = None):
        self.settings = settings or FreeFlowSettings.from_env()
        self.client = FreeFlowJmfClient(self.settings)

    def status(self) -> dict[str, Any]:
        base = {
            "enabled": self.settings.enabled,
            "base_url": self.settings.base_url,
            "status_query_enabled": self.settings.enable_status_query,
            "mutations_enabled": self.settings.allow_mutations,
        }
        if not self.settings.enabled:
            return {**base, "healthy": False, "state": "disabled"}

        started = perf_counter()
        try:
            devices = self.client.known_devices()
            latency_ms = round((perf_counter() - started) * 1000, 1)
            return {
                **base,
                "healthy": True,
                "state": "healthy",
                "latency_ms": latency_ms,
                "device_count": len(devices),
            }
        except Exception as exc:
            latency_ms = round((perf_counter() - started) * 1000, 1)
            return {
                **base,
                "healthy": False,
                "state": "unavailable",
                "latency_ms": latency_ms,
                "error": str(exc),
            }

    def devices(self) -> list[dict[str, Any]]:
        return [d.to_dict() for d in self.client.known_devices()]

    def workflows(self) -> list[dict[str, Any]]:
        # Xerox documents KnownDevices as the discovery query for workflows and
        # queues. Exact response attributes are version-dependent. Until the
        # installed SDK is validated, retain all fields and use a conservative
        # heuristic rather than discarding unknown devices.
        items = self.devices()
        result = []
        for item in items:
            blob = " ".join(
                str(item.get(k) or "") for k in ("device_type", "device_class", "descriptive_name")
            ).lower()
            if "workflow" in blob or "routingworkflow" in blob:
                result.append(item)
        return result

    def queues(self) -> list[dict[str, Any]]:
        items = self.devices()
        result = []
        for item in items:
            blob = " ".join(
                str(item.get(k) or "") for k in ("device_type", "device_class", "descriptive_name")
            ).lower()
            if "queue" in blob:
                result.append(item)
        return result

    def jobs(self) -> dict[str, Any]:
        if not self.settings.enable_status_query:
            return {
                "supported": False,
                "reason": (
                    "JMF Status/QueueInfo enumeration is disabled pending validation "
                    "against the installed FreeFlow Core SDK/version."
                ),
                "jobs": [],
            }
        try:
            jobs = [x.to_dict() for x in self.client.queue_entries()]
            return {"supported": True, "jobs": jobs}
        except FreeFlowJmfError as exc:
            return {"supported": False, "reason": str(exc), "jobs": []}
'@

$files["api.py"] = @'
# AEGIS_FREEFLOW_GENERATED_V1
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .config import FreeFlowSettings
from .service import FreeFlowService


router = APIRouter(prefix="/api/integrations/freeflow", tags=["FreeFlow Core"])


def _service() -> FreeFlowService:
    return FreeFlowService(FreeFlowSettings.from_env())


def _require_enabled(service: FreeFlowService) -> None:
    if not service.settings.enabled:
        raise HTTPException(
            status_code=503,
            detail="FreeFlow Core integration is disabled.",
        )


@router.get("/status")
def get_status():
    return _service().status()


@router.get("/devices")
def get_devices():
    service = _service()
    _require_enabled(service)
    return {"devices": service.devices()}


@router.get("/workflows")
def get_workflows():
    service = _service()
    _require_enabled(service)
    return {"workflows": service.workflows()}


@router.get("/queues")
def get_queues():
    service = _service()
    _require_enabled(service)
    return {"queues": service.queues()}


@router.get("/jobs")
def get_jobs():
    service = _service()
    _require_enabled(service)
    return service.jobs()


@router.get("/capabilities")
def get_capabilities():
    service = _service()
    return {
        "known_devices": True,
        "workflow_discovery": True,
        "queue_discovery": True,
        "status_queue_info": service.settings.enable_status_query,
        "job_mutations": False,
        "printer_snmp": False,
        "printer_ipp": False,
        "notes": [
            "KnownDevices is the vendor-documented initial discovery capability.",
            "Status/QueueInfo remains feature-flagged pending installed-SDK validation.",
            "Mutating JMF commands are intentionally not implemented in v1.",
        ],
    }
'@

$files["test_jmf.py"] = @'
# AEGIS_FREEFLOW_GENERATED_V1
from __future__ import annotations

import unittest

from .config import FreeFlowSettings
from .jmf import FreeFlowJmfClient, parse_known_devices, parse_queue_entries


class FreeFlowJmfTests(unittest.TestCase):
    def _settings(self, status: bool = False):
        return FreeFlowSettings(
            enabled=True,
            base_url="http://example.invalid:7751/FreeFlowCore",
            timeout_seconds=1.0,
            verify_tls=True,
            enable_status_query=status,
            allow_mutations=False,
        )

    def test_known_devices_request(self):
        xml = FreeFlowJmfClient(self._settings()).build_known_devices()
        self.assertIn('Type="KnownDevices"', xml)
        self.assertIn("AEGIS9", xml)

    def test_parse_device_info(self):
        xml = """<?xml version="1.0"?>
        <JMF xmlns="http://www.CIP4.org/JDFSchema_1_1">
          <Response Type="KnownDevices">
            <DeviceInfo DeviceID="WF1" DescriptiveName="Production Workflow" DeviceStatus="Running"/>
          </Response>
        </JMF>"""
        devices = parse_known_devices(xml)
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0].device_id, "WF1")

    def test_parse_queue_entry(self):
        xml = """<?xml version="1.0"?>
        <JMF xmlns="http://www.CIP4.org/JDFSchema_1_1">
          <Response Type="Status">
            <QueueEntry QueueEntryID="QE1" JobID="J1" JobName="Test.pdf" QueueEntryStatus="Waiting"/>
          </Response>
        </JMF>"""
        jobs = parse_queue_entries(xml)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].job_id, "J1")


if __name__ == "__main__":
    unittest.main()
'@

foreach ($entry in $files.GetEnumerator()) {
    $path = Join-Path $target $entry.Key
    Write-AegisGeneratedFile -RepoPath $repo -Path $path -Content $entry.Value -Apply:$Apply -ForceReplace:$ForceReplace
}

if (-not $Apply) {
    Write-AegisWarn "No files were modified. Codex should review this dry-run and generated module design before Apply mode."
} else {
    Write-AegisOk "Backend module installed. It is not active until the registration and configuration scripts are applied."
}
