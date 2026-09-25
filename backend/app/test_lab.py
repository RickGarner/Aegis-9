"""Fail-closed planning and packaging for disposable A.E.G.I.S. Test Lab runs."""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape


RULES = (
    ("critical", "destructive-filesystem", r"\b(?:Remove-Item|rm\s+-r|Directory\.Delete|File\.Delete)\b", "Use only copied synthetic files in a disposable sandbox."),
    ("critical", "remote-execution", r"\b(?:Invoke-Command|Enter-PSSession|New-PSSession|Process\.Start)\b", "Block production credentials and all network access."),
    ("high", "system-mutation", r"\b(?:Set-ItemProperty|New-Service|Stop-Service|Restart-Service|Register-ScheduledTask|schtasks)\b", "Mock the operation or use a disposable VM."),
    ("high", "network", r"\b(?:Invoke-WebRequest|Invoke-RestMethod|HttpClient|WebClient|TcpClient|SmtpClient)\b", "Networking remains disabled; use an isolated mock endpoint later only by explicit approval."),
    ("high", "database", r"\b(?:SqlConnection|Invoke-Sqlcmd|ExecuteNonQuery)\b", "Replace the database with an ephemeral synthetic fixture."),
    ("medium", "process", r"\b(?:Start-Process|System\.Diagnostics\.Process)\b", "Record child processes and enforce process/time limits."),
    ("medium", "environment", r"\b(?:GetEnvironmentVariable|\$env:|Environment\.SetEnvironmentVariable)\b", "Provide only synthetic environment values."),
)
SEVERITY = ("low", "medium", "high", "critical")


