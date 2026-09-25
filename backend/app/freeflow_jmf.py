from __future__ import annotations

import json
import threading
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx
from pydantic import BaseModel, Field

from app.config import Settings


JDF_NAMESPACE = "http://www.CIP4.org/JDFSchema_1_1"
XSI_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"
MAX_JMF_RESPONSE_BYTES = 1_048_576
ET.register_namespace("", JDF_NAMESPACE)
ET.register_namespace("xsi", XSI_NAMESPACE)


class FreeFlowJmfDevice(BaseModel):
    device_id: str = ""
    descriptive_name: str = ""
    device_type: str = ""
    device_class: str = ""
    model_description: str = ""
    kind: str = "device"
    status: str = ""
    attributes: dict[str, str] = Field(default_factory=dict)


class FreeFlowJmfServerResult(BaseModel):
    name: str
    role: str
    version: str = ""
    build: str = ""
    jmf_url: str = ""
    state: str
    detail: str
    http_status: int | None = None
    response_ms: int | None = None
    devices: list[FreeFlowJmfDevice] = Field(default_factory=list)


class FreeFlowJmfDiscovery(BaseModel):
    generated_at: str
    read_only: bool = True
    query: str = "KnownDevices"
    servers: list[FreeFlowJmfServerResult] = Field(default_factory=list)
    comparison: FreeFlowJmfComparison | None = None


class FreeFlowJmfComparison(BaseModel):
    state: str
    detail: str
    comparable: bool
    shared_device_count: int = 0
    primary_only_count: int = 0
    backup_only_count: int = 0
    primary_blank_id_count: int = 0
    backup_blank_id_count: int = 0
    primary_duplicate_id_count: int = 0
    backup_duplicate_id_count: int = 0


class FreeFlowJmfStatus(BaseModel):
    generated_at: str
    state: str
    detail: str
    primary_available: bool
    backup_available: bool
    servers: list[FreeFlowJmfServerResult] = Field(default_factory=list)


class FreeFlowJmfCapabilities(BaseModel):
    read_only: bool = True
    known_devices: bool = True
    workflows: bool = True
    queues: bool = True
    printers: bool = True
    job_enumeration: bool = True
    mutations: bool = False
    supported_queries: list[str] = Field(default_factory=lambda: ["KnownDevices", "KnownMessages", "QueueStatus"])
    detail: str = "KnownDevices and QueueStatus are enabled read-only. Mutations are not implemented."


class FreeFlowJmfJob(BaseModel):
    queue_entry_id: str = ""
    job_id: str = ""
    job_name: str = ""
    status: str = ""
    status_details: str = ""
    priority: str = ""
    submission_time: str = ""
    start_time: str = ""
    end_time: str = ""


class FreeFlowJmfMessage(BaseModel):
    """Represents a single JDF message type discovered via KnownMessages."""
    message_type: str = ""
    description: str = ""
    direction: str = ""  # "send", "receive", or "bidirectional"
    version: str = ""


class FreeFlowJmfMessages(BaseModel):
    """KnownMessages response for a single server."""
    generated_at: str
    name: str
    role: str
    version: str = ""
    state: str
    detail: str
    http_status: int | None = None
    response_ms: int | None = None
    messages: list[FreeFlowJmfMessage] = Field(default_factory=list)


class FreeFlowJmfServerJobs(BaseModel):
    name: str
    role: str
    version: str = ""
    state: str
    detail: str
    http_status: int | None = None
    response_ms: int | None = None
    jobs: list[FreeFlowJmfJob] = Field(default_factory=list)


class FreeFlowJmfJobs(BaseModel):
    generated_at: str
    supported: bool = True
    read_only: bool = True
    detail: str
    servers: list[FreeFlowJmfServerJobs] = Field(default_factory=list)


class FreeFlowJmfError(RuntimeError):
    pass


