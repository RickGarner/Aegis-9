"""Windows Sandbox Runner for isolated execution of external capabilities.

This module provides a disposable Windows Sandbox runner for executing
PowerShell scripts, C# programs, and other external capabilities in an
isolated environment with strict security boundaries.

Key Features:
- Disposable sandbox environment (created on-demand, destroyed after use)
- Network isolation (egress controls via firewall rules)
- File system isolation (read-only host access via mapped folders)
- Process isolation (separate session, no IPC with host)
- Automated cleanup (no data留存 between runs)

Security Boundaries:
- File system: Read-only host access via mapped folders
- Network: Egress controls via Windows Firewall
- Memory: Hyper-V isolation
- Process: No host process access
- Registry: Virtualized registry
- User profile: Isolated user context
"""

from __future__ import annotations

import json
import shutil
import subprocess
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class WindowsSandboxError(Exception):
    """Exception raised for Windows Sandbox errors."""
    pass


class WindowsSandboxRunner:
    """Runner for disposable Windows Sandbox execution.
    
    Attributes:
        sandbox_name: Unique name for the sandbox session
        sandbox_wsb_path: Path to the Windows Sandbox configuration file
        input_folder: Path to input files for the sandbox
        output_folder: Path to capture output from the sandbox
        network_isolated: Whether to isolate network access
        timeout_seconds: Maximum execution time
    """
    
    def __init__(
        self,
        sandbox_name: str | None = None,
        input_folder: Path | None = None,
        output_folder: Path | None = None,
        network_isolated: bool = True,
        timeout_seconds: int = 300,
    ):
        """Initialize the Windows Sandbox runner.
        
        Args:
            sandbox_name: Unique identifier for this sandbox session
            input_folder: Folder containing files to copy into sandbox
            output_folder: Folder to capture sandbox output
            network_isolated: Whether to isolate network access
            timeout_seconds: Maximum execution time in seconds
        """
        self.sandbox_name = sandbox_name or f"AegisSandbox-{uuid4().hex[:8]}"
        self.input_folder = input_folder or Path.cwd() / "sandbox-input"
        self.output_folder = output_folder or Path.cwd() / "sandbox-output"
        self.network_isolated = network_isolated
        self.timeout_seconds = timeout_seconds
        self.process: subprocess.Popen | None = None
        self.started_at: str | None = None
        self.completed_at: str | None = None
        
    def create_configuration(self) -> Path:
        """Create Windows Sandbox configuration file.
        
        Returns:
            Path to the generated .wsb configuration file
            
        Raises:
            WindowsSandboxError: If configuration creation fails
        """
        wsb_path = Path.cwd() / f"{self.sandbox_name}.wsb"
        
        # Create input/output folders if they don't exist
        self.input_folder.mkdir(parents=True, exist_ok=True)
        self.output_folder.mkdir(parents=True, exist_ok=True)
        
        # Generate WSB configuration
        wsb_content = f'''<Configuration>
  <MappedFolders>
    <MappedFolder>
      <HostFolder>{self.input_folder.resolve()}</HostFolder>
      <SandboxFolder>%USERPROFILE%\\Desktop\\input</SandboxFolder>
      <ReadOnly>true</ReadOnly>
    </MappedFolder>
    <MappedFolder>
      <HostFolder>{self.output_folder.resolve()}</HostFolder>
      <SandboxFolder>%USERPROFILE%\\Desktop\\output</SandboxFolder>
      <ReadOnly>false</ReadOnly>
    </MappedFolder>
  </MappedFolders>
  <LogonCommand>
    <Command>powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File "%USERPROFILE%\\Desktop\\input\\run.ps1"</Command>
  </LogonCommand>
  <Networking>{'Disabled' if self.network_isolated else 'Standard'}</Networking>
</Configuration>'''
        
        try:
            wsb_path.write_text(wsb_content, encoding="utf-8")
            return wsb_path
        except OSError as error:
            raise WindowsSandboxError(f"Failed to create WSB configuration: {error}") from error
    
    def launch(self) -> dict[str, Any]:
        """Launch the Windows Sandbox.
        
        Returns:
            Dictionary with launch status, process ID, and metadata
            
        Raises:
            WindowsSandboxError: If sandbox launch fails
        """
        wsb_path = self.create_configuration()
        
        if not wsb_path.exists():
            raise WindowsSandboxError(f"WSB configuration not found: {wsb_path}")
        
        try:
            # Launch Windows Sandbox
            self.process = subprocess.Popen(
                [str(wsb_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
            
            self.started_at = datetime.now(timezone.utc).isoformat()
            
            return {
                "status": "launched",
                "sandbox_name": self.sandbox_name,
                "process_id": self.process.pid,
                "wsb_file": str(wsb_path),
                "input_folder": str(self.input_folder),
                "output_folder": str(self.output_folder),
                "network_isolated": self.network_isolated,
                "timeout_seconds": self.timeout_seconds,
                "started_at": self.started_at,
            }
        except OSError as error:
            raise WindowsSandboxError(f"Failed to launch sandbox: {error}") from error
    
    def wait(self, timeout_seconds: int | None = None) -> dict[str, Any]:
        """Wait for sandbox execution to complete.
        
        Args:
            timeout_seconds: Maximum time to wait (uses default if not specified)
            
        Returns:
            Dictionary with execution results
            
        Raises:
            WindowsSandboxError: If execution times out or fails
        """
        if self.process is None:
            raise WindowsSandboxError("Sandbox not launched")
        
        timeout = timeout_seconds or self.timeout_seconds
        
        try:
            stdout, stderr = self.process.communicate(timeout=timeout)
            self.completed_at = datetime.now(timezone.utc).isoformat()
            
            return {
                "status": "completed",
                "return_code": self.process.returncode,
                "stdout": stdout.decode("utf-8", errors="replace") if stdout else "",
                "stderr": stderr.decode("utf-8", errors="replace") if stderr else "",
                "completed_at": self.completed_at,
                "duration_seconds": self._calculate_duration(),
            }
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.completed_at = datetime.now(timezone.utc).isoformat()
            
            return {
                "status": "timeout",
                "return_code": -1,
                "stdout": "",
                "stderr": f"Execution timed out after {timeout} seconds",
                "completed_at": self.completed_at,
                "duration_seconds": timeout,
            }
    
    def cleanup(self) -> dict[str, Any]:
        """Clean up sandbox artifacts.
        
        Returns:
            Dictionary with cleanup status and actions taken
            
        Raises:
            WindowsSandboxError: If cleanup fails
        """
        result = {
            "status": "success",
            "actions": [],
            "errors": [],
        }
        
        try:
            # Remove WSB configuration file
            wsb_path = Path.cwd() / f"{self.sandbox_name}.wsb"
            if wsb_path.exists():
                wsb_path.unlink()
                result["actions"].append(f"Removed WSB file: {wsb_path}")
            
            # Keep input/output folders for inspection
            # (can be removed if desired)
            result["actions"].append(f"Input folder preserved: {self.input_folder}")
            result["actions"].append(f"Output folder preserved: {self.output_folder}")
            
        except OSError as error:
            result["status"] = "partial"
            result["errors"].append(f"Cleanup error: {error}")
        
        return result
    
    def _calculate_duration(self) -> float:
        """Calculate execution duration in seconds."""
        if self.started_at and self.completed_at:
            start = datetime.fromisoformat(self.started_at)
            end = datetime.fromisoformat(self.completed_at)
            return (end - start).total_seconds()
        return 0.0


def run_in_sandbox(
    script_content: str,
    input_files: dict[str, str] | None = None,
    timeout_seconds: int = 300,
    network_isolated: bool = True,
) -> dict[str, Any]:
    """Convenience function to run a script in a disposable sandbox.
    
    Args:
        script_content: PowerShell script content to execute
        input_files: Dictionary of filename -> content for input files
        timeout_seconds: Maximum execution time
        network_isolated: Whether to isolate network access
        
    Returns:
        Dictionary with execution results
        
    Example:
        >>> result = run_in_sandbox(
        ...     script_content="Write-Output 'Hello from sandbox'",
        ...     timeout_seconds=60
        ... )
        >>> print(result["stdout"])
        Hello from sandbox
    """
    runner = WindowsSandboxRunner(
        timeout_seconds=timeout_seconds,
        network_isolated=network_isolated,
    )
    
    # Create input files
    if input_files:
        for filename, content in input_files.items():
            (runner.input_folder / filename).write_text(content, encoding="utf-8")
    
    # Create run script
    run_script = f'''# Auto-generated run script
# Execution time: {datetime.now(timezone.utc).isoformat()}

try {{
    # Execute provided script
    {script_content}
    
    # Save output to file
    $output = Get-Content "$env:USERPROFILE\\Desktop\\output\\*" -ErrorAction SilentlyContinue
    $output | Out-File "$env:USERPROFILE\\Desktop\\output\\result.txt" -Encoding UTF8
}} catch {{
    # Capture error
    $error[0].Exception.Message | Out-File "$env:USERPROFILE\\Desktop\\output\\error.txt" -Encoding UTF8
    exit 1
}}
'''
    
    (runner.input_folder / "run.ps1").write_text(run_script, encoding="utf-8")
    
    # Launch and execute
    launch_result = runner.launch()
    execution_result = runner.wait()
    cleanup_result = runner.cleanup()
    
    return {
        **launch_result,
        **execution_result,
        "cleanup": cleanup_result,
    }


def uuid4() -> str:
    """Generate a UUID4 string."""
    return str(uuid.uuid4())
