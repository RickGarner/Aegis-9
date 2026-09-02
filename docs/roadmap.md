# Jarvis Roadmap

## Vision

Create a local-first personal assistant inspired by the Jarvis concept: a voice-enabled, UI-driven, research-capable, task-oriented assistant that runs primarily on local hardware and local models while still supporting safe automation and internet-based research when needed.

## Guiding Principles

- Local first
- Full UI command center
- Safety over autonomy
- Tool-driven execution rather than pure chat
- Build in phases, not giant speculative design
- Keep the project evolvable without over-engineering early

## Phase 1: Local Assistant Shell

**Status: implemented and verified on 2026-08-20.**

### Goal
Create a working local assistant that can respond from a local model and interact with a simple UI.

### Deliverables
- project skeleton
- backend API service
- frontend shell
- model connection to Ollama or LM Studio
- base chat interface
- local logging
- SQLite persistence and workflow supervision control plane

### Success criteria
- A user can open the UI
- A prompt can be sent to the local model
- The response is visible in the interface
- The app works without commercial token-based APIs
- The dashboard restores local state and shows model and workflow status

## Phase 2: File Intake and Workspace

**Status: next implementation milestone.**

### Goal
Let the user drop files and work with them in the assistant context.

### Deliverables
- drag-and-drop file upload
- file metadata extraction
- text extraction for supported formats
- saved workspace items
- file attachment to chat and tasks

### Success criteria
- User can drag files into the UI
- The system recognizes and stores uploaded content
- The assistant can reference and summarize uploaded files

## Phase 3: Research and Web Tools

### Goal
Allow internet-aware tasks through controlled tools instead of direct model internet access.

### Deliverables
- search tool
- browser automation or content fetcher
- summarization of search results
- source tracking and research panel
- UI for research workspace

### Success criteria
- User can ask for research
- The assistant can collect sources and summarize findings
- The system shows what tools were used and why

## Phase 4: Voice Interaction

### Goal
Support speech input and output for a more natural assistant experience.

### Deliverables
- push-to-talk voice input
- local speech-to-text integration
- local text-to-speech output
- voice commands for core actions

### Success criteria
- User can speak to the assistant
- The assistant can respond verbally
- Voice mode is usable without always-on ambient listening

## Phase 5: Safe Automation

**Status: workflow safety foundation implemented; external automation tools pending.**

### Goal
Enable desktop and browser automation with guardrails.

### Deliverables
- app launching
- browser automation
- desktop interactions
- automation log
- approval flow for risky actions
- workflow supervisor queue and lifecycle controls

### Success criteria
- Assistant can complete basic workflows on command
- High-risk actions require explicit confirmation
- All actions are logged
- Active automation is visible and stoppable from the command center

## Phase 6: Task Orchestration and Memory

**Status: workflow queue, lifecycle, monitor capacity, managed views, and display reconciliation are implemented; planning/memory features remain pending.**

### Goal
Turn the app from a chat tool into a task-oriented assistant.

### Deliverables
- task queue
- workflow planning
- short-term memory
- long-term preference memory
- multi-step task execution
- monitor-aware managed workflow windows, capped at six

### Success criteria
- User can assign a multi-step task
- Assistant can break it into ordered steps
- Context persists over sessions
- Approved workflows run within a visible, capacity-bounded supervision model

## Phase 7: Multi-Workspace and Advanced UI

### Goal
Support more complex desktop-style workflows.

### Deliverables
- multi-panel UI
- multiple workspaces or contexts
- cross-panel drag behaviors
- persistent research and task context

### Success criteria
- User can move items and data across workspaces
- The interface feels like a true command center rather than a chat app

## Phase 8: Security, Stability, and Hardening

### Goal
Ensure the project is resilient and safe for daily use.

### Deliverables
- allowlist/denylist system
- sandboxing and approved tools
- audit trail
- failure recovery logic
- graceful stop/resume behavior

### Success criteria
- Assistant behaves predictably under failure
- High-risk actions are blocked or require confirmation
- The app remains usable over time

## Phase 9: Aegis Developer Studio

**Status: approved and planned. Existing WolfForge foundation is partially built; Aegis integration has not started.**

### Goal
Launch and supervise a local-first, repository-aware development IDE from an
Aegis slide-out panel while retaining the full IDE in its own native window.

### Deliverables
- Developer Studio slide-out launcher and control surface
- recent folder/repository selection and persisted session state
- safe launch/focus/process-status integration with the Code - OSS-based IDE
- authenticated local status and approval bridge
- local FERAL coding assistance through LM Studio, Ollama, and LiteLLM
- governed file operations, code conversion, solution/project scaffolding, and
  retained build/test evidence
- product-wide local-only controls and cloud-egress acceptance testing

### Success criteria
- A user can select a repository and launch Aegis Developer Studio from Aegis
- the full IDE opens separately while its state remains visible in the slide-out
- prompts, repository context, and inference remain on approved local endpoints
- edits, commands, builds, tests, and operational release actions use explicit,
  auditable approval boundaries

See `docs/AEGIS-DEVELOPER-STUDIO.md` for the approved architecture and milestones.

## MVP Recommendation

The first real milestone should include:
- local assistant shell
- full dashboard UI
- drag/drop file support
- file workspace
- research panel
- task queue
- approval flow
- local voice prototype

This offers the best balance of functionality and risk for a personal project.
