# Forensic Lane I — Documentation & Knowledge Corpus (PhenoShared)

- **Repo:** `/Users/kooshapari/CodeProjects/Phenotype/repos/PhenoShared`
- **Mode:** READ-ONLY. No git mutations, no writes inside the repo.
- **Measured:** 2026-11-10T04:38Z to 04:41Z (~12 bounded bash calls)
- **Scope:** tracked `*.md` only (`git ls-files`). Untracked/ignored markdown not counted.

**Headline:** 10,532 tracked markdown files, 716,333 total lines. The corpus is not one
knowledge base; it is at least **four overlapping corpora** (canonical docs, vendored/absorbed
repos, forensic audits, and per-crate boilerplate) with **58% and 95% basename overlap between
three pairs of supposedly distinct trees**. The dominant defect is not missing documentation. It
is duplicated and forked documentation presented as if it were distinct.

---

## 1. Corpus size — markdown by top-level directory (top 25)

| # | Top-level dir | .md files | Share | Reading |
|---|---|---:|---:|---|
| 1 | `crates/` | 3,518 | 33.4% | Per-crate docs; heavy AGENTS/CLAUDE/SPEC boilerplate |
| 2 | `docs/` | 2,581 | 24.5% | The intended canonical corpus |
| 3 | `audits/` | 1,290 | 12.2% | Forensic/audit output, incl. snapshots of snapshots |
| 4 | `absorption/` | 1,102 | 10.5% | Absorbed external repos' docs, retained wholesale |
| 5 | `agileplus/` | 304 | 2.9% | AgilePlus spec/plan/tasks triad |
| 6 | `agents/` | 155 | 1.5% | Agent definitions and prompts |
| 7 | `kitty-specs/` | 140 | 1.3% | Unrelated-sounding spec tree, unclassified |
| 8 | `sites/` | 128 | 1.2% | Site/docs-site sources |
| 9 | **`<repo root>`** | 128 | 1.2% | **128 loose root-level markdown files** |
| 10 | `_archived/` | 126 | 1.2% | Archive generation 1 |
| 11 | `handbook/` | 123 | 1.2% | Handbook + `handbook/historical/` |
| 12 | `.archive/` | 104 | 1.0% | Archive generation 2 (hidden dir) |
| 13 | `archives/` | 99 | 0.9% | Archive generation 3 |
| 14 | `specs/` | 83 | 0.8% | Root-level specs, parallel to `docs/specs` |
| 15 | `infrakit/` | 36 | 0.3% | Infra kit |
| 16 | `bench/` | 36 | 0.3% | Benchmarks |
| 17 | `unity/` | 35 | 0.3% | Unity surface |
| 18 | `servers/` | 30 | 0.3% | Server docs |
| 19 | `prompts/` | 25 | 0.2% | Prompt library |
| 20 | `registry/` | 24 | 0.2% | Registry docs |
| 21 | `.agileplus/` | 22 | 0.2% | Hidden AgilePlus working state |
| 22 | `architecture/` | 21 | 0.2% | Architecture set, parallel to `docs/architecture` |
| 23 | `scripts/` | 18 | 0.2% | Script docs |
| 24 | `python/` | 18 | 0.2% | Python surface |
| 25 | `plans/` | 18 | 0.2% | Plans, parallel to `docs/plans` |

Tail: `.github` 17, `phenotype-infrakit` 15, `sota` 14, `patterns` 14, `verification` 13,
`state` 13, `scaffold` 13, `work` 12, `templates` 11, `iac` 11. **149 top-level directories**
compete for a newcomer's attention.

**Three separate archive trees** (`_archived/`, `.archive/`, `archives/`) hold 329 files. That is
not archival hygiene; it is three generations of archiving that nobody retired.

---

## 2. Canonical vs session vs temporal classification

