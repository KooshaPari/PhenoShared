# MCP fork selection: framework vs spec vs runtime

**Status:** adopted · **Applies to:** any MCP polyrepo fork, rename, or code placement decision.

## Pre-flight (required)

Before the first edit in an MCP session, read in order:

1. [ADR-017: MCP Polyrepo Boundaries](https://github.com/KooshaPari/PhenoSpecs/blob/main/adrs/017-mcp-polyrepo-boundaries.md)
2. [PhenoMCPServers `catalog/registry.yaml`](https://github.com/KooshaPari/PhenoMCPServers/blob/main/catalog/registry.yaml)
3. Target repo `PHENO.md` + `FORK-NOTES.md`
4. [ADR-018: Agent Session Zero-Loop SSOT](https://github.com/KooshaPari/PhenoSpecs/blob/main/adrs/018-agent-session-zero-loop-ssot.md) — skills and dogfood ritual

Agent skills (PhenoMCPServers): [`mcp-boundary-guard`](https://github.com/KooshaPari/PhenoMCPServers/blob/main/skills/mcp-boundary-guard/SKILL.md), [`github-fork-policy`](https://github.com/KooshaPari/PhenoMCPServers/blob/main/skills/github-fork-policy/SKILL.md), [`language-tier-picker`](https://github.com/KooshaPari/PhenoMCPServers/tree/main/skills), [`substrate-vs-servers`](https://github.com/KooshaPari/PhenoMCPServers/tree/main/skills).

## Decision tree

```
What are you building or changing?
│
├─ Transport, macros, CLI, upstream sync, framework ergonomics?
│  └─ FRAMEWORK layer → PhenoFastMCP-{py,go,rust} (see fork table below)
│
├─ Official rmcp / streamable HTTP / OAuth / spec conformance tests?
│  └─ SPEC SDK layer → PhenoRMCP only (never under PhenoFastMCP-rust branding)
│
├─ Deployable MCP server, tool, skill, plugin, or fleet agent?
│  └─ IMPLEMENTATIONS layer → PhenoMCPServers/{servers,skills,plugins,agents}/
│
├─ Fleet dispatch, argv routing, cheap-llm CLI, driver-http?
│  └─ RUNTIME layer → substrate/ (not an MCP framework repo)
│
└─ Project scaffold / template only?
   └─ HexaKit/ (`hexakit init mcp-server` → PhenoMCPServers layout)
```

### Which Rust MCP fork?

| Need | Phenotype repo | Upstream parent | Layer |
|------|----------------|-----------------|-------|
| fastmcp ergonomics (macros, server builder) | [PhenoFastMCP-rust](https://github.com/KooshaPari/PhenoFastMCP-rust) | `Dicklesworthstone/fastmcp_rust` | Framework |
| Official rmcp / spec SDK | [PhenoRMCP](https://github.com/KooshaPari/PhenoRMCP) | `modelcontextprotocol/rust-sdk` | Spec |

**Never** fork `modelcontextprotocol/rust-sdk` into a repo named PhenoFastMCP-rust. Session `40d15363` required a full re-parent because of this confusion — see [ADR-018 Appendix A](https://github.com/KooshaPari/PhenoSpecs/blob/main/adrs/018-agent-session-zero-loop-ssot.md).

### Framework fork parents (normative)

| Phenotype repo | Upstream parent | Tier |
|----------------|-----------------|------|
| PhenoFastMCP | PrefectHQ/fastmcp | 2 |
| PhenoFastMCP-go | mark3labs/mcp-go | 1 |
| PhenoFastMCP-rust | Dicklesworthstone/fastmcp_rust | 0 |
| PhenoRMCP | modelcontextprotocol/rust-sdk | 0 |

Verify `fork: true` and parent after every fork — see [github-fork-policy skill](https://github.com/KooshaPari/PhenoMCPServers/blob/main/skills/github-fork-policy/SKILL.md) and [mirror-to-empty-repo anti-pattern](../../anti-patterns/mirror-to-empty-repo.md).

## Do / Don't

- **DO** use `gh repo fork <upstream>/<repo> --fork-name <PhenoName>` for every new framework fork.
- **DO** update `catalog/registry.yaml` `fork_parent` when re-parenting.
- **DO** place deployable servers in PhenoMCPServers, not inside framework fork repos.
- **DON'T** create language-bucket SDK repos — see [language-bucket-sdk anti-pattern](../../anti-patterns/language-bucket-sdk.md).
- **DON'T** mirror-push into an empty GitHub repo instead of forking.
- **DON'T** host protocol core in Python/TS when a tier-0 Rust/Zig lane exists — see [LANGUAGE-TIERS-AND-ROLES](https://github.com/KooshaPari/PhenoMCPServers/blob/main/docs/LANGUAGE-TIERS-AND-ROLES.md).

## Why

Three layers (framework / implementations / runtime) plus a separate spec SDK fork prevent agents from re-debating settled placement every session. Wrong fork parent breaks GitHub upstream sync UI and forces expensive re-parent surgery. ADR-017 is the decision authority; this page is the agent-readable decision tree.

## Related

- [ADR-017](https://github.com/KooshaPari/PhenoSpecs/blob/main/adrs/017-mcp-polyrepo-boundaries.md) — polyrepo boundaries
- [ADR-018](https://github.com/KooshaPari/PhenoSpecs/blob/main/adrs/018-agent-session-zero-loop-ssot.md) — zero-loop pre-flight and skills
- [PhenoMCPServers DOGFOOD](https://github.com/KooshaPari/PhenoMCPServers/blob/main/docs/DOGFOOD.md) — session ritual
- [language-bucket-sdk anti-pattern](../../anti-patterns/language-bucket-sdk.md)
- [mirror-to-empty-repo anti-pattern](../../anti-patterns/mirror-to-empty-repo.md)
