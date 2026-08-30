param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path,
    [switch]$SkipLMStudio
)

$ErrorActionPreference = 'Continue'
$failed = $false

function Test-Endpoint([string]$Name, [string]$Uri) {
    try {
        Invoke-RestMethod -Uri $Uri -TimeoutSec 15 | Out-Null
        Write-Host "[PASS] $Name - $Uri" -ForegroundColor Green
    }
    catch {
        Write-Host "[FAIL] $Name - $($_.Exception.Message)" -ForegroundColor Red
        $script:failed = $true
    }
}

$serviceNames = @('Ollama','LiteLLM','Aegis9Kokoro')
if (-not $SkipLMStudio) { $serviceNames += 'Aegis9LMStudio' }
foreach ($serviceName in $serviceNames) {
    $service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
    if ($service -and $service.Status -eq 'Running') {
        Write-Host "[PASS] Service $serviceName is running" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] Service $serviceName is missing or stopped" -ForegroundColor Red
        $failed = $true
    }
}

Test-Endpoint 'Ollama' 'http://127.0.0.1:11434/api/tags'
Test-Endpoint 'LiteLLM' 'http://127.0.0.1:4000/health/liveliness'
if (-not $SkipLMStudio) { Test-Endpoint 'LM Studio' 'http://127.0.0.1:1234/v1/models' }
Test-Endpoint 'Kokoro' 'http://127.0.0.1:5050/health'

Push-Location $RepoRoot
try {
    & dotnet build Jarvis.sln --no-restore
    if ($LASTEXITCODE -ne 0) { $failed = $true }
    Push-Location backend
    & ..\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_*.py'
    if ($LASTEXITCODE -ne 0) { $failed = $true }
    Pop-Location
}
finally {
    Pop-Location
}

if ($failed) { throw 'One or more A.E.G.I.S.-9 workstation checks failed.' }
Write-Host 'A.E.G.I.S.-9 workstation validation passed.' -ForegroundColor Green