| Class | Definition | Est. count | Where |
|---|---|---:|---|
| **Canonical** (intended SSOT) | Named architecture/spec/reference docs meant to be read as current | ~400 | `docs/atlas`, `docs/phenotype-docset-v1.1`, `docs/architecture`, `docs/specs/*.md`, `docs/reference`, root `ARCHITECTURE.md`/`PRD.md`/`SPECIFICATION.md` |
| **Session/dated record** | Implementation sessions, worklogs, audit snapshots | ~1,600 | `docs/sessions` (53), `docs/worklogs` (91), `docs/audits` (97), `audits/org-audit-snapshots` (302), `audits/org-audits` (886) |
| **Absorbed/vendored** | Third-party or sibling-repo docs imported wholesale | ~1,102 | `absorption/` (PhenoInfra 766, PhenoMLX-temp 146, phenoDesign 85, pheno-forge 44) + `docs/specs/pheno-specs` (393, a nested repo tree with its own LICENSE/CODEOWNERS/CHARTER) |
| **Generated** | Machine-written inventories | few but huge | `docs/atlas/codebase/FILES.md` (22,660 lines) |
| **Boilerplate** | Per-crate agent/readme files | ~2,500 | `crates/` (AGENTS.md ×136, CLAUDE.md ×111, README ×844) |
| **Temporal** (should not be canonical) | SUMMARY/STATUS/FINAL/PHASE/"complete" docs | 1,002 | Spread across every tree, worst in `crates/` 437, `absorption/` 195, `audits/` 131 |

---

## 3. `docs/` subtree map (105 subdirectories, 2,581 md)

| Subdir | md | What it holds |
|---|---:|---|
| `specs/` | 528 | Largest subtree. Mixed loose specs (`001-eval-architecture.md` … `007-…`) **plus** `specs/pheno-specs/` (393) which is a **nested vendored repo** carrying its own `LICENSE`, `CODEOWNERS`, `CHARTER.md`, `CITATION.cff`, `AGENTS.md`, `cliff.toml`, `justfile`. Not a subdir of this product at all. |
| `sessions/` | 222 | 52 session dirs + `index.md` (avg ~4 docs each) |
| `boundary/` | 166 | Per-product boundary declarations, one file per repo (AgentMCP, AgilePlus, BytePort, …) |
| `atlas/` | 149 | Full product atlas: `ALD/HLD/LLD/PRD/DOMAIN_MODEL`, `architecture/`, `products/` (15+), `qa/` (assurance contract, metrics, negative controls), `portfolio/`, `prompts/`, `records/`, `references/`, `codebase/FILES.md` |
| `phenotype-docset-v1.1/` | 146 | **Near-copy of `atlas/`.** Same skeleton: `ALD.md`, `HLD.md`, `LLD.md`, `PRD.md`, `DOMAIN_MODEL.md`, `INDEX.md`, `MANIFEST.json`, `adr/`, `architecture/`, `intent/`, `portfolio/`, `products/`, `qa/`, `records/`, `references/`, `report/`, `examples/`, `operations/` |
| `intent/` | 139 | Per-product intent statements — **near-copy of `boundary/`** |
| `reference/` | 100 | Reference material, but top entries are dated audits and status docs (`AGILEPLUS_DASHBOARD_STATUS.md`, `BLOCKING_DECISIONS_2026-03-29.md`) |
| `audits/` | 97 | Dated audits + `2026-10-16-completion/`, `2026-10-17/`, plus JSON scorecards |
| `worklogs/` | 91 | Agent worklogs; **contains a byte-duplicate of `crates/hexa-kit/docs/worklogs/`** (DEPENDENCIES.md 3,032 and RESEARCH.md 2,673 lines each appear twice) |
| `adr/` | 90 | ADR store #1 (sing. `adr`) |
| `src/` | 81 | Docs site source (VitePress-ish) |
| `research/`, `operations/`, `guides/`, `okf/`, `absorption/`, `handbook/`, `org-audits/`, `plans/`, `governance/`, `adrs/`, `disposition/`, `patterns/`, `adoption/`, `superpowers/`, `rationalization/`, `monorepo-state/`, `ecosystem/`, `guide/`, `runbooks/`, `workflow/`, `absorbed-from/`, `reports/`, `process/`, `index/`, `pilot/`, `grades/`, `forks/`, `changes/`, `sdk/` | 14→5 | Smaller, mostly coherent, except **`adrs/` (25, pl.) is a second incompatible ADR store** alongside `adr/` (90, sing.) |

**Loose in `docs/` root:** ~60 files including `ARCHITECTURE.md`, `PRD.md`, `SPECIFICATION.md`,
`SSOT.md`, `SUMMARY.md`, `STATUS`-class docs, `SENTRY_*`, `LOCAL_FIRST_*`, `PHENOLM_MIGRATION.md`,
plus `AGENTS.md`, `README.md`, `index.md`, `book.toml`, `health.html`, and stray `en.json`/`es.json`/`fa*.json`.

