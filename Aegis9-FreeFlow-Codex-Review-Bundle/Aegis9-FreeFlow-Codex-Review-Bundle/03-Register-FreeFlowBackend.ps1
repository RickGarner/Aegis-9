[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$RepoPath,
    [switch]$Apply
)

. (Join-Path $PSScriptRoot "Aegis9-FreeFlow.Common.ps1")

$repo = Resolve-AegisRepoPath -RepoPath $RepoPath
$main = Get-AegisBackendMain -RepoPath $repo
$appObject = Get-AegisFastApiObjectName -MainPy $main
$text = Get-Content -LiteralPath $main -Raw

$begin = "# BEGIN AEGIS FREEFLOW INTEGRATION"
$end = "# END AEGIS FREEFLOW INTEGRATION"

if ($text.Contains($begin)) {
    Write-AegisOk "FreeFlow registration marker already exists in $([IO.Path]::GetRelativePath($repo, $main))."
    exit 0
}

$block = @"

$begin
try:
    from app.integrations.freeflow.api import router as freeflow_router
except ImportError:
    from .integrations.freeflow.api import router as freeflow_router

$appObject.include_router(freeflow_router)
$end
"@

Write-AegisStep ($(if ($Apply) { "Registering FreeFlow FastAPI router" } else { "Dry-run: FreeFlow FastAPI router registration" }))
Write-Host "File       : $([IO.Path]::GetRelativePath($repo, $main))"
Write-Host "FastAPI app: $appObject"
Write-Host ""
Write-Host $block

if (-not $Apply) {
    Write-AegisWarn "No source was modified. Codex should confirm this repository does not already use a central router/registry that is preferable."
    exit 0
}

$backup = Backup-AegisFile -RepoPath $repo -Path $main

$mainGuardPattern = '(?m)^\s*if\s+__name__\s*==\s*["'']__main__["'']\s*:'
$guard = [regex]::Match($text, $mainGuardPattern)

if ($guard.Success) {
    $updated = $text.Insert($guard.Index, ($block + "`r`n"))
    Set-Content -LiteralPath $main -Value $updated -Encoding UTF8
    Write-AegisOk "Router registration inserted before the Python __main__ block. Backup: $backup"
} else {
    Add-Content -LiteralPath $main -Value $block -Encoding UTF8
    Write-AegisOk "Router registration appended to module scope. Backup: $backup"
}
