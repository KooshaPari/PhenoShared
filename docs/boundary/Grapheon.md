# Boundary — Grapheon

> Standalone private Grapheon/Tracera runtime. Boundary file created
> 2026-07-17 and reconciled 2026-07-27 after recovery-branch audit.

## In Scope

- **Graph server runtime** — claims/evidence graph store with HTTP
  transport layer.
- **Persistence adapters** — pluggable backends (MemoryPort trait
  integration via thegent-memory for episodic memory, optional
  Postgres/SQLite bindings).
- **HTTP server** — accepts REST requests at `/intents`, `/claims`,
  `/evidence`, `/graph` paths; returns JSON.
- **CLI** — `grapheon-server` and `grapheon-admin` binaries.

## Out of Scope

| Not here | Lives in | Reason |
| -------- | -------- | ------ |
| FFI consumer bindings | `pheno-cdylib-bridge` (in `pheno` monorepo) | Rust↔Go C-ABI surface |
| Go HTTP client | `phenotype-go-sdk/packages/graphclient` | SDK wrapper, not server |
| AI agent runtime | `thegent` | Grapheon is a data layer; thegent orchestrates agents |
| Auth | `Authvault` (AuthKit absorbed) | Tokens & vault surface |

## Boundary Crossings

| Crossing | Direction | Surface | Status |
| -------- | --------- | ------- | ------ |
| MemoryProvider | Grapheon → thegent-memory | Trait impl | green |
| HTTP /intents | Clients → Grapheon | REST JSON | green |
| MCP server | `PhenoMCPServers` → Grapheon | MCP protocol | amber (gate review pending) |
| FFI | `pheno-cdylib-bridge` → Grapheon | `extern "C"` shim | green |

## Last Boundary Review

**Date:** 2026-07-27
**Reviewer:** registry boundary audit (recovery/default-branch verification)
**Disposition:** `KEEP_STANDALONE_PENDING_BOUNDARY_REVIEW`
**Decisions:**
- The prior ABSORB proposal into `pheno/crates/grapheon/` is stale and is
  withdrawn. Current `Grapheon` is a private, non-archived recovery branch
  whose active Cargo workspace is the Tracera runtime (`tracera-server`,
  `tracertm-mcp`, `tracera-edge`).
- `pheno` exposes `agileplus-graph`, a distinct graph layer; no source-to-target
  mapping for the current repository is proven.
- Preserve the separate `grapheon-bindings` SDK record; this review does not
  rewrite its historical absorption claim.

**Evidence:** repository head `58ce84b2071ab0b7cf8bae5ec294d5613f3ee96a`,
80,510 tracked paths, and 722 MB of Git objects on the recovery checkout.

**Next review:** after a sponsor-approved parent/child boundary proposal
