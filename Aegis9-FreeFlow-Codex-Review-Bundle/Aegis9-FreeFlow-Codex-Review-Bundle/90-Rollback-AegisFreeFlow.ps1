[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$RepoPath,
    [switch]$Apply
)

. (Join-Path $PSScriptRoot "Aegis9-FreeFlow.Common.ps1")

$repo = Resolve-AegisRepoPath -RepoPath $RepoPath
$main = Get-AegisBackendMain -RepoPath $repo
$appDir = Get-AegisBackendAppDir -RepoPath $repo
$backendRoot = Get-AegisBackendRoot -RepoPath $repo
$desktopProject = Get-AegisDesktopProject -RepoPath $repo

$targets = @(
    (Join-Path $appDir "integrations\freeflow")
)
if ($desktopProject) {
    $targets += (Join-Path (Split-Path -Parent $desktopProject) "Integrations\FreeFlow")
}

Write-AegisStep ($(if ($Apply) { "Rolling back generated FreeFlow integration" } else { "Dry-run: FreeFlow rollback" }))

foreach ($dir in $targets) {
    if (Test-Path -LiteralPath $dir) {
        $nonGenerated = @(Get-ChildItem -LiteralPath $dir -Recurse -File | Where-Object {
            -not (Test-AegisGeneratedFile -Path $_.FullName)
        })
        if ($nonGenerated.Count -gt 0) {
            Write-AegisWarn "Refusing automatic removal of '$dir' because it contains files no longer marked as generated. Codex/manual review required."
        } else {
            if ($Apply) {
                Remove-Item -LiteralPath $dir -Recurse -Force
                Write-AegisOk "Removed $([IO.Path]::GetRelativePath($repo, $dir))"
            } else {
                Write-Host "[DRY-RUN] Would remove $([IO.Path]::GetRelativePath($repo, $dir))"
            }
        }
    }
}

# Remove main.py marker block.
$mainText = Get-Content -LiteralPath $main -Raw
$begin = [regex]::Escape("# BEGIN AEGIS FREEFLOW INTEGRATION")
$end = [regex]::Escape("# END AEGIS FREEFLOW INTEGRATION")
if ($mainText -match $begin) {
    if ($Apply) {
        [void](Backup-AegisFile -RepoPath $repo -Path $main)
        $newText = [regex]::Replace($mainText, "(?ms)^\s*$begin.*?^\s*$end\s*", "")
        Set-Content -LiteralPath $main -Value $newText -Encoding UTF8
        Write-AegisOk "Removed FastAPI router registration."
    } else {
        Write-Host "[DRY-RUN] Would remove FreeFlow marker block from $([IO.Path]::GetRelativePath($repo, $main))"
    }
}

# Remove only our .env marker block.
$envFile = Join-Path $backendRoot ".env"
if (Test-Path -LiteralPath $envFile) {
    $envText = Get-Content -LiteralPath $envFile -Raw
    $cb = [regex]::Escape("# BEGIN AEGIS FREEFLOW")
    $ce = [regex]::Escape("# END AEGIS FREEFLOW")
    if ($envText -match $cb) {
        if ($Apply) {
            [void](Backup-AegisFile -RepoPath $repo -Path $envFile)
            $newEnv = [regex]::Replace($envText, "(?ms)^\s*$cb.*?^\s*$ce\s*", "")
            Set-Content -LiteralPath $envFile -Value $newEnv -Encoding UTF8
            Write-AegisOk "Removed FreeFlow .env configuration block."
        } else {
            Write-Host "[DRY-RUN] Would remove FreeFlow .env marker block."
        }
    }
}

if (-not $Apply) {
    Write-AegisWarn "Rollback is dry-run only. Use -Apply only after reviewing the listed operations."
}
