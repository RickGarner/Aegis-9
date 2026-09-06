# AEGIS 9 Priority: Align Local Agent Tooling with GitHub Copilot Agent Architecture

**Priority:** High
**Status:** Incorporated into roadmap; initial provider-neutral qualification and security foundation implemented
**Project:** AEGIS Developer Studio / AEGIS 9
**Focus:** Local AI Agent tooling, orchestration, and Copilot-like behavior

---

## 1. Objective

AEGIS Developer Studio should evolve its Local AI Agent tool architecture so that it behaves more like GitHub Copilot Agent mode in current VS Code.

The goal is not to clone GitHub Copilot internally. The goal is to provide the local FERAL/Qwen Agent with the same type of safe, composable development primitives that make Copilot effective:

- read files and diagnostics,
- search the workspace and codebase,
- edit one or many files,
- create files and directories,
- execute commands,
- inspect command output,
- validate changes,
- manage multi-step work,
- and delegate when appropriate.

The model should decide the sequence of those operations while AEGIS:

- exposes the allowed tools,
- validates tool inputs,
- enforces workspace boundaries,
- requests user approval where required,
- executes the operations,
- and returns the results to the model.

This should reduce the need for special-case orchestration and eliminate repeated tool loops such as the project scaffolding issue encountered on 2026-09-05.

---

# 2. Why this is a priority

AEGIS can now successfully perform the core local Agent workflow:

```text
Natural-language request
    ↓
local model reasoning
    ↓
tool selection
    ↓
user approval
    ↓
tool execution
    ↓
file modification
    ↓
tool result returned to model
    ↓
completion response
```

However, some current AEGIS tools are too specialized or are treated as complete workflows rather than primitives.

The recent WPF project test exposed this problem.

Request:

```text
Create a Visual Studio WPF project that can monitor the stock market.
```

Observed behavior:

```text
scaffoldWorkspaceProject
scaffoldWorkspaceProject
scaffoldWorkspaceProject
scaffoldWorkspaceProject
bounded tool-use limit reached
```

The scaffold operation itself succeeded. The problem was orchestration:

- the same scaffold tool remained available on every turn,
- the model repeated it,
- and the existing scaffold policy treated project creation largely as a scaffolding operation rather than a multi-step implementation task.

A Copilot-style architecture is more flexible:

```text
determine setup
    ↓
create/scaffold project
    ↓
inspect generated files
    ↓
edit XAML/C#
    ↓
create supporting files
    ↓
build
    ↓
inspect diagnostics
    ↓
repair
    ↓
validate
    ↓
finish
```

AEGIS should move toward this model.

---

# 3. GitHub Copilot / VS Code Agent tool model

Current VS Code Agent mode exposes tools in capability groups rather than relying on a single monolithic implementation tool.

Representative built-in groups include:

```text
read
search
edit
execute
agent
browser
web
vscode
todos
```

Important built-in operations include:

## Read

```text
readFile
problems
terminalLastCommand
terminalSelection
getNotebookSummary
readNotebookCellOutput
```

## Search

```text
fileSearch
textSearch
listDirectory
usages
codebase
changes
```

## Edit

```text
createDirectory
createFile
editFiles
editNotebook
```

## Execute

```text
runInTerminal
getTerminalOutput
createAndRunTask
runNotebookCell
testFailure
```

## VS Code / Project Setup

```text
getProjectSetupInfo
runCommand
extensions
installExtension
VSCodeAPI
```

## Agent / Workflow

```text
runSubagent
todos
askQuestions
```

## Web / Browser

```text
fetch
browser interaction tools
```

The exact Copilot tool set can vary by:

- VS Code version,
- installed extensions,
- enabled MCP servers,
- workspace state,
- Agent configuration,
- and whether execution is local or delegated.

The architectural principle is more important than matching exact names.

---

# 4. Current AEGIS → Copilot-style mapping

AEGIS already has many comparable capabilities.

