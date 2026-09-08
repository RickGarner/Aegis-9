# AEGIS 9 and Developer Desktop
# MCP Strategy, Recommended Free Servers, and First-Party MCP Implementation Plan

**Document status:** Implementation planning / architecture handoff  
**Validation date:** 2026-09-06  
**Primary environments:** AEGIS 9, AEGIS Developer Desktop / Developer Studio, Windows enterprise infrastructure, local/offline AI environments  
**Objective:** Define which free MCP servers should be adopted, where they should run, how they should be secured, and which MCP servers AEGIS should build itself.

---

## 1. Executive Summary

AEGIS 9 and Developer Desktop should not use a generic "install every MCP server" strategy.

The recommended design is a **three-tier MCP architecture**:

1. **Native AEGIS tools remain primary** for operations AEGIS already implements well, especially workspace read/search/edit/create/terminal/diagnostic capabilities in Developer Desktop.
2. **Vetted vendor-maintained MCP servers** should be added where they provide authoritative external capability that AEGIS does not already possess, such as Microsoft documentation, NuGet package intelligence, GitHub, SQL data access, browser diagnostics, Prometheus, and Grafana.
3. **AEGIS first-party MCP servers** should be built for privileged enterprise operations such as Windows administration, Active Directory, MOVEit failover/failback, and other infrastructure tasks where unrestricted community MCP servers or arbitrary shell access would create unnecessary risk.

The most important architectural rule is:

> **FERAL should never receive broader privileges merely because an MCP server can expose them. AEGIS must expose only the smallest set of tools required for the current task, and every privileged operation must be governed by deterministic policy outside the model.**

The MCP steering group's reference server repository now explicitly describes its servers as **reference implementations rather than production-ready solutions**. This is a major reason to harden, wrap, or replace privileged reference MCP servers before using them in production AEGIS environments.

### Recommended highest-priority additions

#### Developer Desktop

1. Microsoft Learn MCP
2. NuGet MCP
3. GitHub MCP
4. Microsoft SQL MCP
5. Playwright MCP
6. Chrome DevTools MCP
7. Local Git MCP
8. Terraform MCP when infrastructure-as-code is used
9. Kubernetes MCP when Kubernetes/OpenShift is used

#### AEGIS 9

1. Microsoft SQL MCP
2. Prometheus MCP
3. Grafana MCP
4. Playwright MCP for synthetic/application validation
5. Local Git MCP for configuration/runbook repositories
6. Microsoft Learn MCP when Internet access is allowed
7. First-party AEGIS Windows Operations MCP
8. First-party AEGIS Active Directory MCP
9. First-party AEGIS MOVEit Operations MCP
10. Kubernetes/Terraform MCP when those technologies enter the platform

### Items that should be demoted or avoided

- The old `@modelcontextprotocol/server-postgres` reference server is deprecated and should not be used.
- The old reference SQLite server is archived; select a specific maintained implementation before using SQLite through MCP.
- The supplied generic `mcp-server-docker` recommendation should **not** be deployed as an unrestricted Docker administration MCP.
- Filesystem, Memory, Git, Fetch, Sequential Thinking, and Time reference servers are useful examples/development tools, but production use requires threat-model review and additional controls.
- Sequential Thinking MCP is useful, but it gives less practical capability to AEGIS than database, observability, browser, documentation, and source-control MCPs.

---

# 2. Design Principles

## 2.1 Native tools first

Developer Desktop already has native workspace-oriented primitives such as:

- read file
- search files
- search text
- symbol/repository context
- edit files
- create files
- run commands
- diagnostics
- project scaffolding
- validation

Those capabilities should remain the preferred tools for the active workspace.

Do not duplicate them through Filesystem MCP unless AEGIS needs access to a directory that is deliberately outside the active workspace.

This reduces:

- duplicated tool choices,
- model confusion,
- accidental access expansion,
- inconsistent approval behavior,
- conflicting file semantics.

## 2.2 Vendor MCP for vendor domains

Prefer official/vendor-maintained MCP servers for:

- Microsoft documentation
- NuGet
- GitHub
- SQL
- Prometheus
- Grafana
- Chrome DevTools
- Terraform

These vendors understand their own APIs, security models, authentication mechanisms, and domain semantics better than generic community wrappers.

## 2.3 First-party MCP for privileged enterprise control

AEGIS should build and own MCP servers where the capability can:

- stop/start production services,
- modify Active Directory,
- fail over production systems,
- change infrastructure state,
- access privileged Windows interfaces,
- manipulate critical application configuration,
- expose secrets or regulated information.

The model should call **typed business/operations tools**, not unrestricted PowerShell, CMD, SSH, WMI, SQL, or Docker sockets.

## 2.4 Read-only by default

Every production MCP integration should begin in read-only mode.

Writes should be enabled only after:

1. tool-specific validation,
2. authorization design,
3. approval behavior,
4. audit logging,
5. rollback strategy,
6. idempotency testing,
7. lab validation.

## 2.5 Tool selection must be dynamic

AEGIS should not provide every connected MCP tool to the model on every turn.

Tool exposure should depend on:

- current task classification,
- environment,
- user role,
- workspace,
- machine/server target,
- online/offline state,
- Plan/Review/Act mode,
- tool risk classification,
- previous tool results,
- current workflow state.

---

# 3. Free vs. Free-to-Run vs. Service-Dependent

"Free MCP server" can mean different things.

| Classification | Meaning |
|---|---|
| **Fully local/free** | Server and backing capability run locally; no account required for core function |
| **Free MCP, external service required** | MCP software is free but requires access to GitHub, Azure DevOps, HCP Terraform, etc. |
| **Free public remote MCP** | No account or fee required, but Internet access is required |
| **Free with self-hosted backend** | MCP server is free; user must operate Prometheus, Grafana, SQL, Redis, etc. |
| **Conditional enterprise licensing** | MCP server may be free, but the product it controls can have normal commercial licensing |

This distinction is important for AEGIS because Developer Desktop must support a local/air-gapped mode.

---

# 4. Recommended MCP Portfolio

## 4.1 Priority Matrix

