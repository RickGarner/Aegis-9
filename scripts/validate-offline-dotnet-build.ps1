# Validate Offline .NET SDK Build
# Purpose: Verify C# projects can build without network access
# Date: 2026-09-23

param(
    [string]$ProjectPath = "D:\AEGIS\AEGIS-9\desktop\Aegis.Desktop",
    [string]$OutputDirectory = "D:\offline-nuget-feed",
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Offline .NET SDK Build Validation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check .NET SDK installation
Write-Host "[1/4] Checking .NET SDK installation..." -ForegroundColor Yellow

$dotnetVersion = dotnet --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ERROR: dotnet CLI not found" -ForegroundColor Red
    Write-Host "  Please install .NET SDK 8.0 or later" -ForegroundColor Red
    exit 1
}

Write-Host "  Installed: $dotnetVersion" -ForegroundColor Green

# Check SDK version
$sdkList = dotnet --list-sdks
Write-Host "  Available SDKs:" -ForegroundColor Gray
$sdkList | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }

# Check local feed
Write-Host ""
Write-Host "[2/4] Checking offline NuGet feed..." -ForegroundColor Yellow

if (Test-Path $OutputDirectory) {
    $packageCount = (Get-ChildItem $OutputDirectory -Recurse -Filter "*.nupkg" | Measure-Object).Count
    Write-Host "  Feed location: $OutputDirectory" -ForegroundColor Green
    Write-Host "  Packages found: $packageCount" -ForegroundColor Green
} else {
    Write-Host "  WARNING: Offline feed not found at $OutputDirectory" -ForegroundColor Yellow
    Write-Host "  Packages will be downloaded from nuget.org" -ForegroundColor Yellow
}

# Check project file
Write-Host ""
Write-Host "[3/4] Checking project file..." -ForegroundColor Yellow

$projectFile = Join-Path $ProjectPath "*.csproj"
$actualProject = Get-ChildItem $projectFile | Select-Object -First 1

if (-not $actualProject) {
    Write-Host "  ERROR: No .csproj file found in $ProjectPath" -ForegroundColor Red
    exit 1
}

Write-Host "  Project: $($actualProject.FullName)" -ForegroundColor Green

$projectContent = Get-Content $actualProject.FullName -Raw
$targetFramework = [regex]::Match($projectContent, '<TargetFramework>([^<]+)</TargetFramework>').Groups[1].Value
Write-Host "  Target Framework: $targetFramework" -ForegroundColor Green

# Build project
Write-Host ""
Write-Host "[4/4] Building project..." -ForegroundColor Yellow

$buildArgs = @("build")
if ($Clean) {
    $buildArgs += @("--no-build" -eq $false ? @() : @())
    Write-Host "  Cleaning previous builds..." -ForegroundColor Gray
    dotnet clean $actualProject.FullName | Out-Null
}

Write-Host "  Command: dotnet $($buildArgs -join ' ')" -ForegroundColor Gray

$buildResult = dotnet build $actualProject.FullName `
    --no-restore `
    --verbosity minimal `
    --nologo `
    2>&1

$buildExitCode = $LASTEXITCODE

if ($buildExitCode -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Build Successful!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "The project built successfully without network access." -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "Build Failed" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Exit Code: $buildExitCode" -ForegroundColor Red
    Write-Host ""
    Write-Host "Build Output:" -ForegroundColor Yellow
    $buildResult | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
    
    if ($buildResult -match "Unable to find package|Package source.*not found") {
        Write-Host ""
        Write-Host "Possible cause: Missing package in offline feed" -ForegroundColor Cyan
        Write-Host "Solution: Run download-packages.ps1 from online machine" -ForegroundColor Cyan
    }
    
    exit $buildExitCode
}

# Show build output directory
$binDir = Join-Path $ProjectPath "bin"
$objDir = Join-Path $ProjectPath "obj"

if (Test-Path $binDir) {
    Write-Host ""
    Write-Host "Build artifacts:" -ForegroundColor Yellow
    Get-ChildItem $binDir -Recurse -File | Select-Object -First 10 | ForEach-Object {
        Write-Host "  $($_.FullName -replace [regex]::Escape($ProjectPath), '')" -ForegroundColor Gray
    }
}

Write-Host ""
