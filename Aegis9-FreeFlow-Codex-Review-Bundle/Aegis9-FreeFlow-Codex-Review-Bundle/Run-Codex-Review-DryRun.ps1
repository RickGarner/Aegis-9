[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$RepoPath,
    [string]$FreeFlowHost
)

$ErrorActionPreference = "Stop"

$preflight = Join-Path $PSScriptRoot "00-Preflight-AegisFreeFlow.ps1"
$backend = Join-Path $PSScriptRoot "02-Install-FreeFlowBackend.ps1"
$register = Join-Path $PSScriptRoot "03-Register-FreeFlowBackend.ps1"
$desktop = Join-Path $PSScriptRoot "04-Install-FreeFlowDesktopClient.ps1"

if ($FreeFlowHost) {
    & $preflight -RepoPath $RepoPath -FreeFlowHost $FreeFlowHost
} else {
    & $preflight -RepoPath $RepoPath
}
& $backend -RepoPath $RepoPath
& $register -RepoPath $RepoPath
& $desktop -RepoPath $RepoPath

Write-Host ""
Write-Host "Codex review sequence complete. No Apply switches were used." -ForegroundColor Green