| MCP Server | AEGIS 9 | Developer Desktop | Online Needed | Production Recommendation |
|---|---:|---:|---|---|
| Microsoft SQL MCP | 5/5 | 5/5 | No for local SQL | P0 |
| Microsoft Learn MCP | 4/5 | 5/5 | Yes | P0 Dev Desktop |
| NuGet MCP | 2/5 | 5/5 | Usually; can use internal feed | P0 Dev Desktop |
| GitHub MCP | 3/5 | 5/5 | Yes unless GHES/local | P0 Dev Desktop |
| Playwright MCP | 4/5 | 5/5 | Only for remote sites | P0/P1 |
| Chrome DevTools MCP | 2/5 | 5/5 | No for local apps; some defaults phone home | P1 Dev Desktop |
| Prometheus MCP | 5/5 | 3/5 | No for local Prometheus | P0/P1 AEGIS |
| Grafana MCP | 5/5 | 3/5 | No for local Grafana | P0/P1 AEGIS |
| Local Git MCP | 3/5 | 4/5 | No | P1 |
| Kubernetes MCP | 5/5 conditional | 4/5 conditional | No for local/on-prem cluster | Conditional |
| Terraform MCP | 5/5 conditional | 5/5 conditional | Registry access for public docs; optional TFE/HCP | Conditional |
| Azure DevOps MCP | 4/5 conditional | 5/5 conditional | Yes for Azure DevOps Services | Conditional |
| Filesystem reference MCP | 3/5 | 3/5 | No | Supplemental |
| Memory reference MCP | 3/5 | 4/5 | No | Prototype/harden |
| Sequential Thinking MCP | 2/5 | 3/5 | No | Optional |
| Fetch MCP | 3/5 | 3/5 | Depends on target URL | Optional |
| Time MCP | 2/5 | 1/5 | No | Prefer native AEGIS time service |
| Redis MCP | 3/5 conditional | 3/5 conditional | No for local Redis | Conditional |

---

# 5. Developer Desktop Recommended Integrations

## 5.1 Microsoft Learn MCP

### Why it should be added

Microsoft Learn MCP provides direct access to current Microsoft documentation rather than relying on a local model's training data.

It is particularly valuable for Developer Desktop because the environment frequently works with:

- C#
- .NET
- WPF
- PowerShell
- Windows
- SQL Server
- Visual Studio
- VS Code / Code OSS
- Azure components
- Microsoft APIs

Microsoft states that the server:

- is publicly available,
- requires no authentication,
- has no charge,
- supports document search,
- full article retrieval,
- code-sample search,
- Streamable HTTP.

### Environment

**Implement in:**
- Developer Desktop online profile
- AEGIS 9 support/engineering profile when Internet access is allowed

**Do not enable in:**
- strict air-gapped profile

### Configuration concept

```json
{
  "mcpServers": {
    "microsoft-learn": {
      "type": "http",
      "url": "https://learn.microsoft.com/api/mcp?maxTokenBudget=2000"
    }
  }
}
```

### AEGIS policy

- Read-only
- No approval required
- Online-only capability
- Automatically removed from available tools when Internet tools are disabled
- Tool list should be discovered dynamically rather than hard-coded

### Benefit

FERAL can verify an API against current Microsoft documentation before implementing code.

---

## 5.2 NuGet MCP

### Why it should be added

NuGet MCP gives Developer Desktop package intelligence.

It can assist with:

- package discovery,
- version selection,
- dependency upgrades,
- package vulnerability remediation,
- package compatibility,
- package-source inspection,
- modernization.

Microsoft's documented implementation uses `dnx` and requires .NET 10 SDK or later.

### Environment

**Implement in:**
- Developer Desktop
- local development workstations
- build/modernization agents

**Optional in AEGIS 9 runtime:**
- usually unnecessary

### Windows configuration concept

```json
{
  "mcpServers": {
    "nuget": {
      "type": "stdio",
      "command": "dnx",
      "args": [
        "NuGet.Mcp.Server",
        "--source",
        "https://api.nuget.org/v3/index.json",
        "--yes"
      ]
    }
  }
}
```

### Air-gapped design

Replace public `nuget.org` with:

- internal NuGet mirror,
- Artifactory,
- Azure Artifacts internal feed,
- Nexus,
- another approved enterprise feed.

Developer Desktop should switch server configuration automatically based on the selected connectivity profile.

### Security

- package search/read: automatic
- project package changes: use native AEGIS edit/terminal approval rules
- never silently add packages to a project simply because NuGet MCP suggested one

---

## 5.3 GitHub MCP

### Why it should be added

The official GitHub MCP server adds capabilities local Git alone cannot provide:

- remote repositories,
- issues,
- pull requests,
- Actions,
- workflow results,
- releases,
- security findings,
- Dependabot information,
- team collaboration context.

### Recommended architecture

Use both:

```text
Developer Desktop
    |
    +-- Local Git / native Git tools
    |     working tree, branch, diff, local history
    |
    +-- GitHub MCP
          issues, PRs, Actions, remote repository,
          security, releases, team context
```

### Environment

**Implement in:**
- Developer Desktop online profile
- AEGIS engineering/configuration repository workflows

**Do not make core production AEGIS runtime depend on public GitHub.**

### Security

GitHub MCP supports:

- read-only mode,
- toolsets,
- explicit tool lists,
- tool exclusions,
- lockdown mode.

Start Developer Desktop with:

- read-only GitHub MCP by default,
- repository toolset only,
- PR/issue writes behind normal AEGIS approval,
- Actions workflow dispatch behind high-risk approval.

Never embed PATs in repository configuration.

Use:
- OAuth where appropriate, or
- environment/secure credential store,
- minimum scopes,
- separate tokens per environment.

---

## 5.4 Playwright MCP

### Why it should be added

Playwright provides deterministic browser automation based primarily on structured browser/accessibility information.

Use it for:

- web application testing,
- regression tests,
- form workflows,
- UI verification,
- authentication flow testing,
- synthetic transactions,
- screenshots/evidence,
- local web application validation.

### Developer Desktop

FERAL can:

1. implement a web change,
2. run the application,
3. launch Playwright,
4. exercise the affected feature,
5. capture results,
6. report verified success/failure.

### AEGIS 9

Playwright is valuable for **synthetic monitoring**.

