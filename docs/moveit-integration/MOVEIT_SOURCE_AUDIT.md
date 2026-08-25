# MoveIT Source Audit

## Original source location

`D:\BSOC_CodeRepository\DEV\Src\DotNet\BSOC\Jarvis`

## Build result

The original solution builds successfully with .NET 8 using `dotnet build Jarvis.slnx --no-restore`.

The build has seven existing warnings in `UI/MainWindow.xaml.cs` involving nullable fields and one unused local variable. No MoveIT compile errors were reported.

## Reusable components

| Original component | Reuse in current Jarvis |
|---|---|
| `MoveITService.cs` | Protocol and endpoint reference; port as a typed async Python client |
| `MoveITTaskTool.cs` | Task-name command patterns and manual execution semantics |
| `AppConfiguration.cs` | Configuration fields and task mapping shape |
| MoveIT fix documentation | Authentication/content type and task-trigger evidence |
| ServerMonitoring sibling solution | Server metric models, threshold concepts, email/alert architecture |

## Not copied intentionally

- `Configuration/appsettings.json` credentials
- Any bearer tokens or authentication response bodies
- The original certificate-validation bypass
- The original plaintext-password fallback behavior
- Unverified endpoint-discovery output

## Security actions required before production

- Rotate the credential that was present in the original configuration.
- Move credentials to Windows Credential Manager, environment variables, or a secrets provider.
- Use a configured internal CA certificate instead of disabling TLS validation.
- Redact authentication headers, passwords, tokens, and raw auth responses from logs.
- Add audit records for operator-triggered actions.

## Related server-monitoring source

The repository history contains a separate solution at:

`D:\BSOC_CodeRepository\DEV\Src\DotNet\BSOC\ServerMonitoring`

The historical commit `041dda5b` contains the agent, hub, dashboard, shared metric models, threshold handling, Windows service monitoring, SQLite persistence, GPU support, and email alerting. It should be treated as a separate source of server-monitoring contracts, not as part of the original WPF Jarvis project.