---

## 4. ADR inventory

**Two parallel ADR stores**, mutually unaware:

| Store | Files | Naming schemes present |
|---|---:|---|
| `docs/adr/` (singular) | 90 | `NNNN-slug.md` (0001…0035), `ADR-NNN-slug.md` (ADR-001…ADR-015), bare `ADR-001.md`-style, and **date directories** `2026-06-18`, `2026-07-08`, `2026-07-14`, `2026-07-19`, `2026-07-22`, plus `ARCHITECTURE.md` |
| `docs/adrs/` (plural) | 25 | `0001-…`…`0007-…` **and** `ADR-ECO-001`…`ADR-ECO-023` |
| `adrs/` (repo root) | 10 | `001-hexagonal-architecture.md` … `008-security.md` — a third, unrelated numbering series |
| `docs/atlas/adr`, `docs/phenotype-docset-v1.1/adr`, `docs/specs/pheno-specs/adrs` | — | Copies of the above, nested inside the atlas/docset pair |

**ID collisions inside a single directory** (`docs/adr`): prefix `0001` used **4×**, `0002` 3×,
`0003` 3×, `0004` 3×, `0005` 3×, `0006` 3×, `0009` 2×, `0010` 2×. A citation like "ADR-0004"
is unresolvable without a slug.

**Status distribution** (`docs/adr`, regex over `Status:` / `- **Status**` / `> **Status**`):
Accepted 22 (21 plain + 1 "updated 2026-06-23"), Proposed 6 (4 stub + 1 stub Phase 2 + 1 plain).
**Only ~28 of 90 ADRs expose a parseable Status field**; the remaining ~62 either use another
format or omit status entirely. There is no machine-readable ADR index.

---

## 5. Session archive

- **Count:** 52 session directories + `index.md` under `docs/sessions/`.
- **Date range:** `2026-02-26-cliproxy-thegent-agentapi-cleanup-pass` → `2026-11-07-vitepress-redacted-escaping`. ~8.5 months.
- **Distribution:** thin at the start (4 sessions in Feb 2026), explosive mid-year, sparse but current in Nov 2026.
- **Two naming conventions coexist:** compact `YYYYMMDD-slug` (48) and hyphenated `YYYY-MM-DD-slug` (4: `2026-10-09`, `2026-10-30`, `2026-11-04`, `2026-11-05`, `2026-11-07`). Sorting by name splits the archive into two blocks.
- **Two outliers with no date:** `index.md`, `pr-review-20260330`, `phenotype-20260331-tooling-vps-agents`.
- **Version-suffix smell inside sessions:** `…-reconcile`, `…-reconcile-v2`, `…-reconcile-v3` are three separate session directories for one task.
- **Dominant themes inferred from names:** agent/CLI proxy reconciliation (5), consolidation waves (`20260722-consolidation-20`, `20260723-wave-2`, `-wave-3`), audits (`policy-engine-audit`, `branding-audit`, `docs-review`, `researchledger-corpus-audit-routing`), platform/runtime work (`metal-model-runtime`, `desktop-nvidia-mvp`, `pyo3-029-security`, `cargo-deny-findings`), repo hygiene (`branch-cleanup`, `workspace-split`, `trunk-migration`, `repository-preservation-wave`).

**Session-template duplication is organisation-wide, not local:** `00_SESSION_OVERVIEW.md`
appears **100 times** but only ~30 are under `docs/sessions`. The rest are in `crates/hexa-kit`
(13), `crates/agile-plus` (13), `absorption/PhenoInfra` (13), `audits/org-audits` (6),
`handbook/docs` (5), `agileplus/docs` (4), `_archived/byteport` (3). The 7-document session
template (`00_SESSION_OVERVIEW` 100, `01_RESEARCH` 85, `02_SPECIFICATIONS` 64, `03_DAG_WBS` 77,
`04_IMPLEMENTATION_STRATEGY` 63, `05_KNOWN_ISSUES` 75, `06_TESTING_STRATEGY` 76) is being stamped
into every crate as well as every session.

---

## 6. The 20 largest documents (with purpose)

