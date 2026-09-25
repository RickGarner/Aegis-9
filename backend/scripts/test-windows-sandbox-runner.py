#!/usr/bin/env python3
"""Test Windows Sandbox Runner."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.windows_sandbox_runner import WindowsSandboxRunner, run_in_sandbox


def test_basic_execution():
    """Test basic script execution in sandbox."""
    print("=" * 80)
    print("Test 1: Basic Script Execution")
    print("=" * 80)
    
    script = """
Write-Output "Hello from Windows Sandbox"
Write-Output "Execution time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Output "Current directory: $(Get-Location)"
"""
    
    result = run_in_sandbox(
        script_content=script,
        timeout_seconds=60,
        network_isolated=True,
    )
    
    print(f"\nStatus: {result['status']}")
    print(f"Return Code: {result['return_code']}")
    print(f"Duration: {result['duration_seconds']:.2f}s")
    
    if result['stdout']:
        print(f"\nOutput:")
        print(result['stdout'])
    
    if result['stderr']:
        print(f"\nErrors:")
        print(result['stderr'])
    
    print(f"\nCleanup: {result['cleanup']['status']}")
    print()


def test_network_isolation():
    """Test network isolation in sandbox."""
    print("=" * 80)
    print("Test 2: Network Isolation")
    print("=" * 80)
    
    script = """
try {
    $result = Test-NetConnection google.com -Port 80 -InformationLevel Quiet
    Write-Output "Network access: $result"
} catch {
    Write-Output "Network test failed: $_"
}
"""
    
    result = run_in_sandbox(
        script_content=script,
        timeout_seconds=60,
        network_isolated=True,
    )
    
    print(f"\nStatus: {result['status']}")
    print(f"Output:")
    print(result['stdout'])
    print()


def test_file_operations():
    """Test file operations in sandbox."""
    print("=" * 80)
    print("Test 3: File Operations")
    print("=" * 80)
    
    script = """
# Create output file
$output = @{
    Timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    ComputerName = $env:COMPUTERNAME
    User = $env:USERNAME
    WorkingDirectory = Get-Location
}

$output | ConvertTo-Json | Out-File "$env:USERPROFILE\Desktop\output\result.json" -Encoding UTF8

Write-Output "File operation completed"
"""
    
    result = run_in_sandbox(
        script_content=script,
        timeout_seconds=60,
        network_isolated=True,
    )
    
    print(f"\nStatus: {result['status']}")
    print(f"Output:")
    print(result['stdout'])
    
    # Check output file
    output_file = Path("sandbox-output/result.json")
    if output_file.exists():
        print(f"\nOutput file contents:")
        print(output_file.read_text(encoding="utf-8"))
    
    print()


def test_timeout():
    """Test execution timeout."""
    print("=" * 80)
    print("Test 4: Execution Timeout")
    print("=" * 80)
    
    script = """
Write-Output "Starting long-running operation..."
Start-Sleep -Seconds 5
Write-Output "Operation completed"
"""
    
    result = run_in_sandbox(
        script_content=script,
        timeout_seconds=2,  # Short timeout
        network_isolated=True,
    )
    
    print(f"\nStatus: {result['status']}")
    print(f"Return Code: {result['return_code']}")
    print(f"Duration: {result['duration_seconds']:.2f}s")
    
    if result['stderr']:
        print(f"\nErrors:")
        print(result['stderr'])
    
    print()


if __name__ == "__main__":
    try:
        test_basic_execution()
        test_network_isolation()
        test_file_operations()
        test_timeout()
        
        print("=" * 80)
        print("All tests completed")
        print("=" * 80)
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
