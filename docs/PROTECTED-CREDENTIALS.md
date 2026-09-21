# Protected credentials

A.E.G.I.S.-9 uses current-user Windows Credential Manager Generic Credentials.
Secrets are not accepted as command-line arguments, printed, logged, committed,
or returned by the status command.

The default target is the approved MOVEit reader,
`Aegis-9/MoveIT/ReadOnly`. From the repository root:

```powershell
.\.venv\Scripts\python.exe backend\scripts\manage_credential.py status
.\.venv\Scripts\python.exe backend\scripts\manage_credential.py set
.\.venv\Scripts\python.exe backend\scripts\manage_credential.py delete
```

`set` privately prompts for the username, password, and password confirmation.
Only an identity with the `credentials.manage` capability can use the command.
Use `--target Aegis-9/SMTP/Alerts` when the alert relay requires authentication.
Credentialed HTTP MCP catalog entries use a non-secret `credentialRef` and an
explicit `credentialAuth` of `basic` or `bearer`. The corresponding protected
target is `Aegis-9/MCP/<credentialRef>`. Credential material is added only to
the HTTP Authorization header at request time and is excluded from MCP payloads
and audit records. Credentialed stdio MCP processes remain unsupported.
Every target must remain in the `Aegis-9/` namespace. The entry is scoped to the
Windows user and local machine. Use separate target
names for separate systems, environments, and privilege levels. A credential
reference grants no authorization by itself; adapters must still enforce their
approved endpoint, operation, role, and data scope.

Environment-variable username/password settings remain a temporary compatibility
fallback only when the protected target is not present. Credential Manager access
errors fail closed and do not fall back to plaintext settings. New deployments
should use protected targets and should not place passwords in `.env`.