| AEGIS Tool | Closest Copilot / VS Code Agent Equivalent |
|---|---|
| `rickgarner_localAi_readWorkspaceFile` | `read/readFile` |
| `rickgarner_localAi_searchFiles` | `search/fileSearch` |
| `rickgarner_localAi_searchWorkspaceText` | `search/textSearch` |
| `rickgarner_localAi_findSymbolUsages` | `search/usages` |
| `rickgarner_localAi_getRepositoryMap` | `search/codebase` |
| `rickgarner_localAi_getRankedWorkspaceContext` | `search/codebase` |
| `rickgarner_localAi_applyEdit` | `edit/editFiles` |
| `rickgarner_localAi_applyWorkspaceEdits` | `edit/editFiles` |
| `rickgarner_localAi_createFile` | `edit/createFile` |
| `rickgarner_localAi_runWorkspaceCommand` | `execute/runInTerminal` |
| `rickgarner_localAi_getWorkspaceDiagnostics` | `read/problems` |
| `rickgarner_localAi_getValidationRecipe` | validation planning |
| `rickgarner_localAi_getBuildTestOwnership` | validation/test planning |
| `rickgarner_localAi_delegateToAgentHostSession` | `agent/runSubagent` / Agent Host |
| `rickgarner_localAi_scaffoldWorkspaceProject` | project bootstrap helper |
| `rickgarner_localAi_getProjectExecutionPlan` | project planning |
| `rickgarner_localAi_getProjectImprovementSuggestions` | review/planning support |
| `rickgarner_localAi_analyzeChangeImpact` | codebase/change analysis |
| `rickgarner_localAi_getMcpTools` | MCP discovery |
| `rickgarner_localAi_getVisualStudioProjectMap` | project/codebase inspection |

This means AEGIS already has much of the required foundation.

The next step is to reorganize and normalize how these tools are exposed and orchestrated.

---

# 5. Target AEGIS Agent tool architecture

Recommended conceptual structure:

```text
AEGIS Agent Core
│
├── Read
│   ├── readFile
│   ├── problems
│   ├── terminalOutput
│   └── projectMetadata
│
├── Search
│   ├── fileSearch
│   ├── textSearch
│   ├── listDirectory
│   ├── usages
│   └── codebase
│
├── Edit
│   ├── createDirectory
│   ├── createFile
│   └── editFiles
│
├── Execute
│   ├── runInTerminal
│   ├── getTerminalOutput
│   ├── runTask
│   └── testFailure
│
├── Project
│   ├── getProjectSetupInfo
│   └── scaffoldProject
│
├── Diagnostics
│   └── problems
│
├── Agent
│   └── runSubagent
│
└── Workflow
    ├── todos
    └── askQuestions
```

These names are conceptual.

Existing AEGIS tool names do not need to be immediately renamed if doing so would introduce unnecessary compatibility risk. The priority is behavior and composition.

---

# 6. Architectural principle

The desired architecture is:

> **AEGIS exposes safe primitives. The local model chooses the sequence.**

AEGIS should not attempt to encode an entire development workflow inside a single tool unless the operation is truly atomic.

For example:

## Good atomic tool

```text
createFile
```

One operation, deterministic result.

## Good atomic tool

```text
runInTerminal
```

One command, bounded execution, deterministic result.

## Good helper tool

```text
scaffoldWorkspaceProject
```

Creates a baseline project structure.

## Bad assumption

```text
scaffoldWorkspaceProject == entire "create application" request
```

Scaffolding is only one phase of application creation.

---

# 7. Project creation should become a stateful Agent workflow

For:

```text
Create a Visual Studio WPF project that can monitor the stock market.
```

Expected AEGIS behavior should eventually resemble:

```text
1. Understand request
2. Determine project type
3. Determine target directory
4. Scaffold WPF project once
5. Inspect generated project structure
6. Read MainWindow.xaml
7. Read MainWindow.xaml.cs
8. Determine supporting classes/services needed
9. Edit/create files
10. Add UI for ticker input / quotes / status
11. Add stock-data abstraction
12. Add initial data source implementation or safe placeholder
13. Build project
14. Inspect build errors
15. Repair if required
16. Rebuild
17. Report what was created
```

The scaffold tool should never repeat after successful completion unless the user explicitly starts a new project.

---

# 8. Recommended missing or improved primitives

## 8.1 `listDirectory`

AEGIS has search tools, but a direct directory listing primitive is useful.

Suggested behavior:

```text
input:
- path
- depth / recursive flag
- maxResults

output:
- files
- folders
- relative paths
```

It should enforce workspace boundaries.

## 8.2 `createDirectory`

Required for project/file workflows where a model needs to add:

```text
Models/
Services/
ViewModels/
Helpers/
Tests/
```

This should be a separate deterministic tool rather than overloading file creation.

## 8.3 `getTerminalOutput`

AEGIS currently has `runWorkspaceCommand`.

A separate output retrieval tool would allow:

```text
run command
    ↓
later inspect output
```

without necessarily re-running the command.

## 8.4 Task execution

Add a controlled equivalent to:

```text
createAndRunTask
```

This could integrate with:

```text
.vscode/tasks.json
MSBuild
dotnet build
dotnet test
PowerShell validation
npm scripts
```

where project metadata provides a verified recipe.

## 8.5 Test-failure retrieval