def compare_server_devices(servers: list[FreeFlowJmfServerResult]) -> FreeFlowJmfComparison:
    primary = next((server for server in servers if server.role.casefold() == "primary"), None)
    backup = next((server for server in servers if server.role.casefold() == "backup"), None)
    if primary is None or backup is None:
        return FreeFlowJmfComparison(
            state="unconfigured",
            detail="A primary and backup server are required for inventory comparison.",
            comparable=False,
        )
    if primary.state != "healthy" or backup.state != "healthy":
        return FreeFlowJmfComparison(
            state="partial",
            detail="Inventory comparison is unavailable until both servers return healthy KnownDevices results.",
            comparable=False,
        )

    def summarize(devices: list[FreeFlowJmfDevice]) -> tuple[set[str], int, int]:
        identifiers = [device.device_id.strip() for device in devices]
        nonblank = [identifier for identifier in identifiers if identifier]
        return set(nonblank), len(identifiers) - len(nonblank), len(nonblank) - len(set(nonblank))

    primary_ids, primary_blank, primary_duplicates = summarize(primary.devices)
    backup_ids, backup_blank, backup_duplicates = summarize(backup.devices)
    shared = len(primary_ids & backup_ids)
    primary_only = len(primary_ids - backup_ids)
    backup_only = len(backup_ids - primary_ids)
    drift = bool(primary_only or backup_only or primary_blank or backup_blank or primary_duplicates or backup_duplicates)
    return FreeFlowJmfComparison(
        state="drift" if drift else "matched",
        detail=(
            f"Compared device identities without retaining identifiers: {shared} shared, "
            f"{primary_only} primary-only, and {backup_only} backup-only."
        ),
        comparable=True,
        shared_device_count=shared,
        primary_only_count=primary_only,
        backup_only_count=backup_only,
        primary_blank_id_count=primary_blank,
        backup_blank_id_count=backup_blank,
        primary_duplicate_id_count=primary_duplicates,
        backup_duplicate_id_count=backup_duplicates,
    )


def build_known_devices_request() -> bytes:
    """Build KnownDevices query using the format confirmed working with FreeFlow Core.
    
    Working format (produces HTTP 200):
    - Root: <JMF> with xmlns="http://www.CIP4.org/JDFSchema_1_1"
    - Query with Type="KnownDevices" and xsi:type="QueryKnownDevices"
    - DeviceFilter DeviceDetails="Brief" inside Query
    """
    root = ET.Element(
        f"{{{JDF_NAMESPACE}}}JMF",
        {
            f"{{{XSI_NAMESPACE}}}type": "QueryKnownDevices",
            "MaxVersion": "1.6",
            "SenderID": "AEGIS9",
            "TimeStamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "Version": "1.6",
        },
    )
    query = ET.SubElement(
        root,
        f"{{{JDF_NAMESPACE}}}Query",
        {"ID": f"q-{uuid4().hex}", "Type": "KnownDevices"},
    )
    ET.SubElement(
        query,
        f"{{{JDF_NAMESPACE}}}DeviceFilter",
        {"DeviceDetails": "Brief"},
    )
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def build_known_messages_request() -> bytes:
    """Build KnownMessages query to discover supported JDF message types.
    
    KnownMessages returns a list of message types that the FreeFlow Core
    can send or receive, which helps identify supported capabilities.
    """
    root = ET.Element(
        f"{{{JDF_NAMESPACE}}}JMF",
        {
            f"{{{XSI_NAMESPACE}}}type": "QueryKnownMessages",
            "MaxVersion": "1.6",
            "SenderID": "AEGIS9",
            "TimeStamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "Version": "1.6",
        },
    )
    query = ET.SubElement(
        root,
        f"{{{JDF_NAMESPACE}}}Query",
        {"ID": f"q-{uuid4().hex}", "Type": "KnownMessages"},
    )
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def build_queue_status_request() -> bytes:
    root = ET.Element(
        f"{{{JDF_NAMESPACE}}}JMF",
        {
            "SenderID": "AEGIS9",
            "TimeStamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "Version": "1.3",
            "MaxVersion": "1.6",
        },
    )
    ET.SubElement(
        root,
        f"{{{JDF_NAMESPACE}}}Query",
        {"ID": f"q-{uuid4().hex}", "Type": "QueueStatus", f"{{{XSI_NAMESPACE}}}type": "QueryQueueStatus"},
    )
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def parse_known_messages(payload: bytes) -> list[FreeFlowJmfMessage]:
    """Parse KnownMessages response to extract supported JDF message types.
    
    KnownMessages returns a list of message types that FreeFlow Core supports.
    Each message type indicates a capability for JDF communication.
    
    The response contains MessageService elements with Type attributes.
    """
    if len(payload) > MAX_JMF_RESPONSE_BYTES:
        raise FreeFlowJmfError("FreeFlow JMF response exceeded the 1 MiB safety limit.")
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as error:
        raise FreeFlowJmfError("FreeFlow JMF returned malformed XML.") from error
    
    messages: list[FreeFlowJmfMessage] = []
    seen_types: set[str] = set()
    
    # Look for MessageService elements in the response
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] != "MessageService":
            continue
        
        attributes = {str(key): str(value) for key, value in element.attrib.items()}
        message_type = attributes.get("Type", "")
        
        # Avoid duplicates
        if not message_type or message_type in seen_types:
            continue
        seen_types.add(message_type)
        
        # Extract description from attributes if available
        description = attributes.get("Description", "")
        
        # Extract direction from attributes
        # Query=True means it can be queried, Command=True means it can be commanded
        direction = "bidirectional"
        if attributes.get("Query") == "true" and attributes.get("Command") == "false":
            direction = "receive"
        elif attributes.get("Query") == "false" and attributes.get("Command") == "true":
            direction = "send"
        
        # Extract version if available
        version = attributes.get("Version", "1.0")
        
        messages.append(FreeFlowJmfMessage(
            message_type=message_type,
            description=description,
            direction=direction,
            version=version,
        ))
    
    return messages


