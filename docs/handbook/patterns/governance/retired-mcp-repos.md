# Retired MCP repos — where to route new work

**Status:** convention · **ADR:** [ADR-017](https://github.com/KooshaPari/PhenoSpecs/blob/main/adrs/017-mcp-polyrepo-boundaries.md), [ADR-019](https://github.com/KooshaPari/PhenoSpecs/blob/main/adrs/019-mcp-runtime-dependency-graph.md)

When an agent or contributor hits an archived MCP repo, use this routing table instead of reviving the old layout.

| Retired | Replacement |
|---------|-------------|
| PhenoMCP | [PhenoMCPServers](https://github.com/KooshaPari/PhenoMCPServers) implementations + [PhenoFastMCP](https://github.com/KooshaPari/PhenoFastMCP)* frameworks |
| McpKit | PhenoFastMCP-py + catalog SSOT |
| cheap-llm / dispatch standalone MCP repos | [substrate](https://github.com/KooshaPari/substrate) runtime (`driver-argv`, `driver-http`) |
| phenotype-go-sdk / phenotype-rust-sdk MCP buckets | Domain edges per [language-bucket-sdk anti-pattern](../../anti-patterns/language-bucket-sdk.md) |
| dagctl | [phenodag](https://github.com/KooshaPari/phenodag) fleet presets |

Full table + AgentMCP absorb notes: [PhenoMCPServers `docs/retire/RETIRED-MCP-REPOS.md`](https://github.com/KooshaPari/PhenoMCPServers/blob/main/docs/retire/RETIRED-MCP-REPOS.md).

## Handbook cross-links

- [MCP fork selection](mcp-fork-selection.md)
- [mirror-to-empty-repo anti-pattern](../../anti-patterns/mirror-to-empty-repo.md)
- [language-bucket-sdk anti-pattern](../../anti-patterns/language-bucket-sdk.md)
