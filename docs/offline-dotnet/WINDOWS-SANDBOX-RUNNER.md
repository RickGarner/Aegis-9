# Disposable Windows Sandbox Runner Specification

**Date:** 2026-09-22  
**Status:** Not Implemented  
**Priority:** External Integration (Priority 2)

---

## Executive Summary

A.E.G.I.S.-9 requires a disposable Windows Sandbox/VM runner for executing external capabilities in an isolated environment. This specification defines the isolation boundaries, provisioning mechanism, network controls, data handoff procedures, and cleanup requirements.

---

## Requirements

### 1. Isolation Boundaries

**Why needed:**  
External capabilities must execute in a completely isolated environment to prevent:

- Host system compromise
- Data exfiltration
- Persistence mechanisms
- Lateral movement

**Isolation requirements:**

| Boundary | Requirement | Implementation |
|----------|-------------|----------------|
| File system | Read-only host access | Sandbox virtual disk, no host mount |
| Network | Egress controls | Firewall rules, proxy whitelist |
| Memory | Isolated address space | Hyper-V isolation |
| Process | No host process access | Separate session, no IPC |
| Registry | Virtualized registry | Sandbox registry hive |
| User profile | Isolated user context | Temporary user profile |

---

### 2. Provisioning Mechanism

**Why needed:**  
Sandbox must be created on-demand and destroyed after use to ensure:

- No data留存 between runs
- Fresh environment for each execution
- Minimal resource footprint

**Provisioning options:**

#### Option A: Windows Sandbox
```powershell
# Enable Windows Sandbox feature
Enable-WindowsOptionalFeature -FeatureName "Containers-DisposableClientVM" -Online -Restart

# Launch Windows Sandbox
Start-Process "WindowsSandbox.exe"

# Programmatic launch via PowerShell
$sandbox = Start-SandBox -Configuration @{
    Configuration = @'
<Configuration>
  <MappedFolders>
    <Folder>
      <HostFolder>C:\sandbox-input</HostFolder>
      <SandboxFolder>%USERPROFILE%\Desktop\input</SandboxFolder>
      <ReadOnly>true</ReadOnly>
    </Folder>
  </MappedFolders>
  <LogonCommand>
    <Command>powershell -ExecutionPolicy Bypass -File C:\setup.ps1</Command>
  </LogonCommand>
</Configuration>
'@
}
```

#### Option B: Hyper-V Quick VM
```powershell
# Create isolated Hyper-V VM
$vmName = "Aegis-Sandbox-$(Get-Random)"
New-VM -Name $vmName -MemoryStartupBytes 4GB -VHDPath "D:\sandbox-vms\$vmName.vhdx" -VHDSizeBytes 50GB

# Configure isolation
Set-VMProcessor -VMName $vmName -ExposeVirtualizationExtensions $true
Set-VMNetworkAdapter -VMName $vmName -IsolationAllowHostOSAccess $false

# Start VM
Start-VM -Name $vmName

# Run script in VM via PowerShell Remoting
Invoke-Command -VMName $vmName -ScriptBlock {
    # Execution in isolated VM
    & C:\setup.ps1
}
```

#### Option C: Docker Desktop (Windows Containers)
```powershell
# Create isolated Windows container
docker run -d --name aegis-sandbox --isolation hyperv mcr.microsoft.com/windows/servercore:ltsc2022

# Copy files into container
docker copy input.txt aegis-sandbox:C:\input.txt

# Execute in container
docker exec aegis-sandbox powershell -File C:\run.ps1

# Cleanup
docker stop aegis-sandbox
docker rm aegis-sandbox
```

**Recommended:** Windows Sandbox for desktop use, Hyper-V for server deployment

---

### 3. Network Isolation

**Why needed:**  
Network egress must be controlled to prevent:

- Unauthorized data exfiltration
- Command and control communication
- Lateral movement to other systems

**Network control requirements:**