A service can be healthy at TCP/HTTP level while the application UI is broken. Playwright can validate an actual operational path.

Example:

```text
AEGIS health workflow
    |
    +-- service health
    +-- database health
    +-- endpoint health
    +-- Playwright synthetic transaction
            login
            load page
            validate expected UI state
            logout
```

### Windows configuration concept

For staging/testing:

```json
{
  "mcpServers": {
    "playwright": {
      "type": "stdio",
      "command": "cmd",
      "args": [
        "/c",
        "npx",
        "-y",
        "@playwright/mcp@latest"
      ]
    }
  }
}
```

For controlled deployments, validate a version and **pin the exact package version** rather than permanently using `@latest`.

### Security

Use isolated browser profiles and synthetic accounts.

Do not allow production Playwright sessions to reuse a user's personal browser profile.

---

## 5.5 Chrome DevTools MCP

### Why it is different from Playwright

Playwright is strongest for **workflow automation**.

Chrome DevTools MCP is strongest for **deep browser diagnostics**:

- network requests,
- console errors,
- source-mapped stack traces,
- performance traces,
- runtime inspection,
- screenshots,
- browser automation.

Use both rather than treating them as substitutes.

### Developer Desktop flow

```text
User: "Why is this page slow?"

FERAL
  |
  +-- Playwright: reproduce the behavior
  |
  +-- Chrome DevTools MCP:
        inspect waterfall
        inspect console
        record performance trace
        inspect runtime errors
        identify bottleneck
```

### Privacy/offline configuration

Chrome DevTools MCP currently documents:

- usage statistics enabled by default,
- CrUX lookup during some performance operations,
- update checks.

For AEGIS-controlled use, configure:

```text
--no-usage-statistics
--no-performance-crux
CHROME_DEVTOOLS_MCP_NO_UPDATE_CHECKS=1
```

This is particularly important for local/private development.

### Environment

**Implement in:**
- Developer Desktop
- development/testing only

**Not a core AEGIS production operations tool.**

---

# 6. AEGIS 9 Recommended Integrations

## 6.1 Microsoft SQL MCP

### Why this is a major recommendation

Microsoft SQL MCP is built on Data API Builder and is specifically designed to expose database operations through typed entity operations and role-based access control.

This is a much better fit for AEGIS than giving a model arbitrary SQL execution.

Microsoft describes it as:

- open source,
- free to use through Data API Builder,
- locally hostable,
- Streamable HTTP or stdio,
- entity-based,
- RBAC-aware,
- production-oriented.

### AEGIS use cases

- SQL Server health/state inspection
- MOVEit-related operational queries
- application state validation
- post-workflow verification
- controlled update operations
- diagnostics
- application-support workflows

### MOVEit relevance

Your MOVEit Automation failover pair uses the same Microsoft SQL Server database.

AEGIS should **not** expose unrestricted MOVEit database tables directly to FERAL.

Instead:

1. create approved read-only views,
2. expose only those views/entities through SQL MCP,
3. use a dedicated database identity,
4. prevent arbitrary SQL,
5. never implement MOVEit failback by directly editing MOVEit database state unless Progress explicitly documents that action as supported.

### Local server concept

```text
SQL Server
    |
Data API Builder
    |
SQL MCP
    |
AEGIS MCP Broker
    |
FERAL
```

A local stdio development instance can be started with:

```text
dab start --mcp-stdio
```

Production should generally use a centrally managed HTTP endpoint with:

- TLS,
- authentication,
- network ACLs,
- dedicated identities,
- server-side RBAC.

---

## 6.2 Prometheus MCP

### Why it should be a high AEGIS priority

Prometheus is an ideal time-series telemetry substrate for AEGIS.

Prometheus MCP can let FERAL:

- list metrics,
- inspect labels/metadata,
- run PromQL,
- review target health,
- examine active alerts/rules,
- analyze historical metrics,
- correlate performance problems.

### Suggested AEGIS telemetry architecture

```text
Windows exporters -------+
SQL exporters -----------+
MOVEit custom metrics ---+
AEGIS metrics -----------+
Container metrics -------+
Application metrics -----+
                         |
                     Prometheus
                         |
                  Prometheus MCP
                         |
                     AEGIS / FERAL
```

### Production policy

Prometheus MCP should start as query/read-only from the AEGIS perspective.

AEGIS should allow only approved tools such as:

- query instant
- query range
- list metric names
- label metadata
- target status
- alert/rule inspection
- runtime/build information

Administrative operations should remain disabled until separately reviewed.

### Authentication

For centralized HTTP deployments:

- restrict network access,
- use Prometheus web authentication configuration where available,
- do not expose the MCP endpoint to untrusted networks,
- use a dedicated read-only service identity.

---

## 6.3 Grafana MCP

### Why it adds value beyond Prometheus

Grafana MCP can expose:

- dashboards,
- datasource metadata,
- Prometheus queries,
- Loki logs,
- alert information,
- annotations,
- incidents,
- Elasticsearch/OpenSearch,
- CloudWatch and other configured datasources.

This gives AEGIS a unified operational investigation layer.

### Recommended production mode

Use:

```text
--disable-write
```

Grafana explicitly documents this as a read-only mode.

For highly restricted AEGIS roles, also consider:

```text
--disable-query
```

which leaves metadata/discovery tools but removes datasource query tools.

### Recommended AEGIS use case

```text
Incident:
"Why did MOVEIT-A stop processing files at 02:14?"

AEGIS
  |
  +-- Windows Ops MCP: service/event state
  +-- Prometheus MCP: CPU, RAM, disk, network, exporter metrics
  +-- Grafana MCP: dashboards, Loki logs, alerts
  +-- SQL MCP: approved application state
  +-- MOVEit MCP: failover role and task state
  |
  +-- FERAL correlates evidence
```

This is significantly more powerful than an agent that only checks Windows service status.

---

# 7. Conditional Infrastructure MCPs

## 7.1 Kubernetes MCP

Use when AEGIS or customer workloads run on Kubernetes/OpenShift.

The `containers/kubernetes-mcp-server` implementation supports useful controls including:

```text
--read-only
--disable-destructive
--disable-multi-cluster
--toolsets
```

It can also deny sensitive resources such as Kubernetes Secrets.