def create_test_plan(files: dict[str, str], ai_cases: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    suffixes = {Path(name).suffix.casefold() for name in files}
    language = "mixed" if suffixes & {".ps1", ".psm1"} and suffixes & {".cs", ".csproj"} else "powershell" if suffixes & {".ps1", ".psm1"} else "csharp" if suffixes & {".cs", ".csproj"} else "unknown"
    findings = []
    for name, content in files.items():
        for risk, category, pattern, control in RULES:
            match = re.search(pattern, content, re.I)
            if match:
                findings.append({"risk": risk, "category": category, "evidence": f"{name}: {match.group(0)}"[:500], "control": control})
    risk = max((item["risk"] for item in findings), key=SEVERITY.index, default="low")
    deterministic = [
        {"name": "normal-input", "purpose": "Representative synthetic values.", "syntheticInput": {"computerName": "AEGIS-TEST-01", "records": [{"id": 1, "state": "Healthy"}]}, "expected": "Completes without changing the host."},
        {"name": "empty-and-missing", "purpose": "Empty and missing inputs.", "syntheticInput": {"computerName": "", "records": []}, "expected": "Returns a controlled validation result."},
        {"name": "boundary-and-malformed", "purpose": "Oversized and malformed values.", "syntheticInput": {"computerName": "X" * 255, "records": [{"id": -1, "state": "<invalid>"}]}, "expected": "Fails safely without an external side effect."},
        {"name": "dependency-unavailable", "purpose": "Unavailable dependency and timeout.", "syntheticInput": {"simulatedFailure": "timeout", "endpoint": "http://127.0.0.1:9"}, "expected": "Reports failure without retry storms."},
    ]
    approved_ai = []
    for item in (ai_cases or [])[:20]:
        if isinstance(item, dict) and all(isinstance(item.get(key), (str, dict)) for key in ("name", "purpose", "syntheticInput", "expected")):
            approved_ai.append({"name": str(item["name"])[:100], "purpose": str(item["purpose"])[:1000], "syntheticInput": item["syntheticInput"], "expected": str(item["expected"])[:1000], "source": "local-ai-suggestion"})
    return {"schemaVersion": 1, "id": str(uuid.uuid4()), "createdAt": datetime.now(timezone.utc).isoformat(), "language": language, "risk": risk, "findings": findings, "testCases": deterministic + approved_ai, "capabilities": {"network": False, "clipboard": False, "hostWrite": False, "credentials": False}, "requiresUserApproval": True}


def create_test_package(root: Path, files: dict[str, str], plan: dict[str, Any]) -> Path:
    package_root = root / str(plan["id"])
    input_root, output_root = package_root / "input", package_root / "output"
    input_root.mkdir(parents=True, exist_ok=False); output_root.mkdir()
    hashes: dict[str, str] = {}
    names: set[str] = set()
    for supplied, content in files.items():
        name = Path(supplied).name
        if not name or name.casefold() in names:
            raise ValueError("Test Lab requires unique safe source file names.")
        names.add(name.casefold()); (input_root / name).write_text(content, encoding="utf-8"); hashes[name] = hashlib.sha256(content.encode()).hexdigest()
    (input_root / "test-plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
    (input_root / "synthetic-data.json").write_text(json.dumps([item["syntheticInput"] for item in plan["testCases"]], indent=2), encoding="utf-8")
    (input_root / "manifest.json").write_text(json.dumps({"schemaVersion": 1, "planId": plan["id"], "hashes": hashes, "capabilities": plan["capabilities"]}, indent=2), encoding="utf-8")
    (input_root / "Run-AegisTestLab.ps1").write_text(SANDBOX_RUNNER, encoding="utf-8")
    # Use resource limits from plan or defaults
    memory_limit = plan.get("resourceLimits", {}).get("memoryMB", 4096)
    cpu_limit = plan.get("resourceLimits", {}).get("cpuPercent", 100)
    (package_root / "AegisTestLab.wsb").write_text(sandbox_configuration(input_root, output_root, memory_limit_mb=memory_limit, cpu_limit_percent=cpu_limit), encoding="utf-8")
    return package_root


def sandbox_configuration(input_root: Path, output_root: Path, memory_limit_mb: int = 4096, cpu_limit_percent: int = 100) -> str:
    """Generate Windows Sandbox configuration with resource limits."""
    return f"""<Configuration>
  <Networking>Disable</Networking>
  <ClipboardRedirection>Disable</ClipboardRedirection>
  <PrinterRedirection>Disable</PrinterRedirection>
  <AudioInput>Disable</AudioInput>
  <VideoInput>Disable</VideoInput>
  <MappedFolders>
    <MappedFolder>
      <HostFolder>{escape(str(input_root))}</HostFolder>
      <SandboxFolder>C:\\AegisTestLab\\Input</SandboxFolder>
      <ReadOnly>true</ReadOnly>
    </MappedFolder>
    <MappedFolder>
      <HostFolder>{escape(str(output_root))}</HostFolder>
      <SandboxFolder>C:\\AegisTestLab\\Output</SandboxFolder>
      <ReadOnly>false</ReadOnly>
    </MappedFolder>
  </MappedFolders>
  <LogonCommand>
    <Command>powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\\AegisTestLab\\Input\\Run-AegisTestLab.ps1</Command>
  </LogonCommand>
  <MemoryInMB>{memory_limit_mb}</MemoryInMB>
  <CPULimit>{cpu_limit_percent}</CPULimit>
  <ProtectedClient>Enable</ProtectedClient>
</Configuration>"""


SANDBOX_RUNNER = r"""$ErrorActionPreference = 'Stop'
$started = Get-Date; $results = @()
try {
  New-Item -ItemType Directory C:\AegisTestLab\Work -Force | Out-Null
  Copy-Item C:\AegisTestLab\Input\* C:\AegisTestLab\Work -Recurse -Force
  Get-ChildItem C:\AegisTestLab\Work -Include *.ps1,*.psm1 -Recurse | ForEach-Object { $errors=$null; [void][System.Management.Automation.Language.Parser]::ParseFile($_.FullName,[ref]$null,[ref]$errors); $results += [pscustomobject]@{Test='PowerShellParser';File=$_.Name;Passed=($errors.Count -eq 0);Detail=($errors|Out-String)} }
  Get-ChildItem C:\AegisTestLab\Work -Include *.csproj -Recurse | ForEach-Object { if(Get-Command dotnet -ErrorAction SilentlyContinue){$text=(& dotnet build $_.FullName --no-restore 2>&1|Out-String);$results += [pscustomobject]@{Test='DotNetBuild';File=$_.Name;Passed=($LASTEXITCODE -eq 0);Detail=$text.Substring(0,[Math]::Min($text.Length,64000))}}else{$results += [pscustomobject]@{Test='DotNetBuild';File=$_.Name;Passed=$false;Detail='Required offline .NET SDK is absent.'}} }
} catch {$results += [pscustomobject]@{Test='Harness';File='';Passed=$false;Detail=$_.Exception.Message}}
[pscustomobject]@{SchemaVersion=1;StartedAt=$started.ToUniversalTime().ToString('o');CompletedAt=(Get-Date).ToUniversalTime().ToString('o');Network='disabled';Credentials='none';Results=$results}|ConvertTo-Json -Depth 8|Set-Content C:\AegisTestLab\Output\evidence.json -Encoding UTF8
"""


def launch_sandbox(sandbox_wsb_path: Path, timeout_seconds: int = 300) -> dict[str, Any]:
    """Launch Windows Sandbox and return launch metadata.
    
    Args:
        sandbox_wsb_path: Path to the .wsb configuration file
        timeout_seconds: Maximum time to wait for sandbox to be ready
        
    Returns:
        Dictionary with launch status, process ID, and sandbox name
    """
    import subprocess
    import time
    
    if not sandbox_wsb_path.exists():
        return {"status": "error", "message": f"Sandbox file not found: {sandbox_wsb_path}"}
    
    try:
        # Launch Windows Sandbox
        process = subprocess.Popen(
            [str(sandbox_wsb_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False
        )
        
        # Wait briefly for sandbox to initialize
        time.sleep(2)
        
        return {
            "status": "launched",
            "process_id": process.pid,
            "sandbox_file": str(sandbox_wsb_path),
            "timeout_seconds": timeout_seconds,
            "launched_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def cleanup_sandbox(package_root: Path, sandbox_name: str | None = None) -> dict[str, Any]:
    """Clean up sandbox artifacts after execution.
    
    Args:
        package_root: Root directory of the test package
        sandbox_name: Optional sandbox name to target for cleanup
        
    Returns:
        Dictionary with cleanup status and details
    """
    import subprocess
    import shutil
    
    result = {
        "status": "success",
        "actions": [],
        "errors": [],
    }
    
    try:
        # Remove evidence output (sandbox-generated results)
        output_dir = package_root / "output"
        if output_dir.exists():
            shutil.rmtree(output_dir)
            result["actions"].append(f"Removed output directory: {output_dir}")
        
        # Optional: Kill any remaining sandbox processes
        if sandbox_name:
            try:
                subprocess.run(
                    ["taskkill", "/IM", "WindowsSandbox.exe", "/F"],
                    capture_output=True,
                    timeout=10
                )
                result["actions"].append("Terminated sandbox processes")
            except Exception as e:
                result["errors"].append(f"Failed to terminate sandbox: {e}")
        
    except Exception as e:
        result["status"] = "partial"
        result["errors"].append(str(e))
    
    return result
