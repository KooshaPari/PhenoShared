# Boundary — PhenoMCPServers

> Phenotype MCP server set. Boundary file created 2026-07-17 during
> registry batch4 refresh.

## In Scope

- **Multi-server MCP registry** — exposes a set of MCP servers under
  the `phenotype` namespace, each backed by a Phenotype-org crate.
- **Server catalog**: `pheno-mcp-router` (intent routing),
  `pheno-mcp-config` (config surface), `pheno-mcp-tracing` (telemetry
  OTel), `pheno-mcp-assets` (asset bundle), `pheno-mcp-ops`
  (deployment ops).
- **Process orchestration** — single binary that boots all server
  components on shared tokio runtime.

## Out of Scope

| Not here | Lives in | Reason |
| -------- | -------- | ------ |
| MCP client libraries | `McpKit` (TypeScript), `phenotype-go-sdk/packages/mcp` (Go) | Different language surfaces |
| Individual server implementations | See specific PhenoMCPServers catalog | Each server is a subcomponent |
| Discovery protocol | `PhenoMCP-cheap` / `PhenotypeMCP` | Discovery is a separate spine concern |

## Boundary Crossings

| Crossing | Direction | Surface | Status |
| -------- | --------- | ------- | ------ |
| MCP clients → PhenoMCPServers | external | MCP JSON-RPC over stdio/HTTP | green |
| `phenotype-mcp-asset` → Grapheon | internal | HTTP /intents | amber |
| `phenotype-mcp-ops` → Agentora | internal | MessageRouter | amber |

## Last Boundary Review

**Date:** 2026-07-17
**Reviewer:** registry batch4 audit (queue-refresh-batch4)
**Disposition-index row:** DSPI-NEW (`repo-PhenoMCPServers`, fsm=queued)
**Decisions:**
- ABSORB target: `phenotype-tooling/crates/phench-mcp/` (per registry
  batch4 row).
- Coordination with `AgilePlus` BLOCK-A spine (see AgilePlus boundary
  doc) — proposed spine role IMPLEMENTATIONS pending ratification.

**Next review:** on absorption completion
