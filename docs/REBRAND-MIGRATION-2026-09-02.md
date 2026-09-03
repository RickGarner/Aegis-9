# A.E.G.I.S.-9 repository and application migration

## New identity

- GitHub repository: `https://github.com/RickGarner/Aegis-9`
- Solution: `Aegis-9.sln`
- WPF project: `desktop/Aegis.Desktop/Aegis.Desktop.csproj`
- Executable: `Aegis.Desktop.exe`
- .NET namespace: `Aegis.Desktop`
- Local application data: `%LOCALAPPDATA%\Aegis-9`

The former `RickGarner/Jarvis-Desktop` repository was renamed in place, so its
full history, branches, issues, and tags are retained. The recovery tag before
the migration is `aegis9-pre-rebrand-2026-09-02`.

## Existing checkout migration

```powershell
git remote set-url origin https://github.com/RickGarner/Aegis-9.git
git fetch origin
git switch feature/workflow-automation-monitoring-2026-08-31
git pull --ff-only
dotnet restore Aegis-9.sln
dotnet build Aegis-9.sln --no-restore
```

User preferences automatically read the former `%LOCALAPPDATA%\Jarvis` settings
when the new settings file does not yet exist. The next save writes the settings
under `%LOCALAPPDATA%\Aegis-9`.

Historical database/configuration symbols and GLB animation clip names may retain
`Jarvis` identifiers where changing them would break existing data or third-party
assets. Those are compatibility identifiers, not the current product brand.

## Related repositories

- Developer IDE: `RickGarner/Aegis-Developer-Studio`
- Shared contracts/workspace: private `RickGarner/Aegis-Platform`
