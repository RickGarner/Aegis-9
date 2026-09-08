[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$RepoPath,
    [string]$FreeFlowHost,
    [int]$JmfPort = 7751,
    [string]$JmfPath = "/FreeFlowCore"
)

. (Join-Path $PSScriptRoot "Aegis9-FreeFlow.Common.ps1")

Write-AegisStep "AEGIS 9 / FreeFlow Core preflight"
$repo = Resolve-AegisRepoPath -RepoPath $RepoPath
$state = Get-AegisStateDir -RepoPath $repo

$branch = (& git -C $repo branch --show-current).Trim()
$commit = (& git -C $repo rev-parse HEAD).Trim()
$status = @(& git -C $repo status --porcelain)

$main = $null
$backendApp = $null
$desktop = $null
$fastApiObject = $null

try {
    $main = Get-AegisBackendMain -RepoPath $repo
    $backendApp = Split-Path -Parent $main
    $fastApiObject = Get-AegisFastApiObjectName -MainPy $main
    Write-AegisOk "FastAPI entry point: $([IO.Path]::GetRelativePath($repo, $main)) ($fastApiObject)"
} catch {
    Write-AegisWarn $_.Exception.Message
}

$desktop = Get-AegisDesktopProject -RepoPath $repo
if ($desktop) {
    Write-AegisOk "Desktop project: $([IO.Path]::GetRelativePath($repo, $desktop))"
} else {
    Write-AegisWarn "Desktop project was not uniquely detected. Codex must identify the active WPF project."
}

$gitVersion = (& git --version)
$pythonVersion = $null
$dotnetVersion = $null
try { $pythonVersion = (& python --version 2>&1) } catch {}
try { $dotnetVersion = (& dotnet --version 2>&1) } catch {}

$jmf = $null
if ($FreeFlowHost) {
    $url = "http://$FreeFlowHost`:$JmfPort$JmfPath"
    Write-AegisStep "Testing FreeFlow JMF endpoint $url"
    try {
        $jmfResult = Invoke-AegisJmfKnownDevices -Url $url
        $jmf = @{
            url = $url
            reachable = $true
            status_code = $jmfResult.StatusCode
            contains_jmf = ($jmfResult.Content -match "<(?:\w+:)?JMF\b")
            response_preview = $jmfResult.Content.Substring(0, [Math]::Min(1000, $jmfResult.Content.Length))
        }
        Write-AegisOk "JMF KnownDevices returned HTTP $($jmfResult.StatusCode)."
    } catch {
        $jmf = @{
            url = $url
            reachable = $false
            error = $_.Exception.Message
        }
        Write-AegisWarn "JMF test failed: $($_.Exception.Message)"
    }
}

$report = [ordered]@{
    generated_at = [DateTime]::UtcNow.ToString("o")
    repo_path = $repo
    branch = $branch
    commit = $commit
    dirty = ($status.Count -gt 0)
    git_status = $status
    git_version = $gitVersion
    python_version = $pythonVersion
    dotnet_version = $dotnetVersion
    fastapi_main = $main
    fastapi_object = $fastApiObject
    backend_app_dir = $backendApp
    desktop_project = $desktop
    jmf = $jmf
}

$out = Join-Path $state ("preflight-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".json")
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $out -Encoding UTF8

Write-Host ""
Write-Host "Repository : $repo"
Write-Host "Branch     : $branch"
Write-Host "Commit     : $commit"
Write-Host "Dirty      : $($report.dirty)"
Write-Host "Report     : $out"

if ($report.dirty) {
    Write-AegisWarn "The repository has local changes. Do not run Apply-mode installation until Codex has reviewed the working tree."
}