A dedicated tool should allow the model to retrieve structured test failures rather than parsing arbitrary terminal text.

Conceptually:

```text
getTestFailures
```

Output:

```text
test name
file
line
failure message
stack trace
```

## 8.6 `askQuestions`

AEGIS generally attempts to infer and proceed, but a controlled clarification tool is still useful when an essential decision cannot safely be inferred.

Examples:

```text
Which target framework?
Which API provider should the project use?
Should authentication be included?
Should the generated project replace an existing folder?
```

This tool should be used sparingly.

## 8.7 `todos`

For larger requests, request-scoped task state can help local models maintain progress.

Example:

```text
[done] scaffold solution
[done] inspect WPF project
[in progress] implement quote service
[pending] build
[pending] repair errors
[pending] summarize
```

This should not become a substitute for actual execution state. It is an Agent coordination aid.

---

# 9. Existing tools that should remain

The following AEGIS-specific tools provide capabilities beyond basic Copilot-style primitives and should remain.

## Repository intelligence

```text
getRepositoryMap
getRankedWorkspaceContext
getRepositoryMemory
getSymbolGraph
analyzeChangeImpact
```

These can improve local-model performance by giving the model structured repository context without requiring it to repeatedly scan the entire workspace.

## Visual Studio intelligence

```text
getVisualStudioProjectMap
getProjectExecutionPlan
getBuildTestOwnership
```

These are especially valuable for:

```text
.sln
.csproj
WPF
WinForms
ASP.NET
MSBuild
Visual Studio solution workflows
```

## MCP discovery

```text
getMcpTools
```

This should remain as the bridge to external/local MCP capabilities.

---

# 10. Tool grouping

Longer term, AEGIS should expose tool groups or logical categories to the model.

Example:

```text
read/*
search/*
edit/*
execute/*
project/*
diagnostics/*
agent/*
workflow/*
```

Benefits:

- easier prompting,
- clearer capability boundaries,
- simpler tool filtering,
- better documentation,
- easier comparison with Copilot,
- easier future dynamic tool discovery.

Implementation does not have to rename every current tool immediately. A translation/alias layer is acceptable.

---

# 11. Tool lifecycle and state

A major lesson from the scaffold loop is that some tools should change availability after successful execution.

The Agent request should maintain request-scoped state.

Example:

```ts
interface AgentExecutionState {
    scaffoldCompleted?: boolean;
    createdFiles?: string[];
    modifiedFiles?: string[];
    completedCommands?: string[];
    validationCompleted?: boolean;
}
```

Then tool availability can evolve:

```text
Before scaffold:
    scaffoldProject available

After scaffold:
    scaffoldProject removed
    read/search/edit/execute available

After build:
    diagnostics/test tools prioritized

After successful validation:
    completion encouraged
```

This is preferable to relying entirely on prompt text such as:

```text
Do not call scaffoldWorkspaceProject again.
```

Prompt guidance should be combined with deterministic execution-state controls.

---

# 12. Idempotence

Every destructive or state-creating tool should have protection against accidental repeated execution.

Examples:

```text
scaffoldProject
createFile
createDirectory
dependency installation
project generation
solution generation
```

The Agent host should recognize repeated identical calls in the same request where appropriate.

Possible key:

```text
toolName + normalized input
```

Example:

```text
scaffoldWorkspaceProject
+
{
  template: dotnet-wpf-csharp,
  projectName: StockMarketMonitor,
  targetDirectory: D:\StockTest
}
```

If this has already succeeded during the same request, the second identical call should not execute again.

Instead return:

```text
This operation already completed successfully.
Continue with the next distinct implementation step.
```

---

# 13. Native tools vs textual recovery

AEGIS currently supports recovery for local models that emit textual tool markup.

That recovery must remain a fallback.

Preferred order:

```text
native structured tool call
    ↓ if absent
known textual recovery
    ↓ if absent
malformed-tool detection
    ↓
normal response or controlled failure
```

Do not optimize the entire Agent architecture around weak-model textual output.

Better local models/providers should be able to use the same tools natively.

---

# 14. Tool authorization

Continue using normal Code OSS approval where an operation requires user confirmation.

Examples:

```text
file writes
terminal execution
project scaffolding
agent delegation
potentially destructive operations
```

AEGIS should avoid adding a second redundant custom confirmation system unless a specific security boundary requires it.

---

# 15. Proposed implementation phases

## Phase 1 — Fix Agent state and repeated tool execution

**Priority:** Immediate

- complete v11 scaffold state fix,
- make successful scaffold one-shot per request,
- remove scaffold tool after success,
- add request-scoped execution state,
- add generic repeated-tool detection where appropriate.

Acceptance:

