# Offline .NET SDK Provisioning Script
# Purpose: Create offline development environment for Aegis-9 C# projects
# Target Framework: .NET 8.0 (net8.0-windows)
# Date: 2026-09-23

param(
    [string]$OutputDirectory = "D:\offline-nuget-feed",
    [string]$SdkVersion = "8.0.100",
    [switch]$DownloadSdkInstaller,
    [switch]$CreateLocalFeed,
    [switch]$ValidateBuild
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Offline .NET SDK Provisioning" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Create output directory
if ($CreateLocalFeed -or $DownloadSdkInstaller) {
    Write-Host "[1/5] Creating offline package directory..." -ForegroundColor Yellow
    if (-not (Test-Path $OutputDirectory)) {
        New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
        Write-Host "  Created: $OutputDirectory" -ForegroundColor Green
    } else {
        Write-Host "  Directory already exists: $OutputDirectory" -ForegroundColor Green
    }
}

# Step 2: Download .NET SDK installer (if requested)
if ($DownloadSdkInstaller) {
    Write-Host ""
    Write-Host "[2/5] Downloading .NET SDK installer..." -ForegroundColor Yellow
    
    $SdkUrl = "https://dotnet.microsoft.com/download/dotnet/thank-you/sdk-${SdkVersion}-windows-x64-installer"
    $SdkInstallerPath = Join-Path $OutputDirectory "dotnet-sdk-${SdkVersion}-windows-x64.exe"
    
    if (Test-Path $SdkInstallerPath) {
        Write-Host "  Installer already exists: $SdkInstallerPath" -ForegroundColor Green
    } else {
        Write-Host "  Downloading from: $SdkUrl" -ForegroundColor Gray
        try {
            # Note: This requires internet access for initial download
            # In offline environment, copy installer manually
            Write-Host "  NOTE: Manual download required for offline environment" -ForegroundColor Cyan
            Write-Host "  Download from: https://dotnet.microsoft.com/download/dotnet/sdk" -ForegroundColor Cyan
            Write-Host "  Save as: $SdkInstallerPath" -ForegroundColor Cyan
        } catch {
            Write-Host "  Error: $_" -ForegroundColor Red
        }
    }
}

# Step 3: Identify required NuGet packages
Write-Host ""
Write-Host "[3/5] Identifying required NuGet packages..." -ForegroundColor Yellow

$ProjectFiles = Get-ChildItem -Path "D:\AEGIS\AEGIS-9" -Filter "*.csproj" -Recurse | Where-Object {
    $_.FullName -notmatch 'avatars|Avatar|AvatarHost'
}

$RequiredPackages = @{}

foreach ($ProjectFile in $ProjectFiles) {
    Write-Host "  Processing: $($ProjectFile.Name)" -ForegroundColor Gray
    
    $Content = Get-Content $ProjectFile.FullName -Raw
    $PackageRefs = [regex]::Matches($Content, '<PackageReference Include="([^"]+)" Version="([^"]+)" />')
    
    foreach ($Match in $PackageRefs) {
        $PackageName = $Match.Groups[1].Value
        $PackageVersion = $Match.Groups[2].Value
        $Key = "$PackageName|$PackageVersion"
        
        if (-not $RequiredPackages.ContainsKey($Key)) {
            $RequiredPackages[$Key] = @{
                Package = $PackageName
                Version = $PackageVersion
                Projects = @()
            }
        }
        $RequiredPackages[$Key].Projects += $ProjectFile.FullName
    }
}

Write-Host ""
Write-Host "  Found $($RequiredPackages.Count) unique package(s):" -ForegroundColor Green
foreach ($Package in $RequiredPackages.Values | Select-Object -First 10) {
    Write-Host "    - $($Package.Package) v$($Package.Version)" -ForegroundColor Gray
}
if ($RequiredPackages.Count -gt 10) {
    Write-Host "    ... and $($RequiredPackages.Count - 10) more" -ForegroundColor Gray
}

# Step 4: Create NuGet.config for local feed
Write-Host ""
Write-Host "[4/5] Creating NuGet.config for local feed..." -ForegroundColor Yellow

$NuGetConfigContent = @"
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <packageSources>
    <clear />
    <add key="offline-feed" value="$OutputDirectory" />
    <add key="nuget.org" value="https://api.nuget.org/v3/index.json" protocolVersion="3" />
  </packageSources>
  <packageSourceMapping>
    <packageSource key="offline-feed">
      <package pattern="*" />
    </packageSource>
  </packageSourceMapping>
</configuration>
"@

$NuGetConfigPath = Join-Path "D:\AEGIS\AEGIS-9" "NuGet.config"
Set-Content -Path $NuGetConfigPath -Value $NuGetConfigContent -Force
Write-Host "  Created: $NuGetConfigPath" -ForegroundColor Green

# Step 5: Generate package download script
Write-Host ""
Write-Host "[5/5] Generating package download script..." -ForegroundColor Yellow

$DownloadScriptPath = Join-Path $OutputDirectory "download-packages.ps1"

$DownloadScriptContent = @"
# Download NuGet packages to offline feed
# Run this script from a machine with internet access

\$localFeed = "$OutputDirectory"
\$packages = @$(
    $RequiredPackages.Values | ForEach-Object {
        @"
        @{ Package = '$($_.Package)'; Version = '$($_.Version)' }
"@
    }
)

Write-Host "Downloading $($packages.Count) packages to offline feed..."

foreach ($pkg in $packages) {
    \$packagePath = Join-Path \$localFeed "\$($pkg.Package).\$($pkg.Version)"
    if (-not (Test-Path \$packagePath)) {
        New-Item -ItemType Directory -Path \$packagePath -Force | Out-Null
    }
    
    Write-Host "  Downloading: $($pkg.Package) v$($pkg.Version)"
    try {
        nuget.exe install $($pkg.Package) -Version $($pkg.Version) -OutputDirectory \$packagePath -ExcludeVersion
    } catch {
        Write-Host "    Error: $_" -ForegroundColor Red
    }
}

Write-Host "Package download complete!" -ForegroundColor Green
"@

Set-Content -Path $DownloadScriptPath -Value $DownloadScriptContent -Force
Write-Host "  Created: $DownloadScriptPath" -ForegroundColor Green

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Provisioning Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Offline Feed Directory: $OutputDirectory" -ForegroundColor White
Write-Host "Target Framework: net8.0-windows" -ForegroundColor White
Write-Host "Required Packages: $($RequiredPackages.Count)" -ForegroundColor White
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Copy this directory to offline environment" -ForegroundColor White
Write-Host "2. Run download-packages.ps1 from online machine" -ForegroundColor White
Write-Host "3. Install .NET SDK 8.0.100 or later" -ForegroundColor White
Write-Host "4. Build projects with: dotnet build --no-restore" -ForegroundColor White
Write-Host ""