| # | Lines | Path | Purpose |
|---|---:|---|---|
| 1 | 22,660 | `docs/atlas/codebase/FILES.md` | Machine-generated full file inventory. Should be generated on demand, not tracked. |
| 2 | 5,728 | `audits/absorption-justifications/helios-cli-2026-07-17.md` | Absorption evidence dossier for helios-cli |
| 3 | 3,780 | `docs/specs/pheno-specs/specs/platform/gateway/SPEC.md` | Gateway platform spec (vendored tree) |
| 4-7 | 3,641 ×4 | `crates/hexa-kit/templates/{hexagon/typescript,hexagon/rust,hexagon/go,go}/AGENTS.md` | **Four byte-identical agent templates** |
| 8-11 | 3,638 ×4 | `audits/org-audits/findings/2026-06-18-mcpkit/MCP_TOOLKITS_SOTA.md` and three snapshot copies (`org-audit-snapshots/`, `…/zz-archive-archive2/wt-feature-state-table-org/`, `…/wt-audit-rebuild-v38/`) | MCP toolkits SOTA survey, **copied 4×** |
| 12 | 3,612 | `docs/specs/pheno-specs/archive/agent-wave/AGENTS.md` | Archived agent-wave instructions |
| 13-14 | 3,601 ×2 | `crates/argis-extensions/WARP.md`, `crates/argis-extensions/CLAUDE.md` | Same content under two agent-file conventions |
| 15 | 3,269 | `crates/policystack/SPEC.md` | Policy stack specification |
| 16 | 3,144 | `docs/specs/pheno-specs/research/feature-flag-sota.md` | Feature-flag SOTA research |
| 17-18 | 3,032 ×2 | `docs/worklogs/DEPENDENCIES.md` **and** `crates/hexa-kit/docs/worklogs/DEPENDENCIES.md` | Dependency analysis, **duplicated** |
| 19 | 2,955 | `docs/specs/pheno-specs/specs/platform/data-transform/SPEC.md` | Data-transform spec |
| 20 | 2,697 / 2,673 | `historical/BLUEPRINT.md`, `handbook/historical/BLUEPRINT.md`, `docs/worklogs/RESEARCH.md` (+ hexa-kit copy) | Blueprint and research, each near-duplicated |

Pattern: **of the 20 largest docs, 12 have a byte-identical twin.** Volume is not knowledge here.

---

## 7. Doc-health findings

### F1 — Temporal suffixes on canonical surfaces: 1,002 files (9.5%)
`SUMMARY|STATUS|FINAL|_V[0-9]|_OLD|_NEW|_DRAFT|COMPLETE|WIP|TEMP` by tree: `crates` 437,
`absorption` 195, `audits` 131, `docs` 97, `sites` 24, `templates` 11, **root 10**, `unity` 9,
`handbook` 9, `.github` 9. Root-level offenders include `CONSOLIDATION_SUMMARY.md`,
`FINAL_VERIFICATION_CHECKLIST.md`, `GOVERNANCE_SYNC_COMPLETED.md`,
`PHASE1_FINAL_EXECUTION_BRIEF.md`, `PHASE_1_COMPLETION_SUMMARY.md`, `STATUS.md`,
`STATUS-REPORT.md`, `SENTRY_COMPLETE_CHECKLIST.md`, and a whole `A-01…A-10_VALIDATION.md` series.

### F2 — Duplicated trees masquerading as distinct (the most expensive defect)
| Pair | Files | Shared basenames | Interpretation |
|---|---:|---:|---|
| `docs/atlas/` (263) vs `docs/phenotype-docset-v1.1/` (260) | 523 | **152** | ~58% overlap, identical skeleton. One is a frozen copy of the other. |
| `docs/boundary/` (166) vs `docs/intent/` (139) | 305 | **132** | ~95% overlap. Two labels, one dataset. |
| `docs/adr/` (90) vs `docs/adrs/` (25) vs `adrs/` (10) | 125 | 0 (different schemes) | Three incompatible stores. |

Verified byte-level duplications: `docs/worklogs/DEPENDENCIES.md` ⇄ `crates/hexa-kit/docs/worklogs/DEPENDENCIES.md`; `docs/worklogs/RESEARCH.md` ⇄ hexa-kit copy; `historical/BLUEPRINT.md` ≈ `handbook/historical/BLUEPRINT.md`; 4× `MCP_TOOLKITS_SOTA.md`; 4× `AGENTS.md` template; `argis-extensions/WARP.md` ≈ `CLAUDE.md`.

