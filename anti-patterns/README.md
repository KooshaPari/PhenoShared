# Phenotype Anti-Patterns

What **not** to do — and the SSOT that prevents repeat mistakes. Pair each entry with the matching pattern in [`patterns/`](../patterns/README.md).

## Index

| Anti-pattern | Summary | Authority |
|--------------|---------|-----------|
| [language-bucket-sdk](language-bucket-sdk.md) | Don't create `phenotype-{rust,go}-sdk` umbrella repos for MCP. | [ADR-017](https://github.com/KooshaPari/PhenoSpecs/blob/main/adrs/017-mcp-polyrepo-boundaries.md) |
| [mirror-to-empty-repo](mirror-to-empty-repo.md) | Don't mirror-push into empty repos; use `gh repo fork`. | [ADR-018](https://github.com/KooshaPari/PhenoSpecs/blob/main/adrs/018-agent-session-zero-loop-ssot.md) + [`github-fork-policy`](https://github.com/KooshaPari/PhenoMCPServers/blob/main/skills/github-fork-policy/SKILL.md) |

MCP fleet work: read [mcp-fork-selection](../patterns/governance/mcp-fork-selection.md) before the first edit.
