# Slated for extraction

This crate (`phenotype-mcp-server`) provides MCP/FastMCP server logic and has no
observability concern. It has been removed from the PhenoObservability workspace
members per **NFR-OBS-010** (hexagonal architecture — no domain squatting).

**Action required (user decision):** move this directory to its own
Phenotype-org repo (e.g. `phenotype-mcp` / `PhenoMCP`) and publish independently.
The current `phenotype-observably-macros` dependency should become a proper
published crate dependency rather than a workspace path-dep.

Upstream reference: <REDACTED>/PhenoObservability — refactor/remove-domain-squatters
