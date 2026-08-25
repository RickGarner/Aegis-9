param(
	[int]$Port = 8000,
	[switch]$NoInstall,
	[switch]$Activate
)

Write-Host "Starting Jarvis backend (FastAPI) — repo root will be detected from script location"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir

function Get-SystemPython {
	try { $null = & python --version 2>$null; if ($LASTEXITCODE -eq 0) { return 'python' } } catch {}
	try { $null = & py -3 --version 2>$null; if ($LASTEXITCODE -eq 0) { return 'py -3' } } catch {}
	return $null
}

function Start-Backend {
	param(
		[int]$Port = 8000,
		[switch]$NoInstall,
		[switch]$Activate
	)

	$systemPython = Get-SystemPython
	if (-not $systemPython) {
		Write-Error "Python was not found on PATH. Install Python 3 (https://www.python.org) or use winget: winget install --id Python.Python.3"
		return 1
	}

	Push-Location $repoRoot
	if (-not (Test-Path .venv)) {
		Write-Host "Creating virtual environment at $repoRoot\.venv"
		& $systemPython -m venv .venv
		if ($LASTEXITCODE -ne 0) { Write-Error "Failed to create virtual environment."; Pop-Location; return 1 }
	} else {
		Write-Host "Virtual environment .venv already exists."
	}

	$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
	$venvPip = Join-Path $repoRoot ".venv\Scripts\pip.exe"
	if (-not (Test-Path $venvPython)) { Write-Warning "Virtual environment python not found at $venvPython. Falling back to system python ($systemPython)."; $venvPython = $systemPython }

	if (-not $NoInstall) {
		if (Test-Path $venvPip) {
			Write-Host "Installing backend requirements from backend/requirements.txt"
			& $venvPip install -r (Join-Path $repoRoot "backend\requirements.txt")
			if ($LASTEXITCODE -ne 0) { Write-Warning "pip install returned non-zero exit code. Check output above." }
		} else {
			Write-Warning "pip not found in venv; attempting to use system pip."
			& $systemPython -m pip install -r (Join-Path $repoRoot "backend\requirements.txt")
		}
	} else { Write-Host "Skipping dependency install (NoInstall specified)." }

	if ($Activate) {
		Write-Host "Activating virtual environment in the current session."
		try { Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force } catch { Write-Warning "Unable to set execution policy; you may need to run PowerShell as Administrator to persist policy changes." }
		$activatePath = Join-Path $repoRoot ".venv\Scripts\Activate.ps1"
		if (Test-Path $activatePath) { Write-Host "Dot-sourcing: $activatePath"; . $activatePath; Write-Host "Virtual environment activated for this session." } else { Write-Warning "Activation script not found at $activatePath." }
	}

	Write-Host "Starting uvicorn (app.main:app) on http://127.0.0.1:$Port — press Ctrl+C to stop"
	Push-Location (Join-Path $repoRoot "backend")
	& $venvPython -m uvicorn app.main:app --host 127.0.0.1 --port $Port --app-dir backend
	Pop-Location
	Pop-Location
	return 0
}

# Execute when script is invoked
Start-Backend -Port $Port -NoInstall:$NoInstall -Activate:$Activate
