param(
	[string]$BranchName = 'native/packaging-and-porting'
)

Write-Host "Creating branch $BranchName and moving frontend to archive/frontend (preserve history if possible)..."

git status --porcelain | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Error "Not a git repository or git is not available."; exit 1 }

git checkout -b $BranchName
if ($LASTEXITCODE -ne 0) { Write-Error "Failed to create branch."; exit 1 }

if (Test-Path frontend) {
	git mv frontend archive/frontend
	git commit -m "archive: move frontend to archive/frontend (preserve history)"
	Write-Host "frontend moved to archive/frontend and committed."
} else {
	Write-Host "frontend folder not found; skipping move."
}

Write-Host "Staging changes and creating initial migration commit for code changes..."
git add .
git commit -m "chore(migration): add backend launcher, app startup integration, and health check" -a
Write-Host "Committed migration changes. Push branch when ready: git push -u origin $BranchName"
