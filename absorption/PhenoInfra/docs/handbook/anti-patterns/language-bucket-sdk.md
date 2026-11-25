# Anti-pattern: language-bucket SDK repos

**Status:** retired · **Applies to:** any new or revived `phenotype-{rust,go,python,ts}-sdk` umbrella repo.

## Problem

A repo whose primary boundary is **language** rather than **domain role** becomes a catch-all for unrelated crates, transports, and MCP framework code. Agents cannot tell where new code belongs, duplicate forks appear, and tier rules collapse (e.g. Go treated as tier-0 core because "we already have a Go SDK repo").

Retired examples (2026-06-17, PhenoMCPServers issue #7):

| Anti-pattern repo | Why it failed | Replacement (domain roles) |
|-------------------|---------------|----------------------------|
| `phenotype-rust-sdk` | Generic Rust bucket hid MCP framework vs runtime vs utils | PhenoFastMCP-rust, PhenoRMCP, substrate, phenoUtils |
| `phenotype-go-sdk` | Generic Go bucket consolidated PlatformKit, DevHex, McpKit | PhenoFastMCP-go, MCPForge, phenotype-ops-mcp |

Catalog SSOT: [`retired_anti_patterns`](https://github.com/KooshaPari/PhenoMCPServers/blob/main/catalog/registry.yaml) in PhenoMCPServers.

## Why it's wrong

- **Violates ADR-017** — MCP code must live in framework, implementations, or runtime layers, not a language umbrella.
- **Breaks parallel lanes** — tier-0 Rust/Zig/Mojo forks must stay separate per upstream parent, not merged into one bucket.
- **Hides fork selection** — conflating rmcp (spec SDK) with fastmcp_rust (framework) was a root cause in session `40d15363`; see [ADR-018 Appendix A](https://github.com/KooshaPari/PhenoSpecs/blob/main/adrs/018-agent-session-zero-loop-ssot.md).
- **CI guardrails fail** — `validate_stale_patterns.py` and `validate_fork_parents.py` in PhenoMCPServers reject revived bucket references.

## What to do instead

Use **domain roles** from [LANGUAGE-TIERS-AND-ROLES](https://github.com/KooshaPari/PhenoMCPServers/blob/main/docs/LANGUAGE-TIERS-AND-ROLES.md):

| Role | Owner repo(s) | Tier |
|------|---------------|------|
| MCP framework | PhenoFastMCP (py), PhenoFastMCP-go, PhenoFastMCP-rust | 0–2 per lang |
| MCP spec SDK | PhenoRMCP | 0 |
| MCP implementations | PhenoMCPServers | 2 |
| Fleet runtime | substrate | 0 |
| Rust utilities / ports | phenoUtils, phenoShared | 0 |
| Python dep extras | phenotype-python-sdk `[connect]` groups only | 2 |

Before placing code, run the [mcp-fork-selection decision tree](../patterns/governance/mcp-fork-selection.md) and the [`mcp-boundary-guard`](https://github.com/KooshaPari/PhenoMCPServers/blob/main/skills/mcp-boundary-guard/SKILL.md) skill pre-flight.

## Do / Don't

- **DO** create a new **domain fork** under `framework:` in `catalog/registry.yaml` when adding a tier-0 lane (e.g. Zig/Mojo parallel to Rust).
- **DO** use `phenotype-python-sdk` only as optional dependency extras — not protocol core.
- **DON'T** reintroduce `phenotype-rust-sdk` or `phenotype-go-sdk` as MCP framework homes.
- **DON'T** add MCP servers, skills, or runtime drivers into a language bucket repo.

## Related

- [ADR-017: MCP Polyrepo Boundaries](https://github.com/KooshaPari/PhenoSpecs/blob/main/adrs/017-mcp-polyrepo-boundaries.md) — normative anti-pattern list
- [ADR-018](https://github.com/KooshaPari/PhenoSpecs/blob/main/adrs/018-agent-session-zero-loop-ssot.md) — tier confusion loop catalog
- [mcp-fork-selection pattern](../patterns/governance/mcp-fork-selection.md) — framework vs spec vs runtime tree
- [`mcp-boundary-guard` skill](https://github.com/KooshaPari/PhenoMCPServers/blob/main/skills/mcp-boundary-guard/SKILL.md)
- [`language-tier-picker` skill](https://github.com/KooshaPari/PhenoMCPServers/tree/main/skills)