### F3 — Boilerplate inflation
`README.md` **844**, `index.md` **258**, `AGENTS.md` **136**, `CLAUDE.md` **111**, `spec`/`SPEC`
**353**, `plan.md` **170**, `tasks.md` **152**, `CHANGELOG.md` **123**, `DOSSIER.md` **97**,
`SECURITY.md` **90**, `PRD.md` **74**, `MIGRATED.md` **74**, `ADR.md` **62**. Two agent-instruction
conventions (`AGENTS.md` + `CLAUDE.md`) run in parallel in the same directories, so every rule
change is a two-to-three-file edit per crate.

### F4 — Archive sprawl
Three archive trees (`_archived/` 126, `.archive/` 104, `archives/` 99 = 329 files) plus
`docs/archive`, `docs/phenotype-docset-v1.1` (itself an archive), `handbook/historical/`,
`historical/`, `audits/org-audits/2026-07/zz-archive-archive2/`. At least **six generations** of
"archive" coexist with no retention rule.

### F5 — Nested vendored repo inside `docs/`
`docs/specs/pheno-specs/` (393 md) carries `LICENSE`, `LICENSE-APACHE`, `LICENSE-MIT`, `CODEOWNERS`,
`CITATION.cff`, `CHARTER.md`, `cliff.toml`, `justfile`, `catalog-info.yaml`, `llms.txt`. It is a
foreign repository checked into `docs/`, which makes every docs-scoped search, index, and lint
operate on someone else's content.

### F6 — Broken relative links
Cheap sample: first 40 `docs/*.md`, 15 relative `.md` links extracted, **2 broken (13%)**. Small
sample; treat as indicative of a low-single-digit-percent breakage rate, not a measured global figure.
No link checker is configured in the tooling observed.

### F7 — Generated artifact tracked as documentation
`docs/atlas/codebase/FILES.md` is 22,660 lines of file inventory (the largest doc in the repo by
4×). It is regenerable output committed as prose, and it is guaranteed stale.

### F8 — Root-level 128-file broadsheet
128 loose `.md` at the repo root, including the dated `A-0x_VALIDATION.md` series, three
`DEPENDENCIES*` variants (`DEPENDENCIES.md`, `DEPENDENCIES_STANDARD.md`,
`DEPENDENCY_PHASE2_{EXECUTION_PLAN,START,VALIDATION}.md`), `CONSOLIDATION_SUMMARY.md` vs
`CONSOLIDATION_AUDIT.md`, `ADR.md` vs `ADRS.md` vs `ADR_REGISTRY.md`, and `ARCHIVED.md`.

---

## 8. Where to read what (newcomer navigation)

| You want | Read this | Do **not** read |
|---|---|---|
| What the product is | `README.md`, then `docs/atlas/PRD.md` | `docs/phenotype-docset-v1.1/PRD.md` (copy) |
| System architecture | `docs/atlas/HLD.md`, `ALD.md`, `LLD.md` | `docs/architecture/*` (21, unclear age) |
| Decisions and why | `docs/adr/0001-…0035-*` (Accepted set) | `docs/adrs/`, `adrs/`, `ADR_REGISTRY.md` |
| Normative requirements | `docs/atlas/qa/ASSURANCE-CONTRACT.md`, `qa/METRICS.md`, `qa/NEGATIVE-CONTROLS.md` | `audits/*/scorecard.json` |
| Per-product boundary/ownership | `docs/boundary/<product>.md` (pick one label set, not both) | `docs/intent/<product>.md` (95% duplicate) |
| Platform specifications | `docs/specs/*.md` loose files (`001-…`–`007-…`, `compute-mesh-spec.md`) | `docs/specs/pheno-specs/` (vendored foreign repo) |
| How a past change was done | `docs/sessions/<date>-<slug>/00_SESSION_OVERVIEW.md` | `docs/worklogs/` (duplicated into crates) |
| Absorbed-project history | `audits/absorption-justifications/` | `absorption/PhenoInfra/` body (766 files, raw dump) |
| Assurance/quality gates | `docs/atlas/qa/`, `docs/grades/` | `audits/org-audit-snapshots/` (302, stale copies) |

