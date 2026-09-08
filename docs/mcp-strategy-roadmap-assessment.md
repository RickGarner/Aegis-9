# MCP Strategy Roadmap Assessment

**Date:** 2026-09-06  
**Input:** `AEGIS9_DeveloperDesktop_MCP_Strategy_and_Implementation_Plan.md`  
**Status:** Adopted as roadmap input; server/version claims require verification
before installation or production promotion.

## Conclusion

The proposed three-tier architecture fits the current Aegis roadmap:

1. Native Aegis tools remain primary for workspace and workflow operations.
2. Vetted vendor MCP servers supply authoritative domain capabilities.
3. Aegis-owned MCP servers encapsulate privileged enterprise operations.

This refines, rather than replaces, Developer Studio Priority 7F and the seven
platform-backlog entries in `SHARED-TOOL-PARITY-CONTRACT.json`. Both products
remain independent clients of the same versioned policy and registry contract;
neither product is required to be running for the other to use MCP.

## Required sequencing change

The portable `getMcpTools` tool may be implemented in the next parity group,
but initially it must be a **registry discovery view only**. It must not scan
arbitrary processes, install packages, start unapproved servers, return secrets,
or automatically expose newly discovered tools to a model.

Before a live MCP tool reaches DMR, Ollama, or another qualified local model,
the following platform foundation is required:

1. Versioned local registry/catalog and environment/connectivity profiles.
2. `stdio`, loopback HTTP, and approved private-LAN transport lifecycle.
3. Schema validation and immutable per-request tool exposure.
4. R0/R1/W1/W2/D risk, role, target, and approval policy.
5. Credential references resolved outside prompts and tool arguments.
6. Destination policy, DNS/redirect/proxy revalidation, and outbound DLP.
7. Local redacted audit/telemetry plus health, restart, and quarantine state.
8. Version pinning, hashes/signatures where practical, and promotion evidence.

## Roadmap placement

### MCP Phase 0 — Governance baseline

- Adopt the registry schema, risk levels, connectivity profiles, credential
  reference rules, audit envelope, approval matrix, and version-pinning policy.
- Extend classifications beyond transport location: private addressing alone
  does not establish trust.
- Acceptance: an unregistered server/tool and an unclassified outbound field
  are denied.

### MCP Phase 1 — Independent broker/registry clients

- Implement the same registry schema, discovery semantics, policy decisions,
  and result envelope in Aegis 9 and Developer Studio.
- Each application owns its client/lifecycle and can operate without the other.
- Support disabled, healthy, degraded, unavailable, quarantined,
  version-mismatch, and authentication-failure states.
- Acceptance: `getMcpTools` returns only enabled, healthy, task-eligible tools;
  discovery grants no authority and leaks no credential material.

### MCP Phase 2 — Local and read-only pilot servers

- Start with pinned local/loopback servers and disposable test data.
- Recommended first validation targets: local Git (only if it adds value beyond
  native Git), Playwright against localhost, local/internal SQL entities, and
  Chrome DevTools with usage statistics, CrUX, and update checks disabled.
- Do not add Filesystem MCP for active workspaces already covered by native
  tools. Do not add unrestricted shell or Docker administration MCP.

### MCP Phase 3 — Organization-controlled services

- Add internal NuGet feeds, SQL/Data API Builder entities, Prometheus, Grafana
  in read-only mode, and approved internal GitHub Enterprise/Azure DevOps where
  applicable.
- Require an owner, exact endpoint identity, permitted fields, retention
  behavior, least-privilege credential profile, and local audit destination.

### MCP Phase 4 — Optional public zero-protected-data services

- Microsoft Learn and public package/document lookup may be offered only in an
  explicitly enabled online profile when the outbound request schema contains
  no prompt, code, repository metadata, credentials, telemetry, arguments, or
  results classified as protected.
- Public GitHub and other service-dependent integrations remain disabled by
  default and must never be required for local-only operation.

### MCP Phase 5 — First-party enterprise servers

- Build `Aegis.Mcp.Core`, then read-only Windows Operations, Active Directory,
  and MOVEit Operations tools.
- Add write tools only after lab tests, deterministic preflight, explicit
  approval, idempotency, post-validation, audit, and compensation behavior.
- MOVEit remains a typed state machine; no arbitrary SQL, shell, service, or
  dual-primary operation is exposed.

### MCP Phase 6 — Production hardening and air-gap acceptance

- Pin packages, preserve approved artifacts internally, record hashes/licenses,
  scan dependencies, test malformed calls/cancellation/timeouts, and exercise
  quarantine/recovery.
- Prove local MCP and local models continue working with all public network
  access blocked.

## Candidate disposition