### Production starting configuration

- read-only
- one cluster/context
- Secrets denied
- ConfigMaps evaluated separately
- explicit toolsets
- dedicated Kubernetes ServiceAccount with minimum RBAC

### AEGIS uses

- pod/deployment health
- logs
- node resource pressure
- events
- services
- workload status
- incident diagnosis

Writes should be a later phase.

---

## 7.2 Terraform MCP

HashiCorp's Terraform MCP provides current Terraform Registry information and can also integrate with HCP Terraform / Terraform Enterprise.

### Developer Desktop uses

- current provider documentation
- module discovery
- policy references
- accurate resource syntax
- infrastructure-code generation

### AEGIS uses

- infrastructure awareness
- topology context
- managed workspace information
- future automated deployment workflows

### Deployment

For a local workstation, use:

- stdio
- loopback only
- precompiled binary or controlled container

HashiCorp explicitly recommends localhost/stdio or loopback HTTP for local use and stronger authentication/TLS/network controls for remote deployment.

---

## 7.3 Azure DevOps MCP

Use if your organization uses Azure DevOps Services.

Useful for:

- Azure Repos
- Boards/work items
- build/pipeline information
- development workflow context

Keep it conditional because:

- it is service-dependent,
- Internet/service access is required,
- it is not needed for fully local Developer Desktop operation.

---

# 8. Lower-Priority Reference MCPs

## 8.1 Filesystem MCP

Use only for explicitly allowed directories outside the native Developer Desktop workspace.

The reference Filesystem server supports scoped directories and MCP Roots.

### Windows configuration concept

```json
{
  "mcpServers": {
    "filesystem": {
      "type": "stdio",
      "command": "cmd",
      "args": [
        "/c",
        "npx",
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "D:\\ApprovedData"
      ]
    }
  }
}
```

Do not expose:

- `C:\`
- user profiles
- credential directories
- entire source drives
- Windows system directories

when a narrower path will suffice.

---

## 8.2 Memory MCP

Useful for prototyping persistent knowledge, but the reference implementation should not become the permanent production AEGIS knowledge architecture without hardening.

Long term, AEGIS should own:

- data lifecycle,
- schema,
- retention,
- authorization,
- audit,
- encryption,
- environment separation,
- secret detection.

---

## 8.3 Sequential Thinking MCP

Useful for development and difficult analysis, but lower priority because it adds reasoning structure rather than new operational data.

Keep it optional.

---

# 9. Environment Deployment Matrix

## 9.1 Developer Desktop — Online

Enable:

- native AEGIS workspace tools
- Microsoft Learn MCP
- NuGet MCP
- GitHub MCP
- Git/local source-control tools
- Playwright MCP
- Chrome DevTools MCP
- SQL MCP when project needs DB access
- Terraform/Kubernetes conditionally

## 9.2 Developer Desktop — Air-Gapped

Enable:

- native AEGIS workspace tools
- local Git
- Playwright for localhost/internal applications
- Chrome DevTools with telemetry/CrUX/update checks disabled
- local SQL MCP
- internal NuGet source
- first-party AEGIS MCP servers
- local memory/knowledge service

Disable automatically:

- Microsoft Learn remote
- public GitHub
- public NuGet feed
- public Terraform Registry
- Azure DevOps Services
- any remote MCP endpoint

## 9.3 AEGIS 9 — Development/Test

Enable broad read-only testing:

- SQL MCP
- Prometheus MCP
- Grafana MCP `--disable-write`
- Playwright synthetic tests
- first-party Windows Ops MCP
- first-party AD MCP
- first-party MOVEit MCP

Write tools can be enabled against test systems with approval.

## 9.4 AEGIS 9 — Production

Production should be intentionally narrower:

- Prometheus: query/read tools only
- Grafana: `--disable-write`
- SQL: approved entities and roles only
- Windows Ops: read tools plus explicitly approved service operations
- AD: read tools; selected mutations gated
- MOVEit: monitoring plus tightly controlled failback workflow
- Playwright: synthetic account, isolated browser
- Git: read-only configuration/runbook context unless deployment workflow requires otherwise

---

# 10. AEGIS MCP Platform Architecture

AEGIS should implement a central **MCP Broker/Registry** rather than configuring servers independently inside every Agent.

```text
                    FERAL / Local Model
                           |
                           v
                 AEGIS Agent Tool Router
                           |
                           v
                  AEGIS MCP Broker
      +--------------------+--------------------+
      |                    |                    |
      v                    v                    v
  Policy Engine       Credential Broker      Audit Engine
      |                    |                    |
      +--------------------+--------------------+
                           |
            +--------------+--------------+
            |              |              |
            v              v              v
      Local stdio MCP   Internal HTTP   Remote MCP
            |              |              |
      Windows/AD/etc   SQL/Prom/Graf   Learn/GitHub
