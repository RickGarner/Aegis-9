# Aegis 9 Agent Instructions

These instructions apply to all work performed in this repository.

## Environment

- Primary host environment: Windows 11.
- Use Windows PowerShell unless another shell has been explicitly verified and is required.
- Do not use Bash command syntax in PowerShell.
- Repository root: `D:\AEGIS\AEGIS-9`.
- Root solution: `Aegis-9.sln`.

## Repository safety

This repository may contain substantial pre-existing modified and untracked work.

Before making changes:

1. Confirm the repository root.
2. Inspect the current branch.
3. Inspect `git status`.
4. Preserve all pre-existing modifications and untracked files.

Never automatically:

- reset the repository
- clean the repository
- restore user changes
- stash user changes
- switch branches
- delete untracked files
- rewrite Git history
- overwrite unrelated changes

If existing work conflicts with the requested implementation, report the conflict and work around it where practical.

## Repository discovery

Use bounded discovery.

Prefer:

- solution and project files
- README and documentation files
- direct source references
- `git ls-files`
- targeted PowerShell searches

Avoid whole-repository recursive enumeration unless it is necessary.

Exclude generated or dependency trees from routine discovery:

- `bin`
- `obj`
- `node_modules`
- `.build`
- `.artifacts`
- `.review`

Do not repeatedly scan the entire repository.

## Architecture

Inspect the current repository before making architecture claims.

Do not rely on stale assumptions about Aegis 9 merely because a subsystem or file existed in an earlier version.

Follow concrete references from the current solution, project files, entry points, configuration, and source code.

If architecture cannot be established from inspected source, report `UNKNOWN`.

## Task execution

For read-only requests:

- do not modify files
- do not generate build artifacts
- do not restore packages
- do not run formatters or migrations
- do not perform Git state changes

For implementation requests:

- modify only files relevant to the requested feature or fix
- preserve existing conventions where practical
- do not refactor unrelated code
- distinguish pre-existing changes from changes made for the current task
- validate the smallest relevant scope first
- expand validation only as necessary

When a command fails, diagnose the failure. Do not use repository resets, terminal resets, or unrelated environment changes as recovery mechanisms.

## PowerShell

Use native PowerShell syntax.

Do not issue Bash constructs such as:

- `&&`
- `||`
- `grep`
- `rm -rf`
- `cp`
- `mv`
- Unix path assumptions

If multiple commands must be executed sequentially, use appropriate PowerShell constructs.

## Terminology

Aegis 9 contains application concepts that may use words such as:

- automation
- workflow
- webhook
- agent
- monitoring
- integration

Treat these as Aegis source-domain concepts unless the user explicitly asks to work with OpenHands platform features.

Do not divert an Aegis development task into OpenHands Automation or skill management merely because those keywords appear in source files or prompts.

## Reporting

Be precise.

Report:

- what was inspected
- what was changed, when changes were requested
- validation performed
- failures or remaining uncertainty

Use `UNKNOWN` rather than guessing.