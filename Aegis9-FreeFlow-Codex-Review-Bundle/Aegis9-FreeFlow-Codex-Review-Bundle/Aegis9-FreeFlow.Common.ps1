Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-AegisStep {
    param([Parameter(Mandatory=$true)][string]$Message)
    Write-Host ""
    Write-Host "=== $Message ===" -ForegroundColor Cyan
}
function Write-AegisOk {
    param([Parameter(Mandatory=$true)][string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}
function Write-AegisWarn {
    param([Parameter(Mandatory=$true)][string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}
function Write-AegisFail {
    param([Parameter(Mandatory=$true)][string]$Message)
    Write-Host "[FAILED] $Message" -ForegroundColor Red
}

function Resolve-AegisRepoPath {
    param([Parameter(Mandatory=$true)][string]$RepoPath)

    $resolved = Resolve-Path -LiteralPath $RepoPath -ErrorAction Stop
    $path = $resolved.Path

    $gitRoot = (& git -C $path rev-parse --show-toplevel 2>$null)
    if (-not $gitRoot) {
        throw "'$path' is not a Git working tree."
    }
    return $gitRoot.Trim()
}

function Get-AegisBackendMain {
    param([Parameter(Mandatory=$true)][string]$RepoPath)

    $preferred = @(
        (Join-Path $RepoPath "backend\app\main.py"),
        (Join-Path $RepoPath "backend\main.py"),
        (Join-Path $RepoPath "app\main.py")
    )

    foreach ($candidate in $preferred) {
        if (Test-Path -LiteralPath $candidate) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    $candidates = @(Get-ChildItem -LiteralPath $RepoPath -Recurse -File -Filter "main.py" -ErrorAction SilentlyContinue |
        Where-Object {
            try {
                (Get-Content -LiteralPath $_.FullName -Raw -ErrorAction Stop) -match "FastAPI\s*\("
            } catch { $false }
        })

    if ($candidates.Count -eq 1) {
        return $candidates[0].FullName
    }

    if ($candidates.Count -gt 1) {
        $names = ($candidates | ForEach-Object FullName) -join "`n  "
        throw "Multiple FastAPI main.py files were found. Codex must select the correct application entry point:`n  $names"
    }

    throw "Could not locate the AEGIS FastAPI main.py."
}

function Get-AegisBackendAppDir {
    param([Parameter(Mandatory=$true)][string]$RepoPath)
    $main = Get-AegisBackendMain -RepoPath $RepoPath
    return (Split-Path -Parent $main)
}

function Get-AegisBackendRoot {
    param([Parameter(Mandatory=$true)][string]$RepoPath)
    $appDir = Get-AegisBackendAppDir -RepoPath $RepoPath
    return (Split-Path -Parent $appDir)
}

function Get-AegisDesktopProject {
    param([Parameter(Mandatory=$true)][string]$RepoPath)

    $preferred = @(
        (Join-Path $RepoPath "desktop\Jarvis.Desktop\Jarvis.Desktop.csproj"),
        (Join-Path $RepoPath "desktop\Aegis.Desktop\Aegis.Desktop.csproj"),
        (Join-Path $RepoPath "desktop\AEGIS.Desktop\AEGIS.Desktop.csproj")
    )
    foreach ($candidate in $preferred) {
        if (Test-Path -LiteralPath $candidate) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    $projects = @(Get-ChildItem -LiteralPath $RepoPath -Recurse -File -Filter "*.csproj" -ErrorAction SilentlyContinue |
        Where-Object {
            try {
                $t = Get-Content -LiteralPath $_.FullName -Raw
                ($t -match "<UseWPF>\s*true\s*</UseWPF>") -or ($_.Name -match "Desktop")
            } catch { $false }
        })

    if ($projects.Count -eq 1) {
        return $projects[0].FullName
    }
    if ($projects.Count -gt 1) {
        return $null
    }
    return $null
}

function Get-AegisRootNamespace {
    param([Parameter(Mandatory=$true)][string]$ProjectFile)

    $text = Get-Content -LiteralPath $ProjectFile -Raw
    $m = [regex]::Match($text, "<RootNamespace>\s*([^<]+)\s*</RootNamespace>", "IgnoreCase")
    if ($m.Success) {
        return $m.Groups[1].Value.Trim()
    }
    return [IO.Path]::GetFileNameWithoutExtension($ProjectFile)
}

function Get-AegisStateDir {
    param([Parameter(Mandatory=$true)][string]$RepoPath)
    $dir = Join-Path $RepoPath ".aegis-freeflow"
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    return $dir
}

function Backup-AegisFile {
    param(
        [Parameter(Mandatory=$true)][string]$RepoPath,
        [Parameter(Mandatory=$true)][string]$Path
    )
    if (-not (Test-Path -LiteralPath $Path)) { return $null }

    $state = Get-AegisStateDir -RepoPath $RepoPath
    $backupRoot = Join-Path $state "backups"
    if (-not (Test-Path -LiteralPath $backupRoot)) {
        New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
    }

    $relative = [IO.Path]::GetRelativePath($RepoPath, $Path)
    $safe = $relative -replace '[\\/:*?"<>|]', '_'
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $dest = Join-Path $backupRoot "$stamp-$safe"
    Copy-Item -LiteralPath $Path -Destination $dest -Force
    return $dest
}

function Test-AegisGeneratedFile {
    param([Parameter(Mandatory=$true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return $false }
    $first = Get-Content -LiteralPath $Path -TotalCount 5 -ErrorAction SilentlyContinue
    return (($first -join "`n") -match "AEGIS_FREEFLOW_GENERATED_V1")
}

function Write-AegisGeneratedFile {
    param(
        [Parameter(Mandatory=$true)][string]$RepoPath,
        [Parameter(Mandatory=$true)][string]$Path,
        [Parameter(Mandatory=$true)][string]$Content,
        [switch]$Apply,
        [switch]$ForceReplace
    )

    $relative = [IO.Path]::GetRelativePath($RepoPath, $Path)
    if (-not $Apply) {
        Write-Host "[DRY-RUN] Would write: $relative"
        return
    }

    if (Test-Path -LiteralPath $Path) {
        if ((Test-AegisGeneratedFile -Path $Path) -or $ForceReplace) {
            $backup = Backup-AegisFile -RepoPath $RepoPath -Path $Path
            Write-AegisWarn "Replacing '$relative'. Backup: $backup"
        } else {
            throw "Refusing to overwrite existing non-generated file '$relative'. Codex must review it or rerun with -ForceReplace."
        }
    }

    $dir = Split-Path -Parent $Path
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    Set-Content -LiteralPath $Path -Value $Content -Encoding UTF8
    Write-AegisOk "Wrote $relative"
}

function Get-AegisFastApiObjectName {
    param([Parameter(Mandatory=$true)][string]$MainPy)
    $text = Get-Content -LiteralPath $MainPy -Raw
    $m = [regex]::Match($text, "(?m)^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*FastAPI\s*\(")
    if (-not $m.Success) {
        throw "Could not determine the FastAPI application object in '$MainPy'."
    }
    return $m.Groups[1].Value
}

function Invoke-AegisJmfKnownDevices {
    param(
        [Parameter(Mandatory=$true)][string]$Url,
        [int]$TimeoutSeconds = 10
    )

    $id = "AEGIS-" + [guid]::NewGuid().ToString("N")
    $timestamp = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
    $xml = @"
<?xml version="1.0" encoding="UTF-8"?>
<JMF xmlns="http://www.CIP4.org/JDFSchema_1_1" SenderID="AEGIS9" TimeStamp="$timestamp" Version="1.3">
  <Query ID="$id" Type="KnownDevices"/>
</JMF>
"@

    $response = Invoke-WebRequest `
        -Uri $Url `
        -Method Post `
        -ContentType "application/vnd.cip4-jmf+xml" `
        -Body ([Text.Encoding]::UTF8.GetBytes($xml)) `
        -TimeoutSec $TimeoutSeconds `
        -UseBasicParsing

    return [pscustomobject]@{
        StatusCode = [int]$response.StatusCode
        Content    = $response.Content
        Request    = $xml
    }
}
