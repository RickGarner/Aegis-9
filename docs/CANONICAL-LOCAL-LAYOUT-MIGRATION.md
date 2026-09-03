# Canonical local layout migration

## Decision

All active Aegis repositories will use fresh, independent clones under:

```text
D:\Aegis\
├── Aegis-9\
├── Aegis-Developer-Studio\
└── Aegis-Platform\
```

The existing `D:\Jarvis-Cinematic-Verify` and `D:\development\vscode` folders
remain temporary recovery copies. They must not be deleted until both fresh
clones pass build, test, launch, and cross-application discovery checks.

## Migration procedure

1. Push and verify all three repositories.
2. Remove only the temporary `D:\Aegis\Aegis-9` and
   `D:\Aegis\Aegis-Developer-Studio` directory junctions.
3. Clone the renamed repositories into those exact paths.
4. Restore machine-local `.env` values without committing them.
5. Restore .NET, Python, Node, and Electron dependencies from source manifests.
6. Build and test both fresh clones.
7. Verify A.E.G.I.S.-9 discovers and launches Developer Studio from the sibling
   canonical path.
8. Retain the old folders as rollback sources until a later explicit cleanup.

Do not copy `bin`, `obj`, `.venv`, `node_modules`, `.build`, databases, model
caches, or user preferences into the fresh clones. Workflow transfer packages
and databases are operational data and are migrated separately when needed.

## Completion record — 2026-09-02

The migration is complete and verified on this workstation:

- `D:\Aegis\Aegis-9` is an independent clone on
  `feature/workflow-automation-monitoring-2026-08-31`.
- The machine-local `.env` was restored without committing it; the Python
  virtual environment and .NET outputs were rebuilt from manifests.
- Developer Studio discovery now defaults to the canonical sibling path,
  `D:\Aegis\Aegis-Developer-Studio`.
- 43 backend tests pass and `Aegis-9.sln` builds with zero errors.
- `Aegis.Desktop.exe` launches successfully from the canonical clone.
- The old checkout remains at `D:\Jarvis-Cinematic-Verify`. A reversible link
  named `D:\Aegis\Aegis-9.previous-location-link` points to it for recovery.

The recovery checkout and link are not active development locations and should
only be removed by a later, explicit cleanup decision.