| Control | Requirement | Implementation |
|---------|-------------|----------------|
| Default policy | Deny all egress | Windows Firewall default deny |
| Allowlist | Whitelist approved endpoints | Firewall rules for specific IPs/ports |
| DNS | Controlled resolution | Custom DNS server or hosts file |
| Proxy | Mandatory proxy for allowed traffic | WPAD or explicit proxy configuration |
| Monitoring | Log all network activity | Windows Firewall logging |

**Firewall configuration:**

```powershell
# Create sandbox network profile
New-NetFirewallProfile -Name "Sandbox" -ProfileType "Private" -Enabled $true

# Default deny all outbound
New-NetFirewallRule -DisplayName "Default Deny Outbound" -Direction Outbound -Action Block -Profile "Private" -Enabled $true

# Allowlist specific endpoints
New-NetFirewallRule -DisplayName "Allow Approved API" -Direction Outbound -Action Allow -RemoteAddress "10.30.0.0/16" -Protocol TCP -LocalPort 443 -Enabled $true

# Allow DNS
New-NetFirewallRule -DisplayName "Allow DNS" -Direction Outbound -Action Allow -RemoteAddress "10.30.1.10" -Protocol UDP -RemotePort 53 -Enabled $true

# Enable logging
Set-NetFirewallProfile -Profile "Private" -LogAllowed $true -LogBlocked $true -LogFilePath "C:\Windows\System32\log\firewall.log"
```

---

### 4. Data Handoff

**Why needed:**  
Data must be transferred securely between host and sandbox without:

- Contaminating the host
- Persisting in the sandbox after cleanup
- Exposing sensitive data

**Data handoff methods:**

#### Method A: Mapped Folders (Read-Only)
```powershell
# Configure read-only mapped folder
$sandboxConfig = @{
    Configuration = @'
<MappedFolders>
  <Folder>
    <HostFolder>C:\sandbox-input</HostFolder>
    <SandboxFolder>%USERPROFILE%\Desktop\input</SandboxFolder>
    <ReadOnly>true</ReadOnly>
  </Folder>
</MappedFolders>
'@
}

# Sandbox can read from input folder but cannot modify host
```

#### Method B: Copy-on-Exit
```powershell
# Copy results from sandbox after execution
# Use PowerShell Remoting or file share

# In sandbox:
$results = & C:\run.ps1
Copy-Item C:\results.json \\host\share\sandbox-results\

# On host:
Copy-Item \\host\share\sandbox-results\results.json C:\sandbox-output\
```

#### Method C: Base64 Encoding
```powershell
# Encode results in sandbox
$results = Get-Content C:\results.json -Raw
$encoded = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($results))

# Output to stdout for capture
Write-Output $encoded

# On host:
$output = & sandbox-command.ps1
$decoded = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($output))
```

---

### 5. Cleanup Procedure

**Why needed:**  
Sandbox must be completely destroyed after use to ensure:

- No data留存
- No persistence mechanisms
- No resource leaks

**Cleanup requirements:**

| Action | Requirement | Implementation |
|--------|-------------|----------------|
| VM shutdown | Graceful shutdown | Stop-VM with -TurnOff |
| Virtual disk deletion | Delete VHDX file | Remove-Item -Recurse |
| Registry cleanup | Remove sandbox registry | Reg delete hive |
| Network cleanup | Remove firewall rules | Remove-NetFirewallRule |
| Temp files | Delete temp directory | Remove-Item -Recurse |

**Cleanup procedure:**

```powershell
function Remove-Sandbox {
    param(
        [string]$VmName,
        [string]$VhdPath
    )
    
    # Stop VM gracefully
    Stop-VM -Name $VmName -TurnOff -Force
    
    # Wait for VM to stop
    Start-Sleep -Seconds 5
    
    # Delete virtual disk
    if (Test-Path $VhdPath) {
        Remove-Item $VhdPath -Force -Recurse
    }
    
    # Remove VM configuration
    Remove-VM -Name $VmName -Force
    
    # Cleanup network rules
    Get-NetFirewallRule -DisplayName "*Sandbox*" | Remove-NetFirewallRule
    
    # Log cleanup
    Add-Content "C:\sandbox-cleanup.log" "$(Get-Date): Cleaned up $VmName"
}
```

