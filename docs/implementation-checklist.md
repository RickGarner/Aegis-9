# Jarvis Implementation Checklist

## Foundation
- [x] Confirm project scope and MVP boundaries
- [x] Create repository folder structure
- [x] Set up Python backend skeleton
- [x] Set up frontend skeleton
- [x] Set up shared config and schema files
- [x] Add initial readme and planning docs

## Local Model Layer
- [x] Install and configure Ollama or LM Studio
- [x] Test model connectivity
- [x] Define default model settings
- [x] Build backend API call wrapper
- [x] Add prompt template and conversation flow

## UI Shell
- [x] Create sidebar navigation
- [x] Create main conversation panel
- [x] Create activity and status panel
- [x] Create bottom log stream
- [x] Add drag-and-drop target area

## File Intake
- [x] Define supported file types
- [x] Handle drag/drop events
- [x] Extract metadata
- [x] Extract text from files
- [x] Preview content in the UI
- [x] Save uploaded content to storage

## Research Tools
- [ ] Add search tool
- [ ] Add webpage fetch tool
- [ ] Add content summarization workflow
- [ ] Add research panel
- [ ] Save sources and references

## Voice Layer
- [ ] Add push-to-talk interface
- [x] Integrate Windows-local push-to-talk speech-to-text with optional wake phrase
- [x] Add local text-to-speech service contract and Kokoro HTTP client scaffold
- [ ] Package or launch the Kokoro runtime/sidecar
- [ ] Add voice command routing

## Native Avatar Layer
- [x] Add animated native avatar fallback
- [x] Add avatar interaction states
- [x] Add persisted avatar name/theme preferences
- [x] Add local 3D renderer host shell and WebView2 message protocol
- [x] Add avatar metadata contract and male/female placeholder manifests
- [x] Add persisted avatar/voice/lip-sync preferences
- [ ] Add licensed local 3D male avatar
- [ ] Add licensed local 3D female avatar
- [ ] Add local model-viewer runtime file and validate GLB rendering
- [ ] Add avatar lip-sync state

## Local Artifact Generation
- [x] Add bounded generated-file path for the PowerShell add-two-numbers script request
- [ ] Generalize script/file creation behind explicit approval and allowlist policy

## Automation Layer
- [ ] Add app launching tool
- [ ] Add browser automation tool
- [ ] Add desktop action handler
- [x] Add action approval flow
- [x] Add action log output

## Task/Memory Workflow
- [x] Define task model
- [x] Add task queue
- [x] Add approval state machine
- [x] Add short-term memory
- [ ] Add preference memory

## Safety and Hardening
- [ ] Add allowlist/denylist policy
- [x] Add explicit approval for risky actions
- [x] Add stop/pause support
- [x] Add error handling
- [x] Add logging and audit trail

## Release Readiness
- [x] Run local smoke tests
- [x] Verify tool approval flow
- [x] Verify file ingestion works
- [x] Verify model communication works
- [x] Verify UI loads and responds
- [x] Document usage and setup