```

## 10.1 MCP Registry responsibilities

For every server record:

- logical name
- environment
- transport
- executable/endpoint
- version
- expected hash/signature
- health state
- tool list
- risk classification
- allowed roles
- allowed targets
- online/offline classification
- credential profile
- timeout
- concurrency limit
- audit requirements
- approval requirements

## 10.2 Example registry model

```json
{
  "id": "aegis.windows.ops",
  "displayName": "AEGIS Windows Operations",
  "transport": "stdio",
  "environment": ["dev", "test", "prod"],
  "connectivity": "local",
  "defaultPolicy": "read-only",
  "toolPolicies": {
    "windows.service.get": "R0",
    "windows.eventlog.query": "R1",
    "windows.service.restart": "W2"
  }
}
```

---

# 11. Tool Risk Classification

AEGIS should classify tools independently of the MCP server's own implementation.

## R0 — Normal read

Examples:

- service status
- CPU/memory
- repository status
- public documentation

Policy:
- normally no interactive approval
- always audited

## R1 — Sensitive read

Examples:

- security event logs
- AD user/group data
- production application logs
- database records

Policy:
- role-restricted
- target-restricted
- audited
- optional approval depending on data classification

## W1 — Low-risk reversible write

Examples:

- create non-production dashboard annotation
- create development file
- update noncritical development metadata

Policy:
- normal approval
- audit before/after state

## W2 — Privileged operational change

Examples:

- restart Windows service
- unlock AD account
- initiate MOVEit failback
- restart application workload

Policy:
- explicit approval
- preflight
- idempotency key
- post-validation
- rollback/compensation plan where possible

## D — Destructive / break-glass

Examples:

- delete production data
- delete Kubernetes namespace
- disable domain account
- remove database
- wipe container volume

Policy:
- disabled by default
- separate break-glass policy
- never autonomous

---

# 12. Why AEGIS Should Build Its Own MCP Servers

This is not primarily about reinventing MCP.

It is about **controlling the security boundary**.

## 12.1 Avoid arbitrary shell authority

A generic PowerShell MCP might expose:

```text
run any PowerShell command
```

That effectively gives the model the privileges of the MCP process.

AEGIS should instead expose:

```text
windows.service.get
windows.service.restart
windows.eventlog.query
windows.disk.get
```

Each operation can have:

- exact validation,
- exact authorization,
- bounded input,
- bounded output,
- predictable audit data.

## 12.2 Domain semantics matter

A generic Windows tool does not know:

- which server is the preferred MOVEit primary,
- which service is safe to restart,
- what stabilization period is required,
- what a successful failback means,
- which post-checks must pass.

A first-party AEGIS MCP can encode those constraints.

## 12.3 Better safety than prompt instructions

A prompt saying:

> "Do not restart both MOVEit servers"

is not a security boundary.

A tool implementation that refuses the second operation unless the topology state proves it is safe **is** a security boundary.

## 12.4 Better idempotency

Operational tools should detect repeated execution.

Example:

```text
moveit.failback.execute
requestId = 8f1...
```

If that failback already succeeded, a repeated identical call should return:

```text
already_completed
```

rather than triggering a second failback.

## 12.5 Air-gap support

First-party servers can be:

- compiled internally,
- signed,
- hash-pinned,
- distributed through internal software deployment,
- operated with zero cloud dependency.

## 12.6 Auditing

Every privileged operation can emit:

- actor/user
- Agent session ID
- request ID
- tool name
- target
- parameters with secrets redacted
- policy decision
- approval identity
- start/end time
- before state
- result
- after state
- validation result

## 12.7 Stable contract

Community tools can add/remove/rename operations.

AEGIS-owned tools can provide a versioned enterprise contract.

---

# 13. First-Party AEGIS MCP Server Suite

## 13.1 `Aegis.Mcp.Core`

Shared framework for every first-party server.

### Responsibilities

- MCP protocol host
- JSON schema validation
- policy metadata
- common errors
- correlation IDs
- audit events
- health endpoints
- cancellation/timeouts
- redaction
- target allowlists
- idempotency support
- structured result envelopes

### Recommended implementation

Use the official MCP SDK appropriate to the platform.

For the Windows enterprise servers, C#/.NET is a strong choice because:

- first-class Windows APIs,
- strong typing,
- mature Active Directory libraries,
- easy Windows service integration,
- direct alignment with other .NET components.

Target the organization's current supported .NET enterprise baseline. For new tooling, .NET 10 is a reasonable target where approved; retain compatibility with the existing AEGIS runtime requirements.

---

# 14. AEGIS Windows Operations MCP

## 14.1 Purpose

Provide safe Windows Server operational capability without exposing arbitrary PowerShell.

## 14.2 Initial tool set

### Read tools

```text
windows.host.get
windows.os.get
windows.service.list
windows.service.get
windows.process.list
windows.process.get
windows.eventlog.query
windows.disk.list
windows.disk.get
windows.network.get
windows.port.test
windows.performance.sample
windows.scheduledtask.list
windows.scheduledtask.get
```

### Controlled write tools

```text
windows.service.start
windows.service.stop
windows.service.restart
windows.scheduledtask.run
```

### Do not initially expose

```text
powershell.execute_arbitrary
cmd.execute_arbitrary
registry.write_arbitrary
process.kill_arbitrary
file.delete_arbitrary
```

## 14.3 Remote execution strategy

Prefer, in order:

1. local Windows APIs when MCP server runs on target,
2. CIM/WMI over approved enterprise remoting,
3. WinRM through a constrained endpoint,
4. PowerShell JEA for commands that require PowerShell.

Do not give the MCP service unconstrained administrative PowerShell if JEA can expose only the required commands.

## 14.4 Identity

For enterprise deployment:

- use dedicated service identities,
- consider gMSA where appropriate,
- deny interactive logon,
- restrict remote logon rights,
- grant only required service-control/event-log/CIM rights.

## 14.5 Acceptance tests

- cannot operate against a host outside allowlist
- cannot restart unapproved service
- timeout works
- repeated restart uses idempotency behavior
- before/after state is audited
- denied operation produces deterministic policy error
- secret values never appear in Agent output

---

# 15. AEGIS Active Directory MCP

## 15.1 Purpose

Provide directory intelligence and narrowly controlled account operations.

## 15.2 Read tools

```text
ad.user.get
ad.user.search
ad.user.lockout_status
ad.group.get
ad.group.members
ad.computer.get
ad.computer.search
ad.domain.get
ad.domaincontroller.list
ad.domaincontroller.health
```

## 15.3 Controlled writes

Later phase:

```text
ad.user.unlock
ad.group.member.add
ad.group.member.remove
```

## 15.4 High-risk operations

Do not make autonomous initially:

```text
ad.user.disable
ad.user.enable
ad.password.reset
ad.object.delete
ad.group.delete
```

Password operations should remain outside normal Agent autonomy unless a specific enterprise workflow is approved.

## 15.5 Implementation

For reads:

- LDAP/System.DirectoryServices.Protocols is preferred where feasible.

For privileged writes:

- typed LDAP operations, or
- constrained PowerShell/JEA wrappers around exact AD cmdlets.

## 15.6 Security

- domain/OU scope allowlists
- attribute allowlists
- output redaction
- separate read and mutation identities if possible
- group mutation allowed only for approved groups
- all mutations require explicit approval

---

# 16. AEGIS MOVEit Operations MCP

## 16.1 Why this should be first-party

MOVEit failover/failback is a business-critical operational workflow.

Generic Windows, SQL, or shell tools do not understand the safety requirements of MOVEit HA.

Progress documentation confirms that in failover operation:

- only one node should be primary at a time,
- the secondary is passive,
- nodes exchange failover state,
- the secondary monitors primary availability,
- both nodes cooperate to prevent dual-primary operation,
- failover configuration uses specific failover communication paths,
- current Progress documentation lists ports 3472 and 3473 for failover,
- a single Microsoft SQL Server instance has specific failover configuration considerations.

The MCP should therefore model MOVEit as a **state machine**, not as a set of unrestricted Windows commands.

## 16.2 Tool set

### Discovery/read

```text
moveit.environment.get
moveit.node.list
moveit.node.health
moveit.node.role
moveit.failover.status
moveit.failover.history
moveit.database.health
moveit.tasks.summary
moveit.active_transfers.summary
moveit.failback.eligibility
```

### Controlled workflow actions

```text
moveit.failback.plan
moveit.failback.execute
moveit.failback.abort
moveit.failback.validate
```

Do not expose:

```text
moveit.database.execute_arbitrary_sql
moveit.registry.write_arbitrary
moveit.service.force_both_nodes
```

## 16.3 Failback eligibility

`moveit.failback.eligibility` should produce a deterministic object such as:

```json
{
  "eligible": true,
  "preferredPrimary": "MOVEIT-A",
  "currentPrimary": "MOVEIT-B",
  "preferredPrimaryHealthy": true,
  "preferredPrimaryStableSeconds": 600,
  "databaseHealthy": true,
  "dualPrimaryRisk": false,
  "activeTransfers": 0,
  "blockingReasons": []
}
```

## 16.4 Failback preflight

Before `moveit.failback.execute` can run:

1. identify current active node,
2. confirm preferred primary,
3. verify both node identities,
4. verify preferred-primary host health,
5. verify MOVEit service health,
6. verify failover communication ports,
7. verify SQL connectivity,
8. verify shared-database state,
9. verify no dual-primary condition,
10. verify stabilization timer,
11. verify no blocked operational condition,
12. capture current state,
13. obtain W2 approval,
14. acquire distributed failback lock,
15. issue one idempotency token.

## 16.5 Execution

The actual role transition must use a **Progress-supported administration mechanism**.

Preferred order:

1. documented MOVEit REST API where the required operation is supported,
2. documented MOVEit Windows API,
3. documented MOVEit administrative command/interface,
4. validated vendor-supported operational procedure wrapped by AEGIS.

Do **not** implement failback by editing MOVEit database rows directly unless Progress explicitly documents that technique as supported.

## 16.6 Post-validation

A failback is not complete when the preferred server merely starts.

Validation should include:

- exactly one primary,
- preferred node is primary,
- other node is passive,
- SQL reachable,
- MOVEit service healthy,
- failover communication healthy,
- task scheduler correct,
- no duplicate processing,
- test/synthetic transfer where approved,
- monitoring event cleared,
- final state recorded.

## 16.7 AEGIS Monitoring integration

Every failback workflow should publish:

```text
AEGIS.MOVEit.Failback.State
AEGIS.MOVEit.Failback.Elapsed
AEGIS.MOVEit.Failback.Result
AEGIS.MOVEit.Node.Role
AEGIS.MOVEit.Node.Health
AEGIS.MOVEit.Failover.Communication
AEGIS.MOVEit.Database.Health
```

These should be visible in AEGIS 9 monitoring and optionally exported to Prometheus.

---

# 17. AEGIS SQL Operations MCP

Do not rebuild Microsoft's SQL MCP engine unless necessary.

Instead, build an AEGIS-specific **domain layer** above SQL MCP/Data API Builder.

## 17.1 Pattern

```text
FERAL
  |