---

## Implementation Plan

### Phase 1: Basic Sandbox Provisioning

**Goal:** Create disposable Windows Sandbox for basic execution

**Tasks:**
1. Enable Windows Sandbox feature
2. Create PowerShell wrapper for sandbox launch
3. Implement read-only input folder mapping
4. Implement result capture via stdout
5. Test basic execution workflow

**Deliverables:**
- `backend/app/sandbox_runner.py` - Python wrapper
- `scripts\launch-sandbox.ps1` - PowerShell launcher
- `docs\offline-dotnet\WINDOWS-SANDBOX-RUNNER.md` - Documentation

### Phase 2: Network Isolation

**Goal:** Enforce network egress controls

**Tasks:**
1. Configure default-deny firewall rules
2. Implement allowlist mechanism
3. Add network logging
4. Test network isolation

**Deliverables:**
- `scripts\configure-sandbox-network.ps1` - Network config script
- Updated firewall rules

### Phase 3: Advanced Features

**Goal:** Add Hyper-V support and advanced cleanup

**Tasks:**
1. Implement Hyper-V quick VM provisioning
2. Add automated cleanup procedure
3. Implement result validation
4. Add monitoring and alerting

**Deliverables:**
- `backend/app\hyper_v_runner.py` - Hyper-V runner
- `scripts\cleanup-sandbox.ps1` - Cleanup script

---

## Security Considerations

### 1. Attack Surface Reduction

- Disable PowerShell script execution by default
- Use AppLocker or WDAC to restrict executable paths
- Disable Windows Defender exclusions
- Enable Attack Surface Reduction rules

### 2. Data Protection

- Encrypt sandbox virtual disk
- Use BitLocker for host protection
- Never store sensitive data in sandbox
- Clear clipboard after execution

### 3. Monitoring

- Log all sandbox launches
- Log all network connections
- Log all file access
- Alert on anomalies

---

## Testing

### Test Cases

| Test | Description | Expected Result |
|------|-------------|-----------------|
| Basic execution | Run simple script in sandbox | Script executes successfully |
| Network denial | Attempt blocked network access | Connection denied |
| File system isolation | Attempt to modify host files | Access denied |
| Cleanup verification | Verify sandbox deleted after use | No VM, no VHD, no registry |
| Result capture | Capture script output | Output captured correctly |

### Test Procedure

```powershell
# Test 1: Basic execution
$result = & scripts\launch-sandbox.ps1 -Script "Write-Output 'Hello'"
if ($result -eq "Hello") {
    Write-Output "Test 1 PASSED"
} else {
    Write-Output "Test 1 FAILED"
}

# Test 2: Network denial
$result = & scripts\launch-sandbox.ps1 -Script "Test-NetConnection google.com -Port 80"
if ($result -eq "False") {
    Write-Output "Test 2 PASSED"
} else {
    Write-Output "Test 2 FAILED"
}

# Test 3: Cleanup verification
Start-Sleep -Seconds 10
if (-not (Get-VM -Name "Aegis-Sandbox-*" -ErrorAction SilentlyContinue)) {
    Write-Output "Test 3 PASSED"
} else {
    Write-Output "Test 3 FAILED"
}
```

---

## Related Documentation

- **Offline .NET SDK:** `docs/offline-dotnet/OFFLINE-NET-SDK-PROVISIONING.md`
- **Windows Sandbox:** https://learn.microsoft.com/windows/security/threat-protection/windows-sandbox
- **Hyper-V:** https://learn.microsoft.com/windows-server/virtualization/hyper-v

---

## References

- Windows Sandbox Documentation: https://learn.microsoft.com/windows/security/threat-protection/windows-sandbox
- Hyper-V Isolation: https://learn.microsoft.com/virtualization/hyper-v-on-windows/
- Windows Firewall: https://learn.microsoft.com/windows-server/networking/windows-firewall