| Candidate | Disposition | Initial placement |
|---|---|---|
| Microsoft SQL/Data API Builder | Adopt, entity/RBAC constrained | Both; local/internal read-only first |
| Prometheus | Adopt | Aegis 9 read-only observability |
| Grafana | Adopt with writes disabled | Aegis 9 read-only observability |
| Playwright | Adopt with isolated profiles | Both; localhost/test first |
| Chrome DevTools | Adopt with telemetry/CrUX/update disabled | Developer Studio test profile |
| Microsoft Learn | Conditional | Online zero-protected-data profile |
| NuGet | Conditional | Internal feed first; public lookup online-only |
| GitHub | Conditional | Read-only; GHES/internal preferred |
| Local Git MCP | Defer unless capability gap is proven | Native Git remains primary |
| Kubernetes/Terraform/Azure DevOps | Technology-driven | Add only with an owned target/use case |
| Filesystem/Memory reference servers | Prototype only | Harden or replace before production |
| Sequential Thinking | Low priority | No new operational data |
| Generic Docker or shell MCP | Reject | Excessive authority |
| Deprecated PostgreSQL/archived SQLite references | Reject | Select maintained alternatives if needed |

## Relationship to the shared-tool roadmap

`getMcpTools` belongs in the portable tool parity backlog and should be present
in both products. The broker/lifecycle, private-LAN governance, telemetry,
network policy, DLP, and air-gap proof remain **platform capabilities**, not
model-callable tools. They must therefore remain in the platform backlog and
must not be marked complete merely because discovery UI or schemas exist.

The immediate next implementation may add:

- registry schema and local configuration loader;
- read-only `getMcpTools` over approved registry records;
- default-deny policy tests;
- identical contract fixtures in both repositories.

It must not install or connect to the recommended servers yet. Endpoint,
credential, package/version, licensing, privacy, and internal-owner validation
belong to the later pilot and promotion phases.

## Registry hardening checkpoint — 2026-09-06

`independentLocalMcpRegistry` is complete in both products. Entries are bounded
and closed-schema; IDs must be unique; transports must match the active
connectivity profile; loopback hosts are exact; external transport requires
HTTPS; URLs cannot contain credentials; stdio commands are absolute and
SHA-256-pinned; credentials are references only; and W1/W2/D tools require
approval. Identical JSON Schema and air-gapped/local-network/online profiles
exist under each product's `config/mcp` directory. Catalogs remain empty.
Lifecycle, live health probing, credential resolution, networking/DLP, audit
storage, and server calls remain outstanding.

## Lifecycle and destination-policy checkpoint — 2026-09-06

Both products now independently implement pinned stdio and policy-approved
loopback HTTP MCP lifecycle foundations: initialize, initialized notification,
tools/list, allowlisted tools/call, bounded timeout, shutdown, failure counting,
and quarantine after repeated failures. HTTP redirects are denied rather than
followed automatically, proxies are disabled/prohibited, and catalogs remain
empty so nothing starts in normal operation.

The shared network destination policy requires exact host and port allowlists,
resolves and classifies every address, rejects mixed/restricted DNS answers,
limits air-gapped mode to loopback, permits private addresses only in the
appropriate profiles, requires TLS off loopback, and detects destination/DNS
changes during redirect revalidation. This completes the lifecycle and network
policy foundations, but does not enable private-LAN MCP. Credential resolution,
outbound DLP/schema enforcement, durable telemetry/audit, and air-gap acceptance
remain prerequisites.

## Telemetry, DLP, private-LAN, and air-gap readiness — 2026-09-06

Both products now contain bounded local JSONL audit stores with recursive
secret redaction and retention compaction. Outbound DLP rejects undeclared
fields, credential material, oversized payloads, unclassified destinations,
and protected data sent to external-zero-protected-data services. MCP tool calls
enforce role, target, approval, outbound schema, DLP, and redacted audit before
transport. Private HTTP is admitted only by the local-network profile for an
organization-controlled registry record and a destination-policy-approved TLS
endpoint.

Both products also include `Test-AegisAirgapReadiness.ps1`. Code-level readiness
passes, but `airGappedAcceptance` remains open until a clean machine test blocks
public networking at the OS/firewall layer and verifies live DMR, Ollama
failover, native tools, workflow generation, local MCP, and zero outbound
protected data.

## Implementation checkpoint — 2026-09-06

The initial registry-only discovery increment is complete in both products.
Each repository contains `config/mcp/catalog.json` with schema version 1, the
`airgapped` profile, and no server registrations. `getMcpTools` returns only
enabled tools on enabled, healthy registry servers, marks results as discovery
only, and explicitly grants no authority. Quarantined and unhealthy entries are
excluded. No MCP server was installed, started, contacted, or approved. Broker
lifecycle, credential resolution, destination/DLP enforcement, health probing,
audit, and populated catalog records remain outstanding platform work.