Aegis.Mcp.SqlOps
  |
Microsoft SQL MCP / Data API Builder
  |
approved views / stored procedures / entities
  |
SQL Server
```

## 17.2 Benefits

- Microsoft maintains the SQL protocol/data layer
- AEGIS owns business semantics
- no arbitrary SQL needed
- database permissions remain authoritative

## 17.3 Example tools

```text
sqlops.moveit.health
sqlops.moveit.transfer_summary
sqlops.application.health
sqlops.job.status
```

Each maps to an approved entity/view rather than a model-generated SQL string.

---

# 18. Optional AEGIS Observability MCP

Prometheus and Grafana MCP should be used directly at first.

Later, AEGIS may add:

```text
Aegis.Mcp.Observability
```

with high-level tools:

```text
observability.incident.snapshot
observability.host.timeline
observability.application.timeline
observability.compare_before_after
```

The server would orchestrate Prometheus, Grafana/Loki, Windows Ops, and SQL data into one bounded result.

This reduces context consumption and avoids requiring the model to execute dozens of low-level metric queries for common incidents.

---

# 19. Approval and Policy Architecture

Tool authorization must exist outside the model.

```text
Model requests tool
      |
      v
Schema validation
      |
      v
Target allowlist
      |
      v
Role authorization
      |
      v
Risk classification
      |
      +-- R0 -> execute
      +-- R1 -> policy-dependent
      +-- W1 -> normal approval
      +-- W2 -> explicit privileged approval + preflight
      +-- D  -> deny unless break-glass
      |
      v
Execution
      |
      v
Post-validation
      |
      v
