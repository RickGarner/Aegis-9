# Aegis Developer Studio

## Decision and status

**Product decision: approved. Integration status: planned. First milestone: pending implementation.**

Aegis Developer Studio is the approved name for the local development environment
that will be launched and supervised from A.E.G.I.S.-9. The existing WolfForge
Code - OSS fork is the implementation foundation; a second editor will not be
created from scratch.

The source repositories remain separate:

- `Jarvis-Desktop` owns the Aegis slide-out panel, launch controls, approvals,
  audit records, build/test evidence, and workflow integration.
- `RickGarner/VSCode` currently owns WolfForge and will become the Aegis
  Developer Studio IDE. Its repository/product rename will be handled as a
  separate, deliberate migration after integration is stable.

No Aegis Developer Studio production code has been added to Jarvis-Desktop yet.

## Product identity

- Full name: **Aegis Developer Studio**
- Aegis navigation label: **Developer Studio**
- Short internal name: **ADS**
- Local coding and reasoning assistant: **FERAL** — Federated Execution,
  Reasoning, and Adaptive Learning

Aegis 9 remains the operations, governance, workflow, and monitoring surface.
Aegis Developer Studio provides the dedicated software-development experience.
FERAL provides local AI assistance across both products.

## User experience

Developer Studio begins as a slide-out panel in the Aegis command center. The
panel is the launcher and ongoing control surface, not an embedded copy of the
entire Electron workbench.

The initial panel will provide:

- recent folders and Git repositories
- browse/open-folder and open-repository actions
- local AI provider and selected-model status
- Aegis Developer Studio installed/running state
- an **Open Developer Studio** action
- the active IDE session and repository
- build/test status and pending approval summaries as those integrations arrive

Opening a repository launches the full Code - OSS-based IDE in its own native
window. Keeping the editor in a separate process preserves its full editor,
terminal, debugging, extension, and window-management capabilities. The Aegis
panel remains available for status, governance, approvals, and reopening or
focusing the IDE.

Eventually, an approved workflow at Implementation Review may open Developer
Studio directly on its retained implementation/artifact directory.

## Existing foundation — completed in WolfForge

The WolfForge repository already contains a substantial local-first foundation:

- branded standalone Code - OSS desktop application
- LM Studio, Ollama, LiteLLM, and custom OpenAI-compatible providers
- repository-aware chat, planning, editing, review, and test modes
- file search/read/create/edit and confirmed multi-file edits
- repository maps and memory, symbol/context retrieval, diagnostics, Git context,
  change-impact analysis, and validation recipes
- approved command execution with timeouts
- PowerShell syntax validation
- support for large C# and VB.NET inputs and conversion prompts

These capabilities are an existing external-project foundation, not completed
Jarvis-Desktop integration work.

## Required capabilities and remaining work

- complete WolfForge Local-Only Mode and make Local AI the default
- disable or remove Copilot-owned default paths, cloud model choices, prompt
  egress, and relevant cloud telemetry/authentication in local-only operation
- add Aegis slide-out panel and persisted recent-repository state
- discover, launch, focus, and monitor the separate IDE process safely
- define a versioned, authenticated local bridge between Aegis and the IDE
- add explicit rename, move, and delete tools with confirmation and rollback
- create Visual Studio solution/project scaffolding
- add structured PowerShell creation and C#/VB.NET conversion workflows
- connect builds/tests to Aegis retained output, artifact hashing, permissions,
  safe profiles, timeouts, and audit history
- require the applicable user, BSOC developer, and supervisor approvals before
  generated or converted software reaches an operational environment
- validate local-only behavior with an outbound-egress acceptance test

GitHub Copilot is not required for the target design.

## Model-hosting direction

Use the existing private AI workstation and provider-neutral interfaces. LiteLLM
is the preferred stable routing endpoint, with LM Studio and Ollama available as
local backends according to model capability. Developer Studio must clearly show
the selected endpoint/model and must not silently fall back to a cloud provider.

## Delivery milestones

1. **Slide-out foundation — pending:** add the Developer Studio navigation and
   slide-out panel with placeholder status, recent repositories, folder browsing,
   and launch-ready view models.
2. **Safe launcher — pending:** configure the executable, validate paths, launch
   or focus one IDE session, pass the selected repository, and report process
   state without terminating unrelated processes.
3. **Local bridge — pending:** authenticated session/status contract, provider
   health, active repository, activity, and approval messages.
4. **Governed development — pending:** file-operation approvals, scaffolding,
   conversion pipelines, build/test evidence, repair loops, and workflow handoff.
5. **Local-only release gate — pending:** Copilot independence, cloud-egress
   controls, privacy tests, packaging, and multi-computer installation validation.

## Immediate next action

Implement milestone 1 in the native WPF command center. The slide-out should be
useful before IDE launch is wired: it must open and close cleanly, fit the
cinematic Aegis visual language, expose repository selection and status fields,
and present disabled or explanatory controls for capabilities scheduled in later
milestones.
