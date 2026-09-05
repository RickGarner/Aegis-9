# Provider Architecture and Local Model Strategy

## Authoritative Runtime Policy — 2026-09-05

The Aegis family now uses one active provider chain:

1. **Primary:** Docker Model Runner (DMR).
2. **Secondary/failover:** Ollama.

Only models verified to return native structured tool calls are admitted. The current allowlist is:

- DMR `docker.io/ai/qwen3-coder:30b-a3b-q4_K_M`
- DMR `docker.io/ai/qwen3:8b-q4_K_M`
- Ollama `llama3.1:8b` (preferred failover model)
- Ollama `llama3.2:latest`

Live testing on the laptop rejected `qwen2.5-coder:7b` because it returned tool-shaped JSON as ordinary text; `deepseek-coder:latest` and `codellama:latest` rejected tool requests. They remain installed locally but are excluded from Aegis routing. LM Studio and LiteLLM are no longer active discovery/failover providers. Their compatibility code may remain for controlled future evaluation, but production/default routing must not select them.

The older provider recommendations below are retained as design history and are superseded by this policy.

## Goal

Keep Jarvis local-first while allowing the same application to run on both the home workstation and the AI workstation at work without changing the application logic.

## Recommended Stack

- Ollama
- LM Studio
- LiteLLM as a compatibility and abstraction layer

This combination gives the project a low-friction local model setup while keeping the application portable between environments.

## Why this stack works

### Ollama
- simple local model hosting
- easy model management
- good default local runtime for personal use

### LM Studio
- local model testing and management with GUI support
- useful for development and experimentation
- good fallback or comparison runtime

### LiteLLM
- unifies multiple providers behind a common OpenAI-compatible API style
- reduces provider-specific application code
- makes switching between home and work machine configurations easier

## Design Pattern

The Jarvis application should not care whether the underlying model is served by Ollama or LM Studio.

The backend should use a provider abstraction with a standard interface such as:

- provider type
- base URL
- model name
- timeout
- fallback model
- environment label

This keeps the frontend and orchestration logic stable while the underlying runtime changes.

## Runtime Configuration Model

Define a provider config like:

```yaml
provider: ollama
base_url: http://localhost:11434
model: llama3.1
fallback_model: qwen2.5
environment: home
```

or:

```yaml
provider: lmstudio
base_url: http://ai-workstation:1234/v1
model: deepseek-r1
fallback_model: qwen2.5
environment: work
```

## Suggested Environment Setup

### Home environment
- Ollama on local machine
- local LM Studio available for testing
- default model from home workstation

### Work environment
- AI workstation runs stronger local models
- Jarvis points to the workstation's local model service
- same application code, different environment config

## Recommended Backend Pattern

The backend should include:

- config loader
- provider registry
- chat client abstraction
- fallback selection logic
- health check endpoint
- model availability validation

This allows the app to:
- detect which provider is active
- verify the model is reachable
- switch to a fallback model if needed
- keep a single code path for chat and tool workflows

## Why not hardcode vendor-specific endpoints in the app?

Hardcoding the provider into the application would create unnecessary friction when moving between home and work systems, and it makes testing more brittle.

By centralizing environment settings, the app remains:
- portable
- local-first
- simple to debug
- easy to run on different machines

## Recommended Default

For the first implementation, default to:

- LiteLLM as the abstraction layer
- Ollama as the primary local runtime
- LM Studio as an alternate provider

This is the best practical balance of flexibility, simplicity, and local-first architecture.

## Current Implementation

Jarvis implements a typed OpenAI-compatible provider client, so LM Studio, LiteLLM, and other compatible runtimes share the same backend chat path. The checked-in `.env.example` defaults to the verified work configuration:

- provider: `lmstudio`
- base URL: `http://10.30.75.229:1234/v1`
- model: `qwen3-coder-30b-a3b-instruct`

The backend exposes provider health through `GET /api/provider/health` and dependency health through `GET /api/system/health`. The active tested provider is remote LM Studio at `http://10.30.75.229:1234/v1` using `qwen3-coder-30b-a3b-instruct`, with `qwen2.5-coder-7b-instruct` configured as a fallback. LiteLLM health uses its remote `10.30.75.229:4000` endpoint and treats a healthy `/health/liveliness` response as service availability even when `/v1/models` returns HTTP 500.

## Phase 1 Implementation Plan

1. Add configuration files for environment-specific runtime settings.
2. Add provider abstraction with a single chat client interface.
3. Add health checks for provider availability.
4. Add fallback logic between providers/models.
5. Validate the app on both home and work machine setups.

## Final Recommendation

Use the local model stack you already have installed and build the application around provider abstraction instead of a fixed runtime. This gives you a strong, portable Jarvis architecture without a cloud dependency and without unnecessary complexity.
