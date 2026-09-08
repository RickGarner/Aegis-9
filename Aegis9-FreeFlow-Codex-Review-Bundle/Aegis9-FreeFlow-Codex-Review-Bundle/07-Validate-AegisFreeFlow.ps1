[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$RepoPath,
    [string]$BackendUrl,
    [switch]$SkipDotNetBuild
)

. (Join-Path $PSScriptRoot "Aegis9-FreeFlow.Common.ps1")

$repo = Resolve-AegisRepoPath -RepoPath $RepoPath
$appDir = Get-AegisBackendAppDir -RepoPath $repo
$backendRoot = Get-AegisBackendRoot -RepoPath $repo
$freeflow = Join-Path $appDir "integrations\freeflow"

Write-AegisStep "Validating generated backend module"
if (-not (Test-Path -LiteralPath $freeflow)) {
    throw "FreeFlow backend module is not installed at $freeflow."
}

Push-Location $backendRoot
try {
    & python -m compileall $freeflow -q
    if ($LASTEXITCODE -ne 0) { throw "Python compileall failed." }

    $relativeTest = [IO.Path]::GetRelativePath($backendRoot, (Join-Path $freeflow "test_jmf.py"))
    $module = $relativeTest.Replace("\", ".").Replace("/", ".")
    if ($module.EndsWith(".py")) { $module = $module.Substring(0, $module.Length - 3) }
    & python -m unittest $module
    if ($LASTEXITCODE -ne 0) { throw "FreeFlow JMF unit tests failed." }

    Write-AegisOk "Backend compile and unit tests passed."
}
finally {
    Pop-Location
}

if (-not $SkipDotNetBuild) {
    $project = Get-AegisDesktopProject -RepoPath $repo
    if ($project) {
        Write-AegisStep "Building AEGIS desktop project"
        & dotnet build $project --no-restore
        if ($LASTEXITCODE -ne 0) {
            throw "Desktop build failed."
        }
        Write-AegisOk "Desktop build passed."
    } else {
        Write-AegisWarn "Desktop project was not uniquely detected; skipping .NET build."
    }
}

if ($BackendUrl) {
    $base = $BackendUrl.TrimEnd("/")
    Write-AegisStep "Testing live AEGIS FreeFlow API"
    $status = Invoke-RestMethod -Uri "$base/api/integrations/freeflow/status" -Method Get
    $caps = Invoke-RestMethod -Uri "$base/api/integrations/freeflow/capabilities" -Method Get

    Write-Host ($status | ConvertTo-Json -Depth 8)
    Write-Host ($caps | ConvertTo-Json -Depth 8)

    if ($status.enabled -and $status.healthy) {
        $devices = Invoke-RestMethod -Uri "$base/api/integrations/freeflow/devices" -Method Get
        Write-AegisOk "Live backend reached FreeFlow Core. Devices returned: $($devices.devices.Count)"
    } else {
        Write-AegisWarn "Backend endpoint responded, but FreeFlow is disabled or not healthy."
    }
}

Write-AegisOk "Validation completed."
