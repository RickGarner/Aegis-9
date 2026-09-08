[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$catalog = Get-Content -LiteralPath (Join-Path $repo 'config\mcp\catalog.json') -Raw | ConvertFrom-Json
if ($catalog.connectivityProfile -ne 'airgapped') { throw 'MCP catalog is not using the airgapped profile.' }
if (@($catalog.servers).Count -ne 0) { throw 'Air-gap baseline requires an empty MCP server catalog.' }
$proxyNames = 'HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy'
$present = $proxyNames | Where-Object { [Environment]::GetEnvironmentVariable($_) }
if ($present) { throw "Proxy variables must be cleared for the isolated test: $($present -join ', ')" }
$python = Join-Path $repo 'backend\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { $python = 'python' }
Push-Location (Join-Path $repo 'backend')
try { & $python -m pytest -q tests\test_mcp_registry.py tests\test_mcp_lifecycle.py tests\test_network_destination_policy.py tests\test_local_audit_dlp.py; if ($LASTEXITCODE) { throw 'Air-gap code-level acceptance tests failed.' } }
finally { Pop-Location }
Write-Output 'Code-level air-gap readiness passed. A separate firewall-isolated live DMR/Ollama run is still required.'