def parse_known_devices(payload: bytes) -> list[FreeFlowJmfDevice]:
    if len(payload) > MAX_JMF_RESPONSE_BYTES:
        raise FreeFlowJmfError("FreeFlow JMF response exceeded the 1 MiB safety limit.")
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as error:
        raise FreeFlowJmfError("FreeFlow JMF returned malformed XML.") from error
    devices: list[FreeFlowJmfDevice] = []
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] != "DeviceInfo":
            continue
        attributes = {str(key): str(value) for key, value in element.attrib.items()}
        device_attributes: dict[str, str] = {}
        for child in element:
            child_name = child.tag.rsplit("}", 1)[-1]
            if child_name == "Device":
                device_attributes = {str(key): str(value) for key, value in child.attrib.items()}
                attributes.update({f"Device.{key}": value for key, value in device_attributes.items()})
            elif child_name == "GeneralID":
                usage = str(child.attrib.get("IDUsage", "GeneralID"))
                attributes[f"GeneralID.{usage}"] = str(child.attrib.get("IDValue", ""))
        device_class = device_attributes.get("DeviceClass", attributes.get("DeviceClass", ""))
        kind = {
            "Preset": "workflow",
            "PrinterDestination": "queue",
            "PrintingPress": "printer",
            "Controller": "controller",
        }.get(device_class, "device")
        devices.append(
            FreeFlowJmfDevice(
                device_id=device_attributes.get("DeviceID", attributes.get("DeviceID", "")),
                descriptive_name=device_attributes.get("DescriptiveName", attributes.get("DescriptiveName", "")),
                device_type=device_attributes.get("DeviceType", attributes.get("DeviceType", "")),
                device_class=device_class,
                model_description=device_attributes.get("ModelDescription", ""),
                kind=kind,
                status=attributes.get("DeviceStatus", ""),
                attributes=attributes,
            )
        )
    return devices


def parse_queue_status(payload: bytes, limit: int = 200) -> list[FreeFlowJmfJob]:
    if len(payload) > MAX_JMF_RESPONSE_BYTES:
        raise FreeFlowJmfError("FreeFlow JMF response exceeded the 1 MiB safety limit.")
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as error:
        raise FreeFlowJmfError("FreeFlow JMF returned malformed XML.") from error
    response = next((element for element in root.iter() if element.tag.rsplit("}", 1)[-1] == "Response"), None)
    if response is None or response.attrib.get("ReturnCode") not in {None, "0"}:
        raise FreeFlowJmfError(f"FreeFlow rejected QueueStatus with JMF return code {response.attrib.get('ReturnCode', 'missing') if response is not None else 'missing'}.")
    jobs: list[FreeFlowJmfJob] = []
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] != "QueueEntry":
            continue
        attributes = element.attrib
        jobs.append(FreeFlowJmfJob(
            queue_entry_id=attributes.get("QueueEntryID", ""),
            job_id=attributes.get("JobID", ""),
            job_name=attributes.get("JobName", ""),
            status=attributes.get("Status", ""),
            status_details=attributes.get("StatusDetails", ""),
            priority=attributes.get("Priority", ""),
            submission_time=attributes.get("SubmissionTime", ""),
            start_time=attributes.get("StartTime", ""),
            end_time=attributes.get("EndTime", ""),
        ))
    jobs.sort(key=lambda job: (job.submission_time, job.queue_entry_id), reverse=True)
    return jobs[:limit]


