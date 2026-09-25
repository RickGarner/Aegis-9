# Offline .NET SDK Provisioning Requirements

**Date:** 2026-09-22  
**Status:** Not Provisioned  
**Priority:** External Integration (Priority 2)

---

## Executive Summary

A.E.G.I.S.-9 requires an offline .NET SDK and dependency image for C# compilation in isolated environments. This document defines the provisioning requirements and procedure for creating a self-contained development environment that does not require internet access.

---

## Requirements

### 1. .NET SDK Version

**Why needed:**  
C# compilation requires a specific .NET SDK version that matches the target framework of Aegis-9 projects.

**Discovery method:**

```powershell
# Check existing Aegis-9 projects for target framework
Get-ChildItem "D:\AEGIS\AEGIS-9\Aegis-Developer-Studio\*.csproj" | 
    Select-Object FullName, @{N='TargetFramework';E={(Get-Content $_.FullName | Select-String '<TargetFramework>')</}}

# Check global.json if present
Get-Content "D:\AEGIS\AEGIS-9\global.json"
```

**Expected output:**
```json
{
  "sdk": {
    "version": "8.0.100",
    "rollForward": "latestMinor"
  }
}
```

**Recommended version:** .NET 8.0 LTS (Long Term Support)

---

### 2. Offline Package Acquisition

**Why needed:**  
Offline compilation requires all NuGet packages to be available without internet access.

**Acquisition method:**

#### Method A: Microsoft Download Center
```powershell
# Download .NET SDK offline installer
# URL: https://dotnet.microsoft.com/download/dotnet/thank-you/sdk-8.0.100-windows-x64-installer
# File: dotnet-sdk-8.0.100-windows-x64.exe

# Verify download
Get-FileHash dotnet-sdk-8.0.100-windows-x64.exe -Algorithm SHA256
```

#### Method B: NuGet Package Feed Mirroring
```powershell
# Create local NuGet feed
$localFeed = "D:\offline-nuget-feed"
New-Item -ItemType Directory -Path $localFeed -Force

# Download required packages
# Use dotnet pack command with --no-cache flag
dotnet pack --output $localFeed --no-cache

# Or use NuGet.exe to download specific packages
NuGet.exe install PackageId -Version Version -OutputDirectory $localFeed
```

#### Method C: Docker Image Extraction
```powershell
# Pull .NET SDK Docker image
docker pull mcr.microsoft.com/dotnet/sdk:8.0

# Extract SDK from image
docker export $(docker create mcr.microsoft.com/dotnet/sdk:8.0) | tar -xvf - -C D:\dotnet-sdk-extract

# Copy required files to offline location
```

---

### 3. Required Dependencies

**Why needed:**  
Aegis-9 C# projects may have specific NuGet package dependencies that must be available offline.

**Discovery method:**

```powershell
# Analyze project dependencies
cd D:\AEGIS\AEGIS-9\Aegis-Developer-Studio

# List all NuGet packages
dotnet list package --include-transitive

# Export to file
dotnet list package --include-transitive > required-packages.txt
```

**Common dependencies for VS extensions:**
- `Microsoft.VisualStudio.SDK`
- `Microsoft.VisualStudio.ExtensionManager`
- `Microsoft.VSSDK.BuildTools`
- `EnvDTE`
- `Microsoft.Build.Framework`
- `Microsoft.Build.Utilities.Core`

---

### 4. Validation Environment

**Why needed:**  
Before deploying to production, the offline environment must be validated to ensure:

- .NET SDK installs correctly
- All required packages are available
- C# projects compile successfully
- No internet access is required

**Validation procedure:**

```powershell
# Step 1: Create isolated test environment
$testDir = "D:\offline-dotnet-test"
New-Item -ItemType Directory -Path $testDir -Force

# Step 2: Install .NET SDK from offline installer
Start-Process "D:\dotnet-sdk-8.0.100-windows-x64.exe" -ArgumentList "/quiet", "/norestart" -Wait

# Step 3: Verify SDK installation
dotnet --version

# Step 4: Create test project
cd $testDir
dotnet new console -n TestProject

# Step 5: Add required packages from local feed
dotnet add package PackageId --source $localFeed

# Step 6: Build project (should work without internet)
dotnet build

# Step 7: Verify no network access required
# Disconnect network and repeat steps 5-6
```

---

### 5. Integration with Aegis

**Why needed:**  
The offline .NET SDK must integrate with Aegis-9 workflow automation for:

- Automated C# compilation
- Extension building
- Dependency resolution
- Artifact generation

**Integration points:**