Audit
```

The model cannot override a policy decision through prompt text.

---

# 20. Credentials Architecture

Never place production credentials directly inside the LLM prompt or normal MCP JSON.

Use a credential broker.

## Recommended Windows options

- Windows Credential Manager where appropriate
- DPAPI-protected local secret material
- gMSA for Windows service identities
- certificate-based service authentication
- enterprise vault integration if available

The MCP server receives only the credential required for its target and operation.

The model should receive:

```text
credentialProfile = moveit-production-read
```

not the password/token itself.

---

# 21. Logging and Audit

Every first-party tool invocation should create a structured audit event.

Example:

```json
{
  "timestamp": "2026-09-06T15:12:03Z",
  "sessionId": "agent-...",
  "requestId": "req-...",
  "user": "domain\\user",
  "server": "aegis.moveit.ops",
  "tool": "moveit.failback.execute",
  "target": "MOVEIT-PAIR-01",
  "risk": "W2",
  "approval": "approved",
  "result": "success",
  "durationMs": 84321,
  "validation": "passed"
}
```

Secrets and sensitive payloads must be redacted before logging.

---

# 22. Health Monitoring for MCP Servers

AEGIS 9 should monitor MCP servers as first-class infrastructure.

Track:

- configured
- enabled
- process/endpoint health
- MCP initialize success
- tool discovery success
- tool count
- version
- last successful call
- error rate
- latency
- restart count
- credential failure
- policy denial count
- incompatible protocol/server version

Suggested states:

```text
Healthy
Degraded
Unavailable
Disabled
Quarantined
VersionMismatch
AuthenticationFailure
```

If a production MCP server becomes unhealthy, AEGIS should remove its tools from the model rather than allowing repeated tool failures.

---

# 23. Version and Supply-Chain Policy

Do not use rolling `@latest` package references permanently in production.

## Development

`@latest` is acceptable for discovery/testing.

## Production

After validation:

1. record version,
2. record source repository,
3. record package hash/signature where practical,
4. store approved package internally,
5. pin exact version,
6. scan dependencies,
7. test with MCP Inspector,
8. promote through dev -> test -> production.

Maintain an AEGIS MCP catalog containing:

```text
name
vendor
version
license
source
hash
approval date
reviewer
known risks
network requirements
```

---

# 24. Implementation Phases

## Phase 0 — MCP Governance Baseline

### Deliverables

- MCP architecture decision record
- tool risk classification
- online/offline profiles
- MCP server catalog schema
- credential rules
- audit schema
- approval matrix
- production version-pinning policy

### Acceptance

No MCP integration enters production without a registry entry and policy classification.

---

## Phase 1 — AEGIS MCP Broker / Registry

### Implement

- stdio and Streamable HTTP client support
- dynamic `tools/list`
- server health checks
- tool allowlist/exclude list
- environment-specific enablement
- online/offline classification
- per-tool risk metadata
- audit integration
- credential references
- server restart/quarantine

### Developer Desktop integration

Expose MCP tools to FERAL through the existing Agent tool-routing layer.

### Acceptance

FERAL receives only approved tools for the active task.

---

## Phase 2 — Developer Desktop P0 Integrations

Integrate:

1. Microsoft Learn
2. NuGet
3. GitHub read-only
4. Playwright
5. Chrome DevTools
6. SQL MCP
7. local Git

### Validation scenarios

- FERAL verifies a .NET API using Microsoft Learn
- FERAL resolves a package version with NuGet
- FERAL reads a GitHub issue and correlates it with local code
- FERAL modifies a web feature and tests it with Playwright
- FERAL diagnoses browser error/performance with Chrome DevTools
- FERAL inspects approved SQL entities

---

## Phase 3 — AEGIS Observability

Deploy:

- Prometheus
- Prometheus MCP
- Grafana
- Grafana MCP read-only
- Windows exporters / AEGIS exporters
- selected application metrics

### Acceptance

FERAL can answer a host/application incident question using correlated monitoring evidence without production write access.

---

## Phase 4 — AEGIS Windows Operations MCP

Implement read tools first.

Then add service start/stop/restart with W2 policy.

### Acceptance

- host allowlists enforced
- service allowlists enforced
- no arbitrary shell
- audited before/after state
- approval required for mutations

---

## Phase 5 — AEGIS Active Directory MCP

Implement read-only domain/user/group/computer operations.

Then add account unlock.

### Acceptance

- OU/domain scopes enforced
- no password exposure
- no arbitrary LDAP mutation
- all writes approved/audited

---

## Phase 6 — AEGIS MOVEit Operations MCP

Integrate the existing MOVEit auto-failback workflow into typed MCP tools.

### Milestones

1. topology/status tools
2. failback eligibility
3. plan/preflight
4. lab failback execution
5. post-validation
6. monitoring integration
7. production approval

### Critical acceptance

AEGIS must never create a dual-primary state.

---

## Phase 7 — SQL Domain Wrappers

Create AEGIS-approved SQL views/entities for:

- MOVEit health
- application health
- workflow status
- operational history

Expose through SQL MCP/Data API Builder and Aegis.Mcp.SqlOps.

---

## Phase 8 — Production Hardening

- package pinning
- code signing
- SBOM generation
- dependency scanning
- fuzz/schema testing
- authorization tests
- fail-closed behavior
- rate limits
- timeout/cancellation testing
- disaster recovery
- server quarantine
- centralized audit retention
- penetration/security review

---

# 25. Suggested Repository Structure

```text
AEGIS/
|
+-- src/
|   +-- Aegis.Mcp.Core/
|   +-- Aegis.Mcp.Broker/
|   +-- Aegis.Mcp.Windows/
|   +-- Aegis.Mcp.ActiveDirectory/
|   +-- Aegis.Mcp.MoveIt/
|   +-- Aegis.Mcp.SqlOps/
|   +-- Aegis.Mcp.Observability/       # later
|
+-- tests/
|   +-- Aegis.Mcp.Core.Tests/
|   +-- Aegis.Mcp.Windows.Tests/
|   +-- Aegis.Mcp.ActiveDirectory.Tests/
|   +-- Aegis.Mcp.MoveIt.Tests/
|   +-- Aegis.Mcp.Security.Tests/
|
+-- config/
|   +-- mcp/
|       +-- catalog.json
|       +-- policy.json
|       +-- development.json
|       +-- test.json
|       +-- production.json
|       +-- airgapped.json
|
+-- docs/
    +-- mcp/
        +-- architecture.md
        +-- security-model.md
        +-- tool-catalog.md
        +-- deployment.md
        +-- operations.md