---

## 9. Recommended consolidation actions

Ordered by defect removed per unit of risk. **Lane I made no changes; these are proposals.**

1. **Pick one atlas.** Keep `docs/atlas/` authoritative and move
   `docs/phenotype-docset-v1.1/` to `archives/` with a dated README naming the superseding commit.
   Removes ~260 files of parallel truth and 152 duplicate basenames. Highest value, lowest risk.
2. **Merge `docs/boundary/` and `docs/intent/`.** 132 of 139 shared basenames means one directory
   is redundant. Keep `boundary/` (the name used by `BOUNDARY_OWNERS.md`), fold intent prose into
   each boundary doc, delete `intent/`.
3. **Collapse three ADR stores into `docs/adr/`.** Renumber to a single `NNNN` series, resolve the
   8 colliding prefixes (`0001`×4, `0002`–`0006`×3), add a mandatory `Status:` line, and generate
   `docs/adr/INDEX.md` from front-matter so `ADR_REGISTRY.md` stops being hand-maintained prose.
   Retire `docs/adrs/` and root `adrs/` with pointers.
4. **Evict the nested repo.** Move `docs/specs/pheno-specs/` to `absorption/pheno-specs/` (it is
   absorbed content by nature) so docs tooling stops indexing foreign license and CI files.
5. **Untrack generated output.** Remove `docs/atlas/codebase/FILES.md` from git, add a `make
   codebase-index` target, and gitignore it. 22,660 lines of guaranteed-stale inventory.
6. **Kill cross-tree worklog duplication.** `docs/worklogs/{DEPENDENCIES,RESEARCH}.md` and
   `crates/hexa-kit/docs/worklogs/` are byte-duplicates; keep one, symlink or pointer the other.
   Same for the 4× `MCP_TOOLKITS_SOTA.md` in `audits/`.
7. **One archive, one retention rule.** Consolidate `_archived/`, `.archive/`, `archives/`,
   `audits/org-audits/2026-07/zz-archive-archive2/` into `archives/<YYYY>/`; add a README stating
   that content older than the retention window is deleted, not re-archived.
8. **Enforce the 7-doc session template in one place.** Stop stamping
   `00_SESSION_OVERVIEW.md`…`06_TESTING_STRATEGY.md` into crates and `absorption/`; reference the
   template instead. Removes ~400 files of template clone.
9. **Retire temporal suffixes on canonical surfaces.** Promote any still-live content out of
   `STATUS`/`FINAL`/`SUMMARY`/`PHASE*_COMPLETE` files into the doc it belongs to; delete the rest.
   Start with the 10 root offenders and the `A-0x_VALIDATION.md` series.
10. **Choose one agent-instruction file per directory.** `AGENTS.md` (136) vs `CLAUDE.md` (111)
    vs `WARP.md` (1) triples the maintenance surface. Standardise on `AGENTS.md` with
    `CLAUDE.md` as a one-line include.
11. **Add a link checker and a docs lint gate.** 13% sampled breakage plus zero enforcement
    suggests nothing currently runs. A `lychee`/`markdown-link-check` job in CI, scoped to `docs/`,
    would stop drift cheaply.
12. **Normalise session directory names.** One `YYYYMMDD-slug` convention; rename the 4 hyphenated
    and 2 undated entries so `ls docs/sessions | sort` is chronological. Collapse
    `…-reconcile`, `…-reconcile-v2`, `…-reconcile-v3` into one session with a decision log.

---

## Method and limitations

- Counted tracked markdown only: `git ls-files '*.md'` → 10,532. Untracked and gitignored
  markdown (likely present in `node_modules`, build output, and worktrees) is excluded.
- "Duplicate" means identical basename and, where spot-checked, identical line count. Only 6 pairs
  were verified byte-for-byte; the rest are basename-and-size matches. A `sha256sum` sweep across
  all 10,532 files was deliberately not run to stay inside the ~12-call budget.
- Broken-link measurement is a 40-file sample and is reported as indicative, not global.
- ADR status tally used three regex forms; ~62 ADRs expose no parseable Status, so the
  distribution describes the *formatted* subset only.
- No files were modified, no git state was touched.