class FreeFlowJmfService:
    def __init__(self, settings: Settings) -> None:
        self._inventory_path: Path = settings.freeflow_inventory_path
        self._timeout = settings.freeflow_timeout_seconds
        self._verify_tls = settings.freeflow_verify_tls
        self._cache: FreeFlowJmfDiscovery | None = None
        self._cache_time = 0.0
        self._cache_lock = threading.Lock()
        self._jobs_cache: FreeFlowJmfJobs | None = None
        self._jobs_cache_time = 0.0

    def discover(self, *, force: bool = False) -> FreeFlowJmfDiscovery:
        with self._cache_lock:
            if not force and self._cache is not None and time.monotonic() - self._cache_time < 30:
                return self._cache.model_copy(deep=True)
        generated_at = datetime.now(timezone.utc).isoformat()
        try:
            payload = json.loads(self._inventory_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            result = FreeFlowJmfDiscovery(
                generated_at=generated_at,
                servers=[FreeFlowJmfServerResult(name="Inventory", role="Configuration", state="unavailable", detail=f"FreeFlow inventory could not be loaded: {error}")],
            )
            self._set_cache(result)
            return result
        servers = [self._discover_server(item) for item in payload if isinstance(item, dict) and item.get("enabled", True)] if isinstance(payload, list) else []
        result = FreeFlowJmfDiscovery(
            generated_at=generated_at,
            servers=servers,
            comparison=compare_server_devices(servers),
        )
        self._set_cache(result)
        return result

    def filtered(self, kind: str) -> FreeFlowJmfDiscovery:
        result = self.discover()
        result.query = kind.capitalize()
        for server in result.servers:
            server.devices = [device for device in server.devices if device.kind == kind]
            server.detail = f"Returned {len(server.devices)} {kind}(s)." if server.state == "healthy" else server.detail
        return result

    def known_messages(self, *, force: bool = False) -> list[FreeFlowJmfMessages]:
        """Test KnownMessages capability on all configured FreeFlow servers.
        
        Returns a list of KnownMessages results, one per server.
        """
        generated_at = datetime.now(timezone.utc).isoformat()
        try:
            payload = json.loads(self._inventory_path.read_text(encoding="utf-8"))
        except (OSError, jsonDecodeError) as error:
            return [FreeFlowJmfMessages(
                generated_at=generated_at,
                name="Inventory",
                role="Configuration",
                state="unavailable",
                detail=f"FreeFlow inventory could not be loaded: {error}",
                messages=[],
            )]
        
        results: list[FreeFlowJmfMessages] = []
        for item in (payload if isinstance(payload, list) else []):
            if not isinstance(item, dict) or not item.get("enabled", True):
                continue
            
            name = str(item.get("name", "Unknown"))
            role = str(item.get("role", "FreeFlow Core"))
            version = str(item.get("version", ""))
            url = str(item.get("jmfUrl", "")).strip()
            
            if not url:
                results.append(FreeFlowJmfMessages(
                    generated_at=generated_at,
                    name=name,
                    role=role,
                    version=version,
                    state="unconfigured",
                    detail="JMF endpoint is not configured.",
                    messages=[],
                ))
                continue
            
            started = time.perf_counter()
            try:
                response = httpx.post(
                    url,
                    content=build_known_messages_request(),
                    headers={"Content-Type": "application/vnd.cip4-jmf+xml", "Accept": "application/vnd.cip4-jmf+xml, application/xml, text/xml"},
                    timeout=self._timeout,
                    verify=self._verify_tls,
                )
                elapsed = round((time.perf_counter() - started) * 1000)
                response.raise_for_status()
                messages = parse_known_messages(response.content)
                results.append(FreeFlowJmfMessages(
                    generated_at=generated_at,
                    name=name,
                    role=role,
                    version=version,
                    jmf_url=url,
                    state="healthy",
                    detail=f"KnownMessages returned {len(messages)} message type(s).",
                    http_status=response.status_code,
                    response_ms=elapsed,
                    messages=messages,
                ))
            except (httpx.HTTPError, FreeFlowJmfError) as error:
                elapsed = round((time.perf_counter() - started) * 1000)
                results.append(FreeFlowJmfMessages(
                    generated_at=generated_at,
                    name=name,
                    role=role,
                    version=version,
                    jmf_url=url,
                    state="error",
                    detail=str(error),
                    http_status=getattr(getattr(error, "response", None), "status_code", None),
                    response_ms=elapsed,
                    messages=[],
                ))
        
        return results

    def status(self) -> FreeFlowJmfStatus:
        result = self.discover()
        primary = next((server for server in result.servers if server.role.casefold() == "primary"), None)
        backup = next((server for server in result.servers if server.role.casefold() == "backup"), None)
        healthy_count = sum(server.state == "healthy" for server in result.servers)
        state = "healthy" if result.servers and healthy_count == len(result.servers) else "degraded" if healthy_count else "unavailable"
        return FreeFlowJmfStatus(
            generated_at=result.generated_at,
            state=state,
            detail=f"{healthy_count} of {len(result.servers)} configured FreeFlow JMF endpoints responded.",
            primary_available=primary is not None and primary.state == "healthy",
            backup_available=backup is not None and backup.state == "healthy",
            servers=result.servers,
        )

    def jobs(self, *, force: bool = False) -> FreeFlowJmfJobs:
        with self._cache_lock:
            if not force and self._jobs_cache is not None and time.monotonic() - self._jobs_cache_time < 30:
                return self._jobs_cache.model_copy(deep=True)
        generated_at = datetime.now(timezone.utc).isoformat()
        try:
            payload = json.loads(self._inventory_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            return FreeFlowJmfJobs(generated_at=generated_at, supported=True, detail=f"FreeFlow inventory could not be loaded: {error}")
        results = [self._jobs_for_server(item) for item in payload if isinstance(item, dict) and item.get("enabled", True)] if isinstance(payload, list) else []
        healthy_count = sum(server.state == "healthy" for server in results)
        result = FreeFlowJmfJobs(generated_at=generated_at, detail=f"QueueStatus responded on {healthy_count} of {len(results)} server(s); up to 200 newest entries per server are returned.", servers=results)
        with self._cache_lock:
            self._jobs_cache = result.model_copy(deep=True)
            self._jobs_cache_time = time.monotonic()
        return result

    def _jobs_for_server(self, item: dict) -> FreeFlowJmfServerJobs:
        name = str(item.get("name", "Unknown"))
        role = str(item.get("role", "FreeFlow Core"))
        version = str(item.get("version", ""))
        url = str(item.get("jmfUrl", "")).strip()
        if not url:
            return FreeFlowJmfServerJobs(name=name, role=role, version=version, state="unconfigured", detail="JMF endpoint is not configured.")
        started = time.perf_counter()
        try:
            response = httpx.post(url, content=build_queue_status_request(), headers={"Content-Type": "application/vnd.cip4-jmf+xml", "Accept": "application/vnd.cip4-jmf+xml, application/xml, text/xml"}, timeout=self._timeout, verify=self._verify_tls)
            elapsed = round((time.perf_counter() - started) * 1000)
            response.raise_for_status()
            jobs = parse_queue_status(response.content)
            return FreeFlowJmfServerJobs(name=name, role=role, version=version, state="healthy", detail=f"Returned {len(jobs)} recent queue entries.", http_status=response.status_code, response_ms=elapsed, jobs=jobs)
        except (httpx.HTTPError, FreeFlowJmfError) as error:
            return FreeFlowJmfServerJobs(name=name, role=role, version=version, state="error", detail=str(error), http_status=getattr(getattr(error, "response", None), "status_code", None), response_ms=round((time.perf_counter() - started) * 1000))

    def _set_cache(self, result: FreeFlowJmfDiscovery) -> None:
        with self._cache_lock:
            self._cache = result.model_copy(deep=True)
            self._cache_time = time.monotonic()

    def _discover_server(self, item: dict) -> FreeFlowJmfServerResult:
        name = str(item.get("name", "Unknown"))
        role = str(item.get("role", "FreeFlow Core"))
        version = str(item.get("version", ""))
        build = str(item.get("build", ""))
        url = str(item.get("jmfUrl", "")).strip()
        if not url:
            return FreeFlowJmfServerResult(name=name, role=role, version=version, build=build, state="unconfigured", detail="JMF endpoint is not configured.")
        started = time.perf_counter()
        try:
            response = httpx.post(
                url,
                content=build_known_devices_request(),
                headers={"Content-Type": "application/vnd.cip4-jmf+xml", "Accept": "application/vnd.cip4-jmf+xml, application/xml, text/xml"},
                timeout=self._timeout,
                verify=self._verify_tls,
            )
            elapsed = round((time.perf_counter() - started) * 1000)
            response.raise_for_status()
            devices = parse_known_devices(response.content)
            return FreeFlowJmfServerResult(name=name, role=role, version=version, build=build, jmf_url=url, state="healthy", detail=f"KnownDevices returned {len(devices)} device(s).", http_status=response.status_code, response_ms=elapsed, devices=devices)
        except (httpx.HTTPError, FreeFlowJmfError) as error:
            return FreeFlowJmfServerResult(name=name, role=role, version=version, build=build, jmf_url=url, state="error", detail=str(error), http_status=getattr(getattr(error, "response", None), "status_code", None), response_ms=round((time.perf_counter() - started) * 1000))
