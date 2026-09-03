# Aegis Developer Studio

## Decision and status

**Product decision: approved. Integration status: in progress. Milestone 1 accepted; milestone 2 implemented and awaiting runtime acceptance.**

Aegis Developer Studio is the approved name for the local development environment
that will be launched and supervised from A.E.G.I.S.-9. The renamed Aegis
Developer Studio Code - OSS fork is the implementation foundation; a second editor will not be
created from scratch.

The source repositories remain separate:

- `Aegis-9` owns the Aegis slide-out panel, launch controls, approvals,
  audit records, build/test evidence, and workflow integration.
- `RickGarner/Aegis-Developer-Studio` owns the separately versioned IDE.

Aegis-9 contains the native slide-out panel and safe launcher foundation. Runtime
acceptance and the authenticated bridge remain pending.

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

## Existing foundation — completed in Aegis Developer Studio

The Aegis Developer Studio repository contains a substantial local-first foundation:

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
Aegis-9 integration work.

## Required capabilities and remaining work

- complete Developer Studio Local-Only Mode and make FERAL the default
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

1. **Slide-out foundation — completed and accepted:** Developer
   Studio navigation, animated slide-out panel, Developer Studio checkout detection,
   folder browsing, persisted selected/recent repositories, and milestone status.
2. **Safe launcher — implemented; runtime acceptance pending:** configurable
   foundation/executable paths, exact-path process detection, selected-repository
   launch, existing-window focus/reuse, and running/ready status. Aegis does not
   terminate or take ownership of unrelated processes.
3. **Local bridge — pending:** authenticated session/status contract, provider
   health, active repository, activity, and approval messages.
4. **Governed development — pending:** file-operation approvals, scaffolding,
   conversion pipelines, build/test evidence, repair loops, and workflow handoff.
5. **Local-only release gate — pending:** Copilot independence, cloud-egress
   controls, privacy tests, packaging, and multi-computer installation validation.

## Immediate next action

Run milestone 2 from the accepted slide-out panel and confirm that the selected
repository opens in the separate IDE window. Then begin milestone 3, the
versioned authenticated local status and approval bridge.
