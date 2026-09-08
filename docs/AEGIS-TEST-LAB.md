# A.E.G.I.S. Test Lab

**Status:** implemented safe first release; Windows Sandbox acceptance passed on the current Windows 11 Enterprise workstation on 2026-09-07.  
**Products:** A.E.G.I.S.-9 and Aegis Developer Studio  
**Mode:** local/offline by default

## Purpose

Test Lab lets an operator review PowerShell or C# source, generate a bounded test plan and synthetic inputs, approve an immutable test package, and launch that package in a disposable Windows Sandbox. Package creation never executes the submitted code. Sandbox launch requires a separate explicit approval.

## Operator flow

1. Select source. A.E.G.I.S.-9 accepts a supported file up to 500 KB; the backend enforces 100 files and 2 MB total for API callers.
2. Create plan. Deterministic rules identify destructive filesystem, remote execution, system mutation, network, database, process, and environment access. A.E.G.I.S.-9 may ask the configured local DMR/Ollama model for additional synthetic cases; model failure falls back safely to deterministic cases.
3. Review and approve the package. The service recomputes the safety assessment and refuses a stale plan whose risk or capabilities changed.
4. Launch Windows Sandbox with a second confirmation.
5. Close the sandbox and select **Review Evidence**. Results are parsed as JSON before display.

Developer Studio exposes the same independent flow through the command palette: **Create Aegis Test Lab Plan**, **Launch Approved Aegis Test Lab**, and **Review Aegis Test Lab Evidence**.

## Enforced boundary

- Windows Sandbox networking, clipboard, printer, audio input, and video input are disabled.
- Protected Client mode is enabled.
- Original source is copied into a package and mounted read-only. The workspace is never mapped into the sandbox.
- Only the package output directory is writable from the sandbox.
- Credentials are not supplied by Test Lab.
- Source SHA-256 hashes, the plan ID, test data, and capability restrictions are recorded in the manifest.
- PowerShell is parsed without executing the submitted script.
- C# projects use `dotnet build --no-restore`; missing offline SDK/runtime support produces a failed evidence item instead of enabling network restore.

## Important limits

Test Lab reduces risk; it does not prove arbitrary code safe. Windows Sandbox is the security boundary, not the AI review or regular-expression scanner. This release does not execute submitted PowerShell scripts, connect to production dependencies, inject credentials, or enable network access. Behavioral execution requires a separately reviewed harness that invokes only an approved entry point against synthetic fixtures. C# compilation requires the disposable environment to contain an approved offline .NET SDK and already-available dependencies.

Do not use Test Lab for malware analysis, kernel drivers, code requiring production identity, or tests that must contact real infrastructure. Those require a separately administered disposable VM/lab profile.

## Storage and configuration

A.E.G.I.S.-9 stores packages under `JARVIS_TEST_LAB_ROOT` (default `storage/test-lab`). Each plan has its own `input`, `output`, manifest, runner, and `.wsb` file. Developer Studio stores packages beneath its extension global-storage directory. Packages may contain source and test evidence and must follow the workstation retention policy.

## Acceptance checklist

- [x] Enable the optional Windows Sandbox feature and confirm `WindowsSandbox.exe` exists on the current workstation.
- [x] Create a harmless PowerShell plan and inspect its manifest and enforced capability values.
- [x] Launch the generated network-disabled, clipboard-disabled profile and confirm `output/evidence.json` appears.
- [x] Confirm the harmless PowerShell source and Test Lab runner pass parser validation inside Windows Sandbox.
- [x] Confirm only the package input is mapped read-only and only the dedicated evidence directory is mapped writable; the source workspace is not mapped.
- For C#, confirm the approved offline SDK and dependencies are present; otherwise confirm the run fails closed.

### Current-workstation acceptance evidence

Acceptance plan `b1a46650-ef9f-44cc-9104-1f9d88b9bf5a` ran on 2026-09-07. The generated manifest recorded `network=false`, `clipboard=false`, `hostWrite=false`, and `credentials=false`. Windows Sandbox produced a valid `evidence.json` with successful parser results for the harmless acceptance script and the generated runner. The evidence package is retained under `%LOCALAPPDATA%\Aegis\TestLabAcceptance` for local review. This validates the installed feature and configured boundary on this workstation; it is not a general proof that arbitrary code is safe.
