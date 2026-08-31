# Manual development transfer by ZIP and USB drive

## Purpose

`Aegis9-Development-Transfer-2026-08-31.zip` is a portable development copy of
the current A.E.G.I.S.-9 application. It can be copied to a USB drive, moved to
another Windows computer, extracted into a new folder, and used to continue
development without downloading the project source from GitHub.

The archive is generated from the canonical branch:

```text
feature/workflow-automation-monitoring-2026-08-31
```

## Included

- Visual Studio solution and native cinematic WPF application
- FastAPI backend source and requirements
- Avatar runtime and tracked application assets
- Configuration templates and non-secret server inventory
- Windows dependency, service, installation, and validation scripts
- Backend tests
- Current handoff, implementation, migration, architecture, and requirements
  documents
- `_transfer/Jarvis-Desktop-full-history.bundle`, containing Git commit and
  branch history for offline repository restoration

## Intentionally excluded

The following are machine-specific, sensitive, generated, or reproducible and
are intentionally not transferred through the ZIP:

- `.env`, passwords, API keys, tokens, or other credentials
- SQLite databases, chat history, workflow runtime state, and monitoring history
- Uploaded documents and generated workflow artifacts
- Python virtual environments
- .NET build output
- Ollama, LM Studio, Kokoro, or other model/runtime caches
- Logs and user preferences
- live `.git` working-directory metadata

These exclusions do not remove application source. They must be installed,
generated, or configured on the destination computer.

## Destination-computer procedure

1. Copy the ZIP from the USB drive into a new local development folder.
2. Extract the entire ZIP while preserving its folder structure.
3. Read:
   - `docs/CURRENT-VERSION.md`
   - `docs/handoff.md`
   - `docs/MIGRATION-2026-08-31.md`
   - this document
4. Open Windows PowerShell as Administrator and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\deployment\windows\Install-Aegis9Workstation.ps1 -ModelProfile Core
```

5. Copy `.env.example` to `.env` and enter only the destination computer's
   approved local URLs, accounts, and secrets. Never commit `.env`.
6. Validate the workstation and source:

```powershell
.\deployment\windows\Test-Aegis9Workstation.ps1
py -m pytest backend/tests -q
dotnet build Jarvis.sln
```

## Restore Git history without GitHub

The extracted source tree is ready to inspect and build, but it does not contain
a live `.git` directory. To restore a complete local Git repository from the
included bundle, run these commands from the parent directory where the restored
repository should be created:

```powershell
git clone .\ExtractedAegisFolder\_transfer\Jarvis-Desktop-full-history.bundle Jarvis-Desktop-Restored
Set-Location Jarvis-Desktop-Restored
git switch feature/workflow-automation-monitoring-2026-08-31
git status --short --branch
```

The Git-restored folder is the preferred place to continue editing because it
retains prior commits and recovery branches. Copy only a destination-specific
`.env` into it; do not copy build output or virtual environments.

## If GitHub is available

Cloning the pushed branch is simpler and avoids copying source twice:

```powershell
git clone --branch feature/workflow-automation-monitoring-2026-08-31 https://github.com/RickGarner/Jarvis-Desktop.git
Set-Location Jarvis-Desktop
git status --short --branch
```

The USB ZIP remains the offline recovery and manual-transfer option.

## Integrity check

After copying the ZIP, compare its SHA-256 hash with the value supplied at the
time the archive was created:

```powershell
Get-FileHash .\Aegis9-Development-Transfer-2026-08-31.zip -Algorithm SHA256
```

If the values differ, recopy the archive before extracting it.