```text
Create a WPF application...
```

must scaffold only once.

## Phase 2 — Normalize core tools

**Priority:** High

Establish first-class equivalents for:

```text
readFile
listDirectory
fileSearch
textSearch
usages
createFile
createDirectory
editFiles
runInTerminal
problems
```

Where current AEGIS tools already satisfy the function, adapt or alias them rather than rewriting unnecessarily.

## Phase 3 — Project setup flow

**Priority:** High

Create a project workflow equivalent to:

```text
getProjectSetupInfo
scaffoldProject
inspect project
edit project
validate project
```

Project setup should not terminate the Agent request.

## Phase 4 — Validation and testing

**Priority:** High

Add/improve:

```text
getTerminalOutput
runTask
getTestFailures
verified validation recipes
build/test repair loops
```

The model should never claim success unless validated tool output supports the claim.

## Phase 5 — Workflow coordination

**Priority:** Medium

Add:

```text
todos
askQuestions
request execution state
completion criteria
```

This should improve larger multi-step tasks.

## Phase 6 — Subagents and advanced orchestration

**Priority:** Medium / Future

Extend:

```text
delegateToAgentHostSession
```

toward a clearer:

```text
runSubagent
```

model.

Potential specialized agents:

```text
planner
implementation agent
reviewer
test agent
security reviewer
UI reviewer
```

These should remain optional and bounded.

---

# 16. Regression scenarios

The following should become standard Agent regression tests.

## Existing file edit

```text
Modify Test.ps1 to...
```

Expected:

```text
read
edit
validate
finish
```

## New file

```text
Create HealthCheck.ps1...
```

Expected:

```text
createFile once
optional validation
finish
```

## WPF project creation

```text
Create a Visual Studio WPF project that can monitor the stock market.
```

Expected:

```text
scaffold once
inspect generated files
edit multiple files
build
repair if required
finish
```

Never:

```text
scaffold
scaffold
scaffold
scaffold
```

## Console project creation

```text
Create a C# console application that scans a folder and reports duplicate files.
```

Expected:

```text
scaffold
inspect
implement
build
finish
```

## Existing solution feature

```text
Add a settings page to this WPF application.
```

Expected:

```text
search project
read relevant files
edit/create files
build
repair
finish
```

No scaffolding.

## Build failure

Expected:

```text
build
read error
inspect source
edit
build again
finish
```

## User denies tool approval

Expected:

```text
stop operation
report that execution was not performed
do not claim success
```

---

# 17. Completion criteria

AEGIS should consider a development request complete only when:

1. the requested artifact/change actually exists,
2. the relevant tool operations succeeded,
3. appropriate validation was performed where practical,
4. validation results support success,
5. no required implementation steps remain,
6. the final response accurately summarizes completed work.

For project creation:

```text
successful scaffold != completed application
```

This distinction must be enforced.

---

# 18. Recommended development rule

Use this rule when designing future Agent tools:

> If a capability can be expressed as a small, deterministic, reusable primitive, prefer that primitive over a monolithic workflow tool.

Examples:

Prefer:

```text
readFile
editFiles
runInTerminal
problems
```

over:

```text
implementEntireFeature
fixEntireProject
createCompleteApplication
```

Higher-level workflows should be produced by the Agent through tool composition.

---

# 19. Expected end-state

The desired AEGIS development experience is:

```text
User:
"Create a Visual Studio WPF project that can monitor the stock market."

FERAL:
    determines WPF project is required
    selects project setup
    requests scaffold approval

AEGIS:
    scaffolds once

FERAL:
    inspects project
    designs minimal implementation
    edits MainWindow.xaml
    edits code-behind or ViewModel
    creates service/model classes
    requests build

AEGIS:
    runs verified build

FERAL:
    reads errors if any
    repairs them
    builds again
    verifies success
    summarizes implementation
```

This should occur locally using approved local models and AEGIS-controlled tooling.

---

# 20. Priority summary

This work should be treated as a **major next-phase priority** for AEGIS 9 / AEGIS Developer Studio.

The Local AI Agent is now capable of real tool execution.

The next step is to make its tool architecture:

- composable,
- state-aware,
- idempotent,
- predictable,
- Copilot-like,
- and suitable for complete multi-step software-development tasks.

The most immediate technical priorities are:

```text
1. finish scaffold-state transition behavior
2. prevent repeated identical state-changing tools
3. expose missing primitives such as listDirectory/createDirectory
4. normalize read/search/edit/execute/project tool categories
5. strengthen validation/build/test loops
6. add request-scoped Agent execution state
7. add regression tests for full application creation
```

This architecture should become the foundation for future AEGIS local coding-agent development.