```python
# Example: Aegis workflow for offline compilation
from pathlib import Path
from subprocess import run, PIPE, CalledProcessError

def compile_dotnet_project(project_path: str, offline_feed: str) -> bool:
    """Compile C# project using offline .NET SDK."""
    
    # Set environment for offline mode
    env = os.environ.copy()
    env["NUGET_PACKAGES"] = str(offline_feed)
    
    # Run dotnet build
    result = run(
        ["dotnet", "build", project_path, "--no-restore"],
        capture_output=True,
        text=True,
        env=env,
        timeout=300
    )
    
    if result.returncode == 0:
        print("Build successful")
        return True
    else:
        print(f"Build failed: {result.stderr}")
        return False
```

---

## Provisioning Procedure

### Step 1: Identify Requirements

```powershell
# 1.1: Check global.json for SDK version
Get-Content "D:\AEGIS\AEGIS-9\global.json"

# 1.2: List all project dependencies
cd D:\AEGIS\AEGIS-9
Get-ChildItem -Recurse -Filter "*.csproj" | ForEach-Object {
    dotnet list $_.FullName package --include-transitive
}

# 1.3: Document required packages
# Save to: docs/offline-dotnet/required-packages.md
```

### Step 2: Acquire Offline Packages

```powershell
# 2.1: Download .NET SDK offline installer
# From: https://dotnet.microsoft.com/download/dotnet/thank-you/sdk-8.0.100-windows-x64-installer
# Save to: D:\offline-packages\dotnet-sdk-8.0.100-windows-x64.exe

# 2.2: Create local NuGet feed
$localFeed = "D:\offline-packages\nuget-feed"
New-Item -ItemType Directory -Path $localFeed -Force

# 2.3: Download required NuGet packages
# Use NuGet.exe or dotnet pack command
```

### Step 3: Create Validation Environment

```powershell
# 3.1: Create isolated test directory
$testDir = "D:\offline-dotnet-validation"
New-Item -ItemType Directory -Path $testDir -Force

# 3.2: Install .NET SDK
Start-Process "D:\offline-packages\dotnet-sdk-8.0.100-windows-x64.exe" -ArgumentList "/quiet", "/norestart" -Wait

# 3.3: Configure NuGet to use local feed
dotnet nuget add source $localFeed --name "OfflineFeed"

# 3.4: Test compilation
cd $testDir
dotnet new console -n TestProject
dotnet build
```

### Step 4: Document Procedure

```markdown
# Offline .NET SDK Provisioning Guide

## Prerequisites
- Windows 10/11 or Windows Server
- Administrator access
- D:\offline-packages directory

## Procedure
1. Download .NET SDK offline installer
2. Create local NuGet feed
3. Download required packages
4. Install SDK
5. Configure NuGet sources
6. Validate compilation

## Validation
- Run dotnet --version
- Build test project
- Verify no network access required
```

---

## Security Considerations

### 1. Package Integrity

```powershell
# Verify package signatures
Get-ChildItem $localFeed -Recurse -Filter "*.nupkg" | ForEach-Object {
    # Check package signature if available
    # Use signtool or NuGet package validator
}
```

### 2. Supply Chain Security

- Only download packages from official Microsoft sources
- Verify SHA256 hashes before installation
- Maintain audit log of all downloaded packages
- Scan packages for malware before use

### 3. Isolation

- Offline feed should be on isolated network segment
- No internet access from validation environment
- Regular security updates applied to offline packages

---

## Troubleshooting

### Issue: Package not found in offline feed

**Solution:**
```powershell
# Check if package exists in feed
Get-ChildItem $localFeed -Recurse -Filter "*PackageId*.nupkg"

# If not found, download manually
NuGet.exe install PackageId -Version Version -OutputDirectory $localFeed
```

### Issue: SDK version mismatch

**Solution:**
```powershell
# Check installed SDK versions
dotnet --list-sdks

# If wrong version, uninstall and reinstall correct version
# Remove from Programs and Features
# Reinstall from offline installer
```

### Issue: Build fails with missing dependency

**Solution:**
```powershell
# Identify missing package from build error
# Download package to local feed
NuGet.exe install MissingPackage -Version Version -OutputDirectory $localFeed

# Retry build
dotnet build
```

---

## Related Documentation

- **Windows Sandbox Runner:** `docs/offline-dotnet/WINDOWS-SANDBOX-RUNNER.md`
- **Aegis Workflow Automation:** `backend/app/workflow_governance.py`
- **Operations Monitoring:** `docs/operational-monitoring.md`

---

## References

- .NET Download: https://dotnet.microsoft.com/download
- NuGet Package Manager: https://learn.microsoft.com/nuget/
- Offline Deployment: https://learn.microsoft.com/dotnet/core/install/windows?tabs=net80#offline-installation
