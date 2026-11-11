# ADR 0006: No MCP host / server surface

- Status: Accepted
- Date: 2026-07-17
- Decision owners: SessionLedger maintainers
- Related: `docs/adr/0001-desktop-companion-scope.md`, `AGENTS.md`, `llms.txt`, audit-v38 C06 L57

## Context

SessionLedger ships as a **local daemon** (`sl-daemon`) plus a **desktop / web
viewer** (`sl-viewer`). It watches local session files, writes OKF artifacts to
a host directory, and serves a loopback HTTP API for compile / search / replay.

Audit-v38 C06 L57 asks for MCP server provenance (pinned MCP / phenoMCP server
lists, host manifests, and similar). SessionLedger is a session compiler and
local companion — it is **not** an MCP host, MCP client product surface, or MCP
server that tools connect to. There is no MCP pin list to maintain.

## Decision

SessionLedger **does not** ship an MCP host, MCP server, or MCP server pin list
(`mcp.json`, `.mcp.json`, phenoMCP pin files, or equivalent).

Surfaces that **are** in scope remain:

1. Agent entry docs (`AGENTS.md`, `llms.txt`) for humans and coding agents
2. Local loopback HTTP for the viewer ↔ daemon contract
3. Session / OKF artifact provenance on the operator’s machine

Absence of MCP server configs and pin lists is **intentional**, not an
unfinished gap. L57 evidence is this ADR + entry-doc cross-links (N/A with
explicit decision), not an MCP scaffold.

## Consequences

- Supply-chain / provenance checks do not require an MCP pin matrix.
- Agents discover build and scope via `AGENTS.md` / `llms.txt`, not MCP
  tool manifests.
- Revisit only when a product phase introduces MCP servers or an MCP host
  that SessionLedger operates or pins.

## Revisit triggers

| Trigger                                           | Why                                     |
| ------------------------------------------------- | --------------------------------------- |
| SessionLedger hosts or exposes MCP tools          | Pin list + provenance become required   |
| Product ships an MCP server crate or binary       | Superseding ADR before adding manifests |
| Explicit customer requirement for MCP integration | Record scope and pin policy first       |
