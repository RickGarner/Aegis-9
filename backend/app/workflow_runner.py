import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, Field


class PermissionManifest(BaseModel):
    schema_version: int = 1
    language: str
    commands: list[str] = Field(default_factory=list)
    modules: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)
    restricted_execution_allowed: bool = False


class WorkflowTestEvidence(BaseModel):
    profile: str
    status: str
    artifact_sha256: str
    permission_manifest: PermissionManifest
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = 0
    evidence_sha256: str
    summary: str


@dataclass(frozen=True)
class PreparedArtifact:
    source_path: Path
    source_text: str
    sha256: str
    manifest: PermissionManifest


class WorkflowTestRunner:
    """Creates immutable artifacts and performs bounded non-production validation."""

    def __init__(self, artifact_root: Path, timeout_seconds: int = 30, output_limit: int = 64_000) -> None:
        self._artifact_root = artifact_root
        self._timeout_seconds = timeout_seconds
        self._output_limit = output_limit

    def prepare(self, transfer_id: str, revision: int, language: str, implementation: str) -> PreparedArtifact:
        source = self._extract_source(language, implementation)
        digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
        manifest = self._analyze(language, source)
        directory = self._artifact_root / transfer_id / f"revision-{revision}" / digest
        directory.mkdir(parents=True, exist_ok=True)
        extension = ".ps1" if language == "powershell" else ".cs"
        source_path = directory / f"workflow{extension}"
        if source_path.exists() and source_path.read_text(encoding="utf-8") != source:
            raise RuntimeError("Immutable artifact hash collision detected.")
        if not source_path.exists():
            source_path.write_text(source, encoding="utf-8", newline="\n")
        manifest_path = directory / "permission-manifest.json"
        manifest_payload = manifest.model_dump_json(indent=2)
        if manifest_path.exists() and manifest_path.read_text(encoding="utf-8") != manifest_payload:
            raise RuntimeError("Immutable permission manifest does not match the stored artifact.")
        if not manifest_path.exists():
            manifest_path.write_text(manifest_payload, encoding="utf-8", newline="\n")
        return PreparedArtifact(source_path, source, digest, manifest)

    def run(self, artifact: PreparedArtifact, language: str, profile: str) -> WorkflowTestEvidence:
        if profile not in {"static", "restricted"}:
            raise ValueError("Test profile must be 'static' or 'restricted'.")
        if profile == "restricted" and not artifact.manifest.restricted_execution_allowed:
            return self._evidence(
                profile, "blocked", artifact, None, "", "",
                "Restricted execution was blocked by the permission manifest. Use static validation and revise the implementation.", 0,
            )
        started = time.perf_counter()
        try:
            command, working_directory = self._command(artifact, language, profile)
            environment = {
                "PATH": os.environ.get("PATH", ""),
                "SystemRoot": os.environ.get("SystemRoot", r"C:\Windows"),
                "TEMP": tempfile.gettempdir(),
                "TMP": tempfile.gettempdir(),
                "USERPROFILE": os.environ.get("USERPROFILE", ""),
                "APPDATA": os.environ.get("APPDATA", ""),
                "LOCALAPPDATA": os.environ.get("LOCALAPPDATA", ""),
                "ProgramFiles": os.environ.get("ProgramFiles", r"C:\Program Files"),
                "DOTNET_CLI_HOME": str(artifact.source_path.parent),
                "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
                "DOTNET_NOLOGO": "1",
            }
            result = subprocess.run(
                command,
                cwd=working_directory,
                env=environment,
                capture_output=True,
                text=True,
                timeout=self._timeout_seconds,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            duration = int((time.perf_counter() - started) * 1000)
            stdout = result.stdout[-self._output_limit:]
            stderr = result.stderr[-self._output_limit:]
            status = "passed" if result.returncode == 0 else "failed"
            summary = f"{profile.title()} validation {status} with exit code {result.returncode}."
            return self._evidence(profile, status, artifact, result.returncode, stdout, stderr, summary, duration)
        except subprocess.TimeoutExpired as error:
            duration = int((time.perf_counter() - started) * 1000)
            return self._evidence(
                profile, "timed_out", artifact, None,
                self._bounded(error.stdout), self._bounded(error.stderr),
                f"Validation exceeded the {self._timeout_seconds}-second limit and was terminated.", duration,
            )
        except (OSError, RuntimeError, ValueError) as error:
            duration = int((time.perf_counter() - started) * 1000)
            return self._evidence(profile, "failed", artifact, None, "", str(error), f"Validation could not start: {error}", duration)

    def _command(self, artifact: PreparedArtifact, language: str, profile: str) -> tuple[list[str], Path]:
        if language == "powershell":
            if profile == "static":
                escaped = str(artifact.source_path).replace("'", "''")
                parser = f"$e=$null;$t=$null;[System.Management.Automation.Language.Parser]::ParseFile('{escaped}',[ref]$t,[ref]$e)|Out-Null;if($e.Count){{$e|ForEach-Object{{$_.Message}}|Write-Error;exit 1}}"
                return ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", parser], artifact.source_path.parent
            escaped = str(artifact.source_path).replace("'", "''")
            constrained = f"$ExecutionContext.SessionState.LanguageMode='ConstrainedLanguage';& '{escaped}'"
            return ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", constrained], artifact.source_path.parent

        project = artifact.source_path.parent / "AegisWorkflowTest.csproj"
        project_payload = '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0</TargetFramework><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable><EnableDefaultCompileItems>false</EnableDefaultCompileItems></PropertyGroup><ItemGroup><Compile Include="workflow.cs" /></ItemGroup></Project>'
        if not project.exists():
            project.write_text(project_payload, encoding="utf-8", newline="\n")
        if profile == "static":
            return ["dotnet", "build", str(project), "--nologo", "--verbosity", "minimal", "-p:RestoreIgnoreFailedSources=true"], project.parent
        return ["dotnet", "run", "--project", str(project), "--no-restore"], project.parent

    @staticmethod
    def _extract_source(language: str, implementation: str) -> str:
        fence = r"```(?:powershell|ps1)\s*(.*?)```" if language == "powershell" else r"```(?:csharp|cs|c#)\s*(.*?)```"
        match = re.search(fence, implementation, re.DOTALL | re.IGNORECASE)
        if not match or not match.group(1).strip():
            raise ValueError(f"Generated implementation does not contain a fenced {language} source artifact.")
        return match.group(1).strip() + "\n"

    @staticmethod
    def _analyze(language: str, source: str) -> PermissionManifest:
        findings: list[str] = []
        capabilities: set[str] = set()
        commands: set[str] = set()
        modules: set[str] = set()
        if language == "powershell":
            command_scan_source = re.sub(r"(?m)#.*$|(?:'(?:''|[^'])*'|\"(?:`.|[^\"])*\")", "", source)
            detected_commands = re.findall(r"(?im)(?<![-\w])([a-z][a-z]+-[a-z][a-z0-9]+)", command_scan_source)
            commands.update(detected_commands)
            modules.update(re.findall(r"(?im)^\s*Import-Module\s+['\"]?([^'\"\s]+)", source))
            checks = (
                (r"\b(?:Invoke-WebRequest|Invoke-RestMethod|Test-NetConnection|New-PSSession|Invoke-Command)\b", "network", "Network or remote-session access requested."),
                (r"\b(?:Add-Content|Set-Content|Out-File|Remove-Item|Move-Item|Copy-Item|New-Item)\b", "filesystem_write", "Filesystem mutation requested."),
                (r"\b(?:Start-Process|Stop-Process|Start-Service|Stop-Service|Restart-Service)\b", "process_service", "Process or service control requested."),
                (r"\b(?:Search-ADAccount|Get-ADUser|Set-ADUser|Unlock-ADAccount)\b", "directory_service", "Active Directory access requested."),
                (r"(?i)\bwhile\s*\(\s*\$true\s*\)|\bStart-Sleep\b", "long_running", "Long-running loop or delay detected."),
                (r"(?i)[A-Z]:\\|\\\\[A-Za-z0-9._-]+\\", "absolute_path", "Absolute or UNC path detected."),
                (r"(?i)\b(?:Get-Credential|PSCredential|ConvertTo-SecureString)\b", "credentials", "Credential access requested."),
                (r"(?im)(?:^|[;|&]\s*)\b(?:rm|del|erase|rd|rmdir|cp|mv|curl|wget|iwr|irm|iex|saps|kill|sc|net|reg)\b", "alias_or_native", "A command alias or native utility is not permitted in restricted tests."),
                (r"(?m)(?:^|[;|]\s*)[&.]\s*(?:['\"]|[A-Za-z]:\\|\\\\)", "dynamic_invocation", "Dynamic script or executable invocation requested."),
                (r"(?<![<>=])(?:>>|\s>\s)", "filesystem_write", "Output redirection requested."),
                (r"\[[A-Za-z][A-Za-z0-9_.]+\]::", "dotnet_api", "Direct .NET API invocation requested."),
            )
            allowed_commands = {"write-output", "write-verbose", "write-warning", "measure-object", "where-object", "foreach-object", "select-object", "sort-object"}
            unapproved_commands = sorted(command for command in commands if command.lower() not in allowed_commands)
            if unapproved_commands:
                capabilities.add("unapproved_command")
                findings.append("Commands outside the restricted-test allowlist: " + ", ".join(unapproved_commands))
            executable_segments = [segment.strip() for segment in re.split(r"(?m)[;|\r\n]+", command_scan_source) if segment.strip()]
            unsupported_segments = [
                segment for segment in executable_segments
                if not re.match(r"(?i)^(?:write-output|write-verbose|write-warning|measure-object|where-object|foreach-object|select-object|sort-object)\b", segment)
            ]
            if unsupported_segments:
                capabilities.add("unsupported_syntax")
                findings.append("Restricted tests only execute simple pipelines made from explicitly allowed cmdlets.")
        else:
            checks = (
                (r"System\.Net|HttpClient|Socket", "network", "Network access requested."),
                (r"System\.IO|\bFile\.|\bDirectory\.", "filesystem_write", "Filesystem access requested."),
                (r"Diagnostics\.Process|Process\.Start", "process_service", "Process control requested."),
                (r"(?i)while\s*\(\s*true\s*\)|Thread\.Sleep|Task\.Delay", "long_running", "Long-running loop or delay detected."),
                (r"DllImport|NativeLibrary", "native_code", "Native-code access requested."),
                (r"Environment\.GetEnvironmentVariable", "credentials", "Environment-variable access requested."),
            )
            capabilities.add("compiled_execution_unavailable")
            findings.append("C# execution requires an OS sandbox; this runner performs build validation only.")
        for pattern, capability, finding in checks:
            if re.search(pattern, source, re.IGNORECASE | re.MULTILINE):
                capabilities.add(capability)
                findings.append(finding)
        allowed = not capabilities
        return PermissionManifest(
            language=language,
            commands=sorted(commands),
            modules=sorted(modules),
            capabilities=sorted(capabilities),
            findings=findings,
            restricted_execution_allowed=allowed,
        )

    def _evidence(self, profile: str, status: str, artifact: PreparedArtifact, exit_code: int | None, stdout: str, stderr: str, summary: str, duration_ms: int) -> WorkflowTestEvidence:
        payload = json.dumps({
            "profile": profile, "status": status, "artifact_sha256": artifact.sha256,
            "manifest": artifact.manifest.model_dump(), "exit_code": exit_code,
            "stdout": stdout, "stderr": stderr, "duration_ms": duration_ms, "summary": summary,
        }, sort_keys=True)
        return WorkflowTestEvidence(
            profile=profile, status=status, artifact_sha256=artifact.sha256,
            permission_manifest=artifact.manifest, exit_code=exit_code,
            stdout=stdout, stderr=stderr, duration_ms=duration_ms,
            evidence_sha256=hashlib.sha256(payload.encode("utf-8")).hexdigest(), summary=summary,
        )

    def _bounded(self, value: bytes | str | None) -> str:
        if value is None:
            return ""
        text = value.decode(errors="replace") if isinstance(value, bytes) else value
        return text[-self._output_limit:]
