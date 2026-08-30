param(
    [Parameter(Mandatory)] [string]$LmsPath,
    [int]$Port = 1234
)

$ErrorActionPreference = 'Stop'
$logRoot = Join-Path $PSScriptRoot 'logs'
New-Item -ItemType Directory -Force -Path $logRoot | Out-Null

while ($true) {
    try {
        & $LmsPath daemon up --json | Out-File (Join-Path $logRoot 'lmstudio-daemon.log') -Append -Encoding utf8
        & $LmsPath server start --port $Port | Out-File (Join-Path $logRoot 'lmstudio-server.log') -Append -Encoding utf8
        Start-Sleep -Seconds 15
        Invoke-RestMethod -Uri "http://127.0.0.1:$Port/v1/models" -TimeoutSec 10 | Out-Null
    }
    catch {
        "$(Get-Date -Format o) $($_.Exception.Message)" | Out-File (Join-Path $logRoot 'lmstudio-error.log') -Append -Encoding utf8
    }
    Start-Sleep -Seconds 15
}
