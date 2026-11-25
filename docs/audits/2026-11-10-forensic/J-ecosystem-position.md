# J2 - Ecosystem Position of PhenoShared

Lane: J2. Date: 2026-11-10. Repo: `/Users/kooshapari/CodeProjects/Phenotype/repos/PhenoShared`
Evidence basis: `gh` API reads, `phenotype-registry` file reads, bounded `rg` over repo roots.
Everything not directly observed is marked **UNKNOWN**.

## 1. Registry standing

| Field | Value | Source |
|---|---|---|
| Registry id | `pheno` | `phenotype-registry/catalog/registry.yaml:635-640` |
| Registered repo | `KooshaPari/PhenoShared` | same |
| Status | `active` | same |
| Tier | `phenotype-framework` | same |
| Architecture | `layered` | same |

Registry-adjacent artifacts that also carry PhenoShared state:

- `phenotype-registry/ledger/stories/PhenoShared.story.md` (per-week commit story, W12-W17+)
- `phenotype-registry/ledger/rollups/PhenoShared.rollup.json` (1965 commits, 285 merges, 29 active weeks, peak week 2026-W42 = 429 commits)
- `phenotype-registry/registry/disposition-index.json` (also contains an unrelated absorbed-repo disposition record that mentions PhenoShared in prose; that record is about a different repo, not about PhenoShared's own disposition)
- `phenotype-registry/catalog/inventory/AUTHORITATIVE_REPO_INVENTORY.md`, `projects/pheno.json`, `ledger/README.md`, `tools/audits/build_completion_pdf.py`

So PhenoShared is a **first-class, actively tracked registry entry at framework tier**, with a maintained commit ledger, not a passive inventory row.

## 2. GitHub facts

| Fact | Value |
|---|---|
| Name | `PhenoShared` |
| Owner | `KooshaPari` |
| Visibility | PUBLIC |
| Created | 2026-04-03T08:14:12Z |
| Last push (observed) | 2026-11-10T04:34:33Z (same day as this audit) |
| Disk usage | 261,891 KB (~256 MB) |
| Primary language | Rust |
| Topics | `devtools`, `maintained`, `monorepo`, `platform` |
| Stars | 0 |
| Description (self-declared) | "Determining merge target: Rust monorepo workspace" |

Notes on the description: it reads as an in-flight decision memo ("Determining merge target") rather than a product statement. That is consistent with an absorption/consolidation role and is treated below as evidence, not as a defect claim.

Git authorship mix (rollup): `KooshaPari` 646, `Koosha Paridehpour` 274, `dependabot[bot]` 247, `jcode` 237, `Mergify` 195, `Forge` 166, `pheno Decomposition` 92, `Claude Code` 33. Roughly 60% of commits are agent or automation authored.

## 3. Consumers (in-tree evidence)

| Consumer candidate | Evidence | Verdict |
|---|---|---|
| Sibling Phenotype repos (`repos/*/Cargo.toml`) | `rg` over `repos/*/Cargo.toml` (depth 2, <=200K) for `PhenoShared\|KooshaPari/PhenoShared` matched **only** PhenoShared's own `Cargo.toml` | **No sibling repo declares PhenoShared as a Cargo dependency** (path or git) |
| Internal workspace crates | 372 directories under `crates/`, 239 `[workspace] members` entries | Internal crates consume each other in-workspace; this is intra-repo, not ecosystem consumption |
| External crates.io consumers | crates.io API returned HTTP 403 to the probe (UA-restricted), so presence/publishing is **UNKNOWN** | **UNKNOWN** |
| Non-Cargo consumers (npm/pypi/binaries) | Not probed in this lane | **UNKNOWN** |

Publish posture: 72 crate manifests set `publish = false` (bounded glob over `crates/*/Cargo.toml`), so a large fraction of the workspace is explicitly internal-only.

## 4. Outbound git dependencies

`rg 'git = '` over the root `Cargo.toml` returned **no matches**: the root manifest declares no git-sourced dependency. Whether individual member crates declare git deps was not exhaustively enumerated in this lane, so a per-crate outbound git-dependency census is **UNKNOWN**.

## 5. PR and release summary

| Metric | Value |
|---|---|
| Total PR sequence observed | up to **#828** (open at snapshot) |
| Recent 10 PRs | 4 MERGED, 3 OPEN, 3 CLOSED (incl. superseded duplicates of the same governance fix) |
| Recent PR theme | governance guard correctness, CI happy-path guard baseline, rustfmt of newly absorbed crates, coverage floor re-derivation, cargo workspace membership, hardcoded-home-path removal (28 scripts), lazy browser-lease acquisition |
| Releases | `promptscrape-v0.1.2` (2026-10-29, Latest), `promptscrape-v0.1.1`, `promptscrape-v0.1.0`, plus a draft `v0.1.1` dated 2026-04-03 |

Two structural observations:

1. **PRs are very high volume (828) while releases are essentially four, all of them `promptscrape`-scoped.** The monorepo as a whole has no release cadence; only one extracted component is released.
2. **The current PR stream is absorption hygiene**, not feature delivery: the most recent batch is about making CI/governance guards and newly absorbed crates (`perf-core`, `native`) correct. This matches the "merge target / consolidation" description and the `pheno Decomposition` author identity.

## 6. Org-chart layer served

Registry tier is `phenotype-framework`, which places PhenoShared in the shared framework/substrate layer beneath product repos.

Observed crate families substantiate that layer:

| Family | Representative crates |
|---|---|
| Substrate / platform | `substrate`, `substrate-core`, `substrate-tui`, `substrate-browser`, `substrate-browser-cdp`, `substrate-browser-broker`, `substrate-browser-mcp` |
| AgilePlus | `agileplus-*` (api, cli, domain, events, git, github, graph, grpc, nats, p2p, plane, sqlite, sync, telemetry, triage, ...) |
| Fabric | `fabric-capture`, `fabric-orchestrator`, `fabric-persist`, `fabric-terminal`, `fabric-tui`, `fabric-web`, `fabric-workspace` |
| Eyewear/eye-tracking | `eyetracker-*` |
| Dispatch / routing | `dispatch-bridge`, `driver-cli`, `driver-http`, `driver-mcp`, `omniroute-adapter`, `bifrost-routing` |
| Contracts / config | `engine-spec`, `acceptance-contract`, `phenotype-config-core`, `arch-test`, `audit-privacy` |

That is the cross-product framework substrate of the ecosystem: browser broker, dispatch drivers, AgilePlus domain, fabric orchestration, routing, and shared config/contracts. It is not a single-purpose leaf.

## 7. Boundary verdict

**Verdict: consolidation hub / shared kernel - NOT a leaf library.**

Evidence for "consolidation hub":

- Self-declared description: "Determining merge target: Rust monorepo workspace".
- The current PR stream is absorption hygiene (adding `native`/`perf-core` crates to the workspace, rustfmt-ing newly absorbed crates, removing one machine's absolute home path from 28 scripts, re-deriving coverage floors).
- `crates/ABSORPTION_MANIFEST.md` exists alongside 372 crate directories.
- A commit author identity literally named `pheno Decomposition` (92 commits).
- 1965 commits / 285 merges / 29 active weeks with a 429-commit peak week: sustained consolidation throughput, not steady-state library maintenance.

Evidence for "shared kernel":

- Registry tier `phenotype-framework`, architecture `layered`.
- 239 workspace members spanning substrate, browser automation, dispatch, routing, AgilePlus, fabric, and eye-tracking: cross-cutting platform capability rather than one product.

Evidence **against** "leaf library":

- No sibling Phenotype repo declares PhenoShared as a Cargo dependency (bounded `rg` over all `repos/*/Cargo.toml`).
- 72 crates explicitly set `publish = false`; only `promptscrape` has releases.
- 0 stars and a decision-memo description: no observable external library-consumer surface.

Evidence **against** a pure "consolidation hub with no downstream":

- Zero external Cargo consumers also means the consolidation has not yet been *redeemed* by downstream adoption at the Cargo-dependency level. Whether adopted via binary/PATH install, MCP server registration, or service deployment is **UNKNOWN** in this lane.

### UNKNOWNs to carry forward

1. crates.io publish state of any PhenoShared crate (API probe returned 403; UA-restricted).
2. Non-Cargo consumption (installed binaries, `~/bin` shims, MCP server registration, deployed services).
3. Per-member-crate outbound git dependencies (only the root manifest was confirmed git-dep free).
4. Whether the described "merge target" decision has been recorded as resolved anywhere authoritative.
5. Actual downstream runtime adoption by product repos (Tracera, AgilePlus-as-product, ShareCLI, Khostty, Orca, KiroCrew, OmniRoute, Discord).

## Evidence commands (reproducible)

```bash
gh repo view KooshaPari/PhenoShared --json name,description,visibility,createdAt,pushedAt,diskUsage,primaryLanguage,repositoryTopics,stargazerCount
gh pr list --repo KooshaPari/PhenoShared --state all --limit 10 --json number,title,state,createdAt
gh release list --repo KooshaPari/PhenoShared --limit 8
rg -n -A4 -B2 'PhenoShared' ~/CodeProjects/Phenotype/repos/phenotype-registry/catalog/registry.yaml
rg -l --max-depth 2 --max-filesize 200K 'PhenoShared|KooshaPari/PhenoShared' ~/CodeProjects/Phenotype/repos/*/Cargo.toml
rg -l --max-depth 3 '^publish\s*=\s*false' --glob 'crates/*/Cargo.toml' ~/CodeProjects/Phenotype/repos/PhenoShared
ls ~/CodeProjects/Phenotype/repos/PhenoShared/crates | wc -l
```
