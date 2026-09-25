# Workshop local-model integration

## What is connected

Aegis submits generation prompts to Workshop's local OpenAI-compatible model
server. Aegis owns the workflow queue, tool execution, files, review stages,
test evidence, and approvals. This is not a handoff to a separate Workshop
project/job orchestrator. No Workshop cloud endpoint is used by this provider.

Design and implementation require native structured tool calls. A model must
pass the existing two-step tool qualification and continuation check before it
receives workflow tools. A healthy model catalog or successful chat alone does
not prove that the model can create an Aegis workflow.

See [the completion tracker](WORKSHOP-INTEGRATION-PLAN.md) for evidence and open work.
Use [the manual test plan](WORKSHOP-MANUAL-TEST-PLAN.md) for exact UI steps,
sample requests, expected results, failure cases, and an execution record.
The standard approval UI automatically generates the next stage; the manual
plan distinguishes that direct path from tracked Send to Workshop jobs.

## Configuration

Start Workshop Desktop and load a tool-capable local model. Configure the local,
git-ignored `.env` as needed; do not copy credentials into documentation.

```dotenv
JARVIS_WORKSHOP_ENABLED=true
JARVIS_WORKSHOP_LOCAL_HOST=127.0.0.1
```

With no port configured, Aegis discovers listening model servers whose process
ancestry includes Workshop Desktop or its backend. It ignores independent and
LM Studio-owned llama-server processes. If process information is inaccessible,
or multiple matching model routes remain, discovery reports unavailable.

For an explicitly selected runtime, set both values to the actual current
Workshop endpoint/model (these example values are not universal defaults):

```dotenv
JARVIS_WORKSHOP_LOCAL_PORT=44245
JARVIS_WORKSHOP_MODEL=Qwen3.5-35B-A3B-Q4_K_M.gguf
```

Only loopback hosts are accepted: `127.0.0.1`, `localhost`, or `::1`.
An explicit port is an operator-selected endpoint; its owning application is
not independently authenticated. Automatic process ancestry is also discovery,
not cryptographic identity verification. Model ports can change after restart.

When Workshop is enabled, the existing general provider selection also uses
Workshop for ordinary chat and direct workflow generation. When disabled,
ordinary provider selection uses the configured generic providers, but
Workshop-labelled queue/retry requests return HTTP 503. A Workshop request
never silently falls back to DMR or Ollama.

`JARVIS_REQUEST_TIMEOUT_SECONDS`, `JARVIS_MAX_RESPONSE_TOKENS`, and
`JARVIS_PROVIDER_RETRY_COUNT` still control inference requests. The old
`JARVIS_WORKSHOP_PRIORITY` setting is retained for compatibility but is not used
to select a model. Pin a model/port to resolve ambiguity.

## Operator sequence

1. Enter the workflow requirements and optional attachments in Aegis.
2. Open the workflow supervision window and choose **Design plan**, then
   **Send to Workshop**. Availability is checked before submission. Native tool
   qualification occurs during generation.
3. Review the returned design, answer any clarification questions, complete
   the design review, and approve the final plan through the existing review UI.
4. Choose **Test plans** and submit. Review and approve the returned test plans.
5. Choose **Implementation** and submit. This is unavailable until both plan
   and test-plan approval have been completed.
6. Review generated code and run the existing non-production validation flow.
   User acceptance and supervisor approval remain separate requirements before
   any supported production execution.

Only one queued/running Workshop job is accepted per workflow. The job panel
shows status, actual provider/model after completion, and errors. Selecting a
failed or cancelled job changes its action button to **Retry job**. If its
workflow context has changed, submit a fresh request rather than retrying an
obsolete snapshot.

Cancellation cancels the local asynchronous request and prevents a late result
from being committed. It does not promise that the inference server stops GPU
work immediately, nor undo files/tools already completed in the bounded
implementation workspace. Restarted queued/running jobs become failed and
require explicit retry; they are not silently resumed.

## Reproducible runtime checks

From `D:\AEGIS\AEGIS-9` in PowerShell:

```powershell
.\.venv\Scripts\python.exe scripts/validate-workshop-local.py
.\.venv\Scripts\python.exe scripts/validate-workshop-local.py --generate
```

The first command checks discovery. The second sends synthetic chat and a
harmless read-only workflow-planning tool request. It also exercises the native
tool qualification probe. Exit code zero means those checks passed; it does
not mean full desktop workflow acceptance passed.

Optional `--port` and `--model` arguments select a runtime explicitly. This
script does not load `.env`, start the normal backend, access production
monitoring, or store test data in the application database. Its qualification
cache is temporary. JSON results are printed to the terminal.

## Remaining desktop acceptance

Use an isolated application configuration and database. Normal backend startup
polls configured monitoring integrations, so it is not the acceptance harness.
Run the operator sequence above using a harmless add-two-integers workflow.
Capture provider/model and outputs for all three generation stages, exercise
clarifications, cancel a running generation, change a draft while generation
is delayed, and retry a failed request. Verify no approval or production run
is created automatically. Record UI screenshots and artifact/test evidence in
the completion tracker. This full operator-driven sequence remains pending.
