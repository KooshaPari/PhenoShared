# Anti-pattern: mirror-push to empty GitHub repo

**Status:** retired · **Applies to:** bootstrapping any Phenotype MCP framework fork under `KooshaPari/`.

## Problem

Creating an empty GitHub repository and running `git push --mirror` (or equivalent mirror-to-empty bootstrap) produces a repo with **`fork: false`**. GitHub does not record an upstream parent, so:

- The fork relationship UI and sync workflows break.
- `catalog/registry.yaml` `fork_parent` claims cannot be verified with `gh api`.
- Re-parenting requires delete + re-fork + catalog update — expensive and error-prone.

This was a root cause in agent session `40d15363` (PhenoFastMCP-rust initially forked from rmcp via mirror-to-empty, then re-parented to `fastmcp_rust`). See [ADR-018 Appendix A](https://github.com/KooshaPari/PhenoSpecs/blob/main/adrs/018-agent-session-zero-loop-ssot.md).

## Why it's wrong

- **Violates ADR-017 bootstrap rule** — framework forks must preserve upstream lineage for parallel sync lanes.
- **Breaks ADR-018 KPI** — fork parent must match catalog 100%; mirror-to-empty makes that impossible until surgery.
- **Banned in fleet validation** — PhenoMCPServers `validate_stale_patterns.py` fails on mirror-to-empty references in catalog and docs.

## What to do instead

**Always** create phenotype forks with GitHub's fork API:

```bash
gh repo fork <upstream>/<repo> --fork-name <PhenoName>
```

Verify immediately:

```bash
gh api repos/KooshaPari/<PhenoName> --jq '{fork, parent: .parent.full_name}'
```

Expected: `fork: true` and `parent` matching `catalog/registry.yaml` `fork_parent`.

Full procedure: [`github-fork-policy` skill](https://github.com/KooshaPari/PhenoMCPServers/blob/main/skills/github-fork-policy/SKILL.md) in PhenoMCPServers.

### Re-parent (rare, documented exception only)

1. Document in ADR + target repo `FORK-NOTES.md`
2. `gh repo delete KooshaPari/<Repo> --yes`
3. `gh repo fork <new-upstream> --fork-name <Repo>`
4. Update PhenoMCPServers catalog `fork_parent`
5. Enable issues if needed: `gh api -X PATCH repos/KooshaPari/<Repo> -f has_issues=true`

Never skip step 4 — agents read the catalog before the next session.

## Do / Don't

- **DO** run [`github-fork-policy`](https://github.com/KooshaPari/PhenoMCPServers/blob/main/skills/github-fork-policy/SKILL.md) before any new framework fork.
- **DO** cross-check fork parent against [mcp-fork-selection](../patterns/governance/mcp-fork-selection.md) (framework vs spec vs runtime).
- **DON'T** use `git push --mirror` into a freshly created empty repo as a "fork bootstrap."
- **DON'T** re-parent by deleting without updating catalog + ADR-017 consequences.

## Related

- [ADR-018: Agent Session Zero-Loop SSOT](https://github.com/KooshaPari/PhenoSpecs/blob/main/adrs/018-agent-session-zero-loop-ssot.md) — fork policy skill mapping
- [ADR-017: MCP Polyrepo Boundaries](https://github.com/KooshaPari/PhenoSpecs/blob/main/adrs/017-mcp-polyrepo-boundaries.md) — framework fork parents
- [`github-fork-policy` skill](https://github.com/KooshaPari/PhenoMCPServers/blob/main/skills/github-fork-policy/SKILL.md)
- [`mcp-boundary-guard` skill](https://github.com/KooshaPari/PhenoMCPServers/blob/main/skills/mcp-boundary-guard/SKILL.md)
- [mcp-fork-selection pattern](../patterns/governance/mcp-fork-selection.md)
