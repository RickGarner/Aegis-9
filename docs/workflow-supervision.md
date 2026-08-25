# Workflow Supervision and Window Management

## Objective

Jarvis must be able to supervise multiple user-approved workflows at once. Each active workflow has a dedicated managed window so the user can see its progress and intervene without losing the main Jarvis command center.

## Capacity Rules

- Detect the active Windows display topology before scheduling workflow windows.
- Derive the managed-window capacity from the connected physical monitor count.
- Never exceed the configured capacity or the hard maximum of six managed workflow windows.
- Default capacity is four when display detection is unavailable or uncertain.
- The command center is not counted as a managed workflow window.
- Queued workflows wait for a slot; they do not create an unmanaged window.

The effective capacity is:

$$
\text{capacity} = \min(\text{detected monitors}, \text{configured limit}, 6)
$$

The configured limit must be between one and six. A user can lower capacity below the display count, but Jarvis must not raise it above the calculated maximum.

## Workflow Lifecycle

Each workflow has a durable record with:

- workflow ID, title, source task, and requested tools
- current state: `queued`, `awaiting_approval`, `running`, `paused`, `completed`, `failed`, `stopped`
- assigned monitor and window identifier while active
- start, update, and completion timestamps
- structured event log, errors, and user decisions

Only the workflow supervisor creates, repositions, or closes managed workflow windows. Tool code cannot spawn its own uncontrolled windows.

## Window Behavior

- A workflow window shows its task, current step, tool activity, approval state, and latest output.
- New windows are placed on distinct usable monitor work areas without covering the command center where possible.
- If more workflows are approved than capacity allows, they remain visible in the command-center queue with their reason for waiting.
- Display changes trigger a supervisor reconciliation: preserve running work, recompute capacity, and queue excess windows rather than terminate work automatically.
- Closing a managed workflow window requests a safe stop or returns control to the command center; it does not silently discard a running task.

## Safety and User Control

- Any workflow that launches an application, controls a browser, or performs desktop automation requires the existing approval policy before it receives a window slot.
- The command center exposes pause, resume, stop, and view controls for every workflow.
- A stop request must be cooperative, logged, and visible until the workflow reaches a terminal state.
- Jarvis logs monitor detection, capacity changes, window assignment, lifecycle transitions, and all approval decisions.

## Implementation Sequence

1. [x] Add durable workflow and task records to SQLite.
2. [x] Add a Windows display-topology service and capacity policy with a testable fallback.
3. [x] Add the supervisor queue, lifecycle state machine, and queue promotion.
4. [x] Add a user-triggered, native WPF workflow view using the calculated monitor work area.
5. [ ] Connect browser and desktop automation tools only through supervisor-issued workflow contexts.
6. [x] Test monitor discovery, capacity reduction, queued work, stop/pause, managed views, and display-change recovery.

## Current Implementation Notes

- The supervisor detects Windows monitor work areas and stores a topology fingerprint in SQLite.
- It reconciles topology at dashboard startup and every 30 seconds. Workflows assigned to a removed slot become `queued`; no running task is terminated automatically.
- Workflow views are native WPF windows opened by explicit user action from the WPF command center. Jarvis positions only its own managed windows.
- The current native workflow-window view is a supervision surface only. It does not execute external browser or desktop automation.
- Native workflow creation preserves selected staged-file attachment IDs for future execution planning.
- Real workflow execution is disabled until the action catalog, allowlist, approval binding, cancellation, retry, and audit requirements are implemented.

## Non-Goals

- Jarvis does not create unlimited windows.
- Jarvis does not move, close, or take over unrelated user windows.
- Jarvis does not bypass approvals to fill available workflow slots.