```

---

# 26. Minimum Test Suite for First-Party MCP Servers

Every server should test:

## Protocol

- initialize
- tools/list
- tools/call
- malformed arguments
- cancellation
- timeout
- server shutdown/restart

## Security

- target outside allowlist
- unauthorized tool
- unauthorized role
- malformed host/path
- command injection strings
- LDAP injection strings
- SQL injection strings
- path traversal
- secret redaction
- oversized input/output

## Operations

- idempotent repeat
- partial failure
- remote host unavailable
- credential expiration
- approval denied
- post-validation failure

## Model-behavior regression

Use actual local FERAL models to verify:

- correct tool choice
- no unsafe fallback to arbitrary commands
- no repeated state-changing calls
- proper handling of denied tools
- proper handling of partial results

---

# 27. Recommended Rollout Order

## Immediate

### Developer Desktop

1. Microsoft Learn MCP
2. NuGet MCP
3. GitHub MCP in read-only mode
4. Playwright MCP
5. Chrome DevTools MCP with outbound diagnostics disabled
6. Microsoft SQL MCP
7. local Git

### AEGIS 9

1. Microsoft SQL MCP
2. Prometheus MCP
3. Grafana MCP `--disable-write`
4. Playwright synthetic monitoring

## Next

1. MCP Broker/Registry
2. Windows Operations MCP
3. Active Directory MCP
4. MOVEit Operations MCP

## Later / technology-driven

1. Kubernetes MCP
2. Terraform MCP
3. Azure DevOps MCP
4. AEGIS Observability aggregation MCP
5. AEGIS production memory/knowledge MCP

---

# 28. Final Recommendation

The best long-term architecture is not:

```text
FERAL -> dozens of unrestricted MCP servers
```

It is:

```text
                         FERAL
                           |
                 AEGIS Agent Router
                           |
                 AEGIS MCP Broker
                           |
        +------------------+------------------+
        |                  |                  |
   Native AEGIS       Vetted Vendor      AEGIS First-Party
      Tools                MCPs                MCPs
        |                  |                  |
 workspace/editor   docs/source/SQL/      Windows/AD/MOVEit/
       tools         observability        privileged operations
```

The distinction is important:

- **Developer Desktop** benefits most from MCP servers that improve software-development knowledge, source control, package intelligence, database context, and browser testing.
- **AEGIS 9** benefits most from MCP servers that provide structured operational telemetry, SQL data, browser-based synthetic validation, and controlled enterprise administration.
- **Privileged operations should be first-party AEGIS MCPs**, because AEGIS can enforce business-specific safety rules that a generic community server cannot know.

The first-party MCP work is therefore not optional architectural duplication. It is the mechanism that lets AEGIS evolve from "an AI with tools" into a **governed enterprise agent platform**.

---

# 29. Validated Source References

Validation was performed against current vendor/official sources available on 2026-09-06.

## MCP reference servers

- Model Context Protocol reference servers  
  https://github.com/modelcontextprotocol/servers
- Filesystem MCP reference server  
  https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem

## Microsoft

- Microsoft Learn MCP Server  
  https://learn.microsoft.com/en-us/training/support/mcp
- Microsoft Learn MCP developer reference  
  https://learn.microsoft.com/en-us/training/support/mcp-developer-reference
- Microsoft Learn MCP best practices  
  https://learn.microsoft.com/en-us/training/support/mcp-best-practices
- NuGet MCP Server  
  https://learn.microsoft.com/en-us/nuget/concepts/nuget-mcp-server
- Microsoft SQL MCP Server  
  https://learn.microsoft.com/en-us/sql/mcp/
- SQL MCP / Data API Builder overview  
  https://learn.microsoft.com/en-us/azure/data-api-builder/mcp/overview
- Azure DevOps MCP Server  
  https://learn.microsoft.com/en-us/azure/devops/mcp-server/remote-mcp-server?view=azure-devops

## Source control

- GitHub MCP Server  
  https://github.com/github/github-mcp-server
- GitHub MCP server configuration  
  https://github.com/github/github-mcp-server/blob/main/docs/server-configuration.md

## Browser automation / diagnostics

- Playwright MCP  
  https://github.com/microsoft/playwright-mcp
- Playwright MCP documentation  
  https://github.com/microsoft/playwright.dev/blob/main/mcp/installation.mdx
- Chrome DevTools MCP  
  https://github.com/ChromeDevTools/chrome-devtools-mcp

## Observability

- Prometheus MCP  
  https://github.com/prometheus/prometheus-mcp
- Grafana MCP  
  https://github.com/grafana/mcp-grafana

## Infrastructure

- Kubernetes MCP Server  
  https://github.com/containers/kubernetes-mcp-server
- Terraform MCP Server  
  https://developer.hashicorp.com/terraform/mcp-server
- Terraform MCP deployment guidance  
  https://developer.hashicorp.com/terraform/mcp-server/deploy

## MOVEit Automation

- MOVEit Automation 2026 documentation  
  https://docs.progress.com/category/moveit-automation-2026
- MOVEit Automation Failover requirements  
  https://docs.progress.com/bundle/moveit-automation-web-admin-help-2026/page/Requirements.html
- MOVEit Automation Failover overview  
  https://docs.progress.com/bundle/moveit-automation-web-admin-help-2026/page/Overview.html
- MOVEit Automation failover setup  
  https://docs.progress.com/bundle/moveit-automation-web-admin-help-2026/page/Step-by-Step-Instructions.html
- MOVEit Automation failover behavior  
  https://docs.progress.com/bundle/moveit-automation-web-admin-help-2025/page/How-Failover-Works.html

---

# 30. Implementation Decision Summary

| Decision | Recommendation |
|---|---|
| Use every available MCP | No |
| Native workspace tools remain primary | Yes |
| Add Microsoft Learn | Yes, Developer Desktop P0 |
| Add NuGet MCP | Yes, Developer Desktop P0 |
| Add GitHub MCP | Yes, read-only first |
| Add Microsoft SQL MCP | Yes, both environments |
| Add Playwright | Yes, both |
| Add Chrome DevTools | Yes, Developer Desktop |
| Add Prometheus MCP | Yes, AEGIS |
| Add Grafana MCP | Yes, AEGIS read-only |
| Add Kubernetes | Conditional |
| Add Terraform | Conditional |
| Use generic unrestricted Docker MCP | No |
| Use old PostgreSQL reference server | No |
| Use archived SQLite reference server | No |
| Build AEGIS Windows MCP | Yes |
| Build AEGIS AD MCP | Yes |
| Build AEGIS MOVEit MCP | Yes |
| Wrap SQL with AEGIS domain tools | Yes |
| Allow arbitrary shell from production MCP | No |
| Require version pinning and audit | Yes |
| Support separate online/air-gapped MCP profiles | Yes |

---

**End of document**
