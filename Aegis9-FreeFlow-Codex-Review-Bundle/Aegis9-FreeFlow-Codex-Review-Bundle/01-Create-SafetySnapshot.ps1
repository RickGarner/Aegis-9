[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$RepoPath,
    [switch]$AllowDirty
)

. (Join-Path $PSScriptRoot "Aegis9-FreeFlow.Common.ps1")

$repo = Resolve-AegisRepoPath -RepoPath $RepoPath
$state = Get-AegisStateDir -RepoPath $repo
$status = @(& git -C $repo status --porcelain)

if (($status.Count -gt 0) -and (-not $AllowDirty)) {
    throw "Repository is dirty. Codex should review local changes first. Rerun with -AllowDirty only if preserving a dirty tree is intentional."
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupRoot = Join-Path $state "snapshots\$stamp"
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null

(& git -C $repo rev-parse HEAD) | Set-Content (Join-Path $backupRoot "HEAD.txt")
(& git -C $repo branch --show-current) | Set-Content (Join-Path $backupRoot "BRANCH.txt")
(& git -C $repo status --porcelain=v1) | Set-Content (Join-Path $backupRoot "STATUS.txt")
(& git -C $repo diff --binary) | Set-Content (Join-Path $backupRoot "working-tree.patch")
(& git -C $repo diff --cached --binary) | Set-Content (Join-Path $backupRoot "index.patch")

$tracked = @(& git -C $repo ls-files)
$manifest = [ordered]@{
    generated_at = [DateTime]::UtcNow.ToString("o")
    repo = $repo
    head = ((& git -C $repo rev-parse HEAD).Trim())
    branch = ((& git -C $repo branch --show-current).Trim())
    dirty = ($status.Count -gt 0)
    tracked_file_count = $tracked.Count
}
$manifest | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $backupRoot "snapshot.json") -Encoding UTF8

Write-AegisOk "Safety snapshot created: $backupRoot"
Write-AegisWarn "This is a source-state snapshot and patch record, not a replacement for your Git remote or normal backups."
