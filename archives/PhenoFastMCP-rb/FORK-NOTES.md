# Fork notes — PhenoFastMCP superset strategy

Last updated: 2026-06-17

## Mirror command (all branches, not just main)

GitHub **rejects** `refs/pull/*` on push. Use mirror clone for heads+tags only:

```bash
# 1. Mirror clone upstream (includes all heads, tags, and pull refs locally)
git clone --mirror https://github.com/PrefectHQ/fastmcp.git fastmcp.git
cd fastmcp.git

# 2. Point at phenotype fork and disable mirror push mode
git remote set-url origin https://github.com/KooshaPari/PhenoFastMCP.git
git config remote.origin.mirror false

# 3. Push all branches and tags (NOT pull refs)
git push origin 'refs/heads/*:refs/heads/*'
git push origin 'refs/tags/*:refs/tags/*'
```

Verified on fork day: **140 branches**, **105 tags** on `KooshaPari/PhenoFastMCP`.

Pull-request heads are preserved **locally** in the mirror bare repo at
`fastmcp.git` for cherry-pick / merge review. They cannot live on GitHub as refs.
Export list:

```bash
git for-each-ref --format='%(refname)' refs/pull/ | wc -l
```

## Upstream remote (working clone)

```bash
git remote add upstream https://github.com/PrefectHQ/fastmcp.git
git fetch upstream --tags
git fetch upstream '+refs/heads/*:refs/remotes/upstream/*'
```

## Superset merge policy

Goal: collect useful upstream branches into `phenotype/superset` so day-0
phenotype users inherit fixes/features without waiting for upstream releases.

### Priority branches (initial triage)

| Branch | Why |
|--------|-----|
| `main` | baseline |
| `2-14-deprecations` | migration path from v2 |
| `anthropic-sampling-handler` | provider sampling |
| `auto-docket-execution` | background task execution |
| `apps-quickstart-tutorial` | MCP Apps docs/samples |
| `add-jmespath-tools-contrib` | tool contrib patterns |
| `chat` | chat transport experiments |

### Merge workflow

```bash
git checkout -B phenotype/superset v3.4.2
# for each candidate branch:
git merge --no-ff upstream/<branch> -m "superset: merge upstream/<branch>"
# run tests; if green, keep; else document conflict in issue
```

Track every merge decision in GitHub issues labeled `superset-merge`.

## Related forks (framework tier-0, separate repos)

| Language | Upstream candidate | Phenotype repo | Status |
|----------|-------------------|----------------|--------|
| Python | PrefectHQ/fastmcp | **this repo** | mirrored |
| Go | mark3labs/mcp-go | PhenoFastMCP-go (planned) | not started |
| Rust | modelcontextprotocol/rust-sdk or rmcp | PhenoFastMCP-rust (planned) | not started |

Repeat mirror workflow for each tier-0 fork.

## Issues to file upstream (carry-over)

When phenotype patches fix bugs found during superset merges, open PRs against
`PrefectHQ/fastmcp` **and** keep phenotype commits on `feat/phenotype-*` until
upstream merges.

## Absorption from deprecated phenotype repos

| Source | Target | Notes |
|--------|--------|-------|
| McpKit framework crates | `rust/`, `go/` subtrees | drop vendored mcp-forge LSP copy |
| AgentMCP hex adapters | `python/pheno/` layer | use HexaKit templates for layout |
| PhenoMCP hand-rolled server | **delete** | use fastmcp APIs |
| phenotype-python-sdk mcp-kit | remove package | depend on PhenoFastMCP wheel |

Server **implementations** → [PhenoMCPServers](https://github.com/KooshaPari/PhenoMCPServers).
