# Jarvis MVP Plan

## Objective

Build a personal AI assistant prototype that runs locally, supports a full UI, can ingest files and URLs, can do research through tools, and can carry out basic automation with explicit user approval.

## Current Implementation Status

The local assistant shell is implemented: FastAPI, React/Vite, SQLite persistence, LM Studio chat, provider health, dashboard activity, staged-file metadata, approval preview, and monitor-aware workflow supervision. Browser/desktop automation, file content extraction, research, and voice remain future work.

## Non-Goals for MVP

- Always-on ambient listening
- Full autonomous OS control with no oversight
- Full multi-user or enterprise deployment
- Native Windows application as first implementation
- Deep external service dependency

## Stack

### Backend
- Python
- FastAPI
- SQLite
- Pydantic models
- local model integration via Ollama or LM Studio

### Frontend
- React + Vite
- dashboard layout with multiple panels
- drag-and-drop file handling
- live action and log panels

### Tools and automation
- Playwright for browser-based research
- Windows automation library for desktop operations
- file parsing for text, PDFs, CSV, DOCX, images
- basic logging and event tracking

### Voice
- push-to-talk input
- local speech-to-text and TTS integration

## MVP Feature Scope

### 1. Local Chat
- user sends prompt
- prompt goes to local model through backend
- response streams back to UI
- conversation persists locally

**Implemented:** local messages and responses persist in SQLite and restore after a dashboard reload.

### 2. Full Dashboard UI
- left navigation sidebar
- center conversation and workspace
- right activity and approval panel
- bottom log stream

**Implemented:** the command center includes chat, provider status, persisted activity, file staging, approval preview, and workflow supervisor panels.

### 3. Drag-and-Drop Intake
- drop files into the UI
- accept common file types
- store file metadata and content preview
- attach files to tasks or assistant context

### 4. Research Workflow
- user asks for research
- assistant can fetch or search relevant material
- fetches webpages or document sources
- summarizes findings
- saves research references and summary

### 5. Task and Approval System
- assistant proposes actions
- user approves or rejects before risky tasks run
- logs every action and outcome
- keeps future multi-window workflows queued and supervised within a configured capacity

**Implemented foundation:** workflow records, approval, queueing, pause/resume/stop, monitor slots, managed workflow views, and display-topology reconciliation.

### 6. Voice Controls
- microphone input via push-to-talk
- assistant responses via speech
- simple command support

### 7. Safety and Logging
- event logs for all actions
- audit trail for tool use
- explicit stop and pause controls
- no destructive actions without confirmation

## Proposed Workstreams

### Workstream A: Architecture and Shared State
- API contracts
- app configuration
- session state models
- local database schema
- message and task models

### Workstream B: UI and UX
- dashboard layout
- drag-and-drop zones
- file upload experience
- research panel
- task panel
- logs and approvals UI

### Workstream C: Local Model Integration
- model selection
- API wrappers for LLM access
- prompt templates
- tool-calling contract
- streaming responses

### Workstream D: File and Content Handling
- supported file extraction
- document previews
- text summarization pipeline
- workspace storage

### Workstream E: Research and Automation Tools
- browser tool integration
- shell tool integration
- desktop automation tools
- tool result parsing

### Workstream F: Voice and Interaction
- microphone capture
- STT
- TTS
- command handling

### Workstream G: Safety, Hardening, and Ops
- confirmation flow
- logging
- cancel/resume logic
- error handling

## Implementation Approach

1. Start with local model and backend shell.
2. Add the UI shell and dashboard layout.
3. Add file ingestion and workspace.
4. Add research and browser tools.
5. Add automation with approval gates.
6. Add voice and interaction improvements.
7. Add memory and task workflows.
8. Harden the system with logs and safety controls.

## Definition of Done for MVP

The MVP is successful when:
- the user can open the app and chat with a local model
- files can be dropped into the app and processed
- the assistant can perform a bounded research workflow
- the user can approve or reject actions
- the app logs all work and is controllable
- the system feels like a functioning assistant dashboard rather than a demo

## Risks to Watch

- Overbuilding the UI before the system works
- Giving the assistant too much autonomy too early
- Weak file handling and context management
- Lack of clear approval workflow
- Too much complexity in the first voice implementation

## Recommended First Sprint

- build backend shell
- connect local model
- build frontend dashboard shell
- create drag-and-drop file intake zone
- store basic session data
- add simple action logging
- define approval flow

This is the right first milestone for the project.
