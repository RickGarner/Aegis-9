[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$RepoPath,
    [Parameter(Mandatory=$true)][string]$FreeFlowHost,
    [int]$JmfPort = 7751,
    [string]$JmfPath = "/FreeFlowCore",
    [switch]$EnableStatusQuery,
    [switch]$Apply
)

. (Join-Path $PSScriptRoot "Aegis9-FreeFlow.Common.ps1")

$repo = Resolve-AegisRepoPath -RepoPath $RepoPath
$backendRoot = Get-AegisBackendRoot -RepoPath $repo
$envFile = Join-Path $backendRoot ".env"

$begin = "# BEGIN AEGIS FREEFLOW"
$end = "# END AEGIS FREEFLOW"
$baseUrl = "http://$FreeFlowHost`:$JmfPort$JmfPath"

$block = @"
$begin
AEGIS_FREEFLOW_ENABLED=true
AEGIS_FREEFLOW_BASE_URL=$baseUrl
AEGIS_FREEFLOW_TIMEOUT_SECONDS=10
AEGIS_FREEFLOW_VERIFY_TLS=true
AEGIS_FREEFLOW_ENABLE_STATUS_QUERY=$($EnableStatusQuery.ToString().ToLowerInvariant())
AEGIS_FREEFLOW_ALLOW_MUTATIONS=false
$end
"@

Write-AegisStep ($(if ($Apply) { "Writing FreeFlow configuration" } else { "Dry-run: FreeFlow configuration" }))
Write-Host "Environment file: $envFile"
Write-Host $block

if (-not $Apply) {
    Write-AegisWarn "No configuration was modified."
    exit 0
}

$text = ""
if (Test-Path -LiteralPath $envFile) {
    $text = Get-Content -LiteralPath $envFile -Raw
    [void](Backup-AegisFile -RepoPath $repo -Path $envFile)
}

if ($text -match [regex]::Escape($begin)) {
    $escapedBegin = [regex]::Escape($begin)
    $escapedEnd = [regex]::Escape($end)
    $text = [regex]::Replace($text, "(?ms)^$escapedBegin.*?^$escapedEnd\s*", "")
}

if ($text -and (-not $text.EndsWith("`n"))) { $text += "`r`n" }
$text += "`r`n$block`r`n"
Set-Content -LiteralPath $envFile -Value $text -Encoding UTF8

Write-AegisOk "FreeFlow configuration written with mutations disabled."
if ($EnableStatusQuery) {
    Write-AegisWarn "Status/QueueInfo was enabled by explicit request. Codex must confirm this against the installed FreeFlow SDK/version."
}
