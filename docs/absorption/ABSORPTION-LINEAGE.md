# Absorption lineage — PhenoShared

**Measured at** HEAD `925ab5ce`, 693 commits, 2026-09-18.

**Repo identity (this matters for reading every other ledger).** `git remote -v`
says `https://github.com/KooshaPari/PhenoShared.git`. `README.md:9-11` states the
canonical GitHub name is `KooshaPari/PhenoShared` and that `KooshaPari/pheno`
redirects to it. Ledgers in this repo write the destination as `pheno`
(e.g. `crates/ABSORPTION_MANIFEST.md:15`, `docs/absorption/phench/README.md:8`),
as `phenotype-tooling` (e.g. `crates/tokn/PROVENANCE.md:6`), or as
`pheno (monorepo)`. `catalog-info.yaml` claims `name: phenohandbook` /
`github.com/project-slug: <REDACTED>/PhenoHandbook` and `package.json` claims
`"name": "phenodocs"`. **Three of those four identities are stale metadata, not
separate repos** — but the ambiguity is not cosmetic: it is why 8 of the lineage
entries below have a destination that cannot be confirmed from the ledger alone.

**Method.** Every git fact is `git log --diff-filter=A -- <path>` /
`git show --name-status`, cited by commit hash. Every doc claim is cited
`file:line`. Where a doc and git disagree, git wins and the disagreement is
printed in the `status` column. Doc-only claims are labelled `PROSE-ONLY`.

---

## 1. Lineage table

### 1a. Single-hop absorptions with a verifiable import commit

| # | Source repo | Hop chain | Destination path(s) | Evidence (commit + ledger) | Status |
|---|---|---|---|---|---|
| 1 | `KooshaPari/zz-merge-unk-eyetracker` | direct | `crates/eyetracker/eyetracker-{domain,math,core,camera,inference,cli,ffi}` (7 crates) | `2fe6b59a` (2026-08-13, 40 files; 37 under `crates/eyetracker/`); `crates/eyetracker-PROVENANCE.md:5-19` | VERIFIED. Message says 7 crates; tree has 7. **Duplicate twins exist**: flat `crates/eyetracker-{camera,cli,core,domain,ffi,inference,math}` were added by `33673213`, not by this commit |
| 2 | `pheno-substrate-family` | direct | `crates/pheno-cdylib-bridge`, `crates/pheno-forge-smoke`, `crates/pheno-runtime-config`, `crates/pheno-context` | `c3f47016` (2026-08-14, 52 files); `docs/absorption/{pheno-cdylib-bridge,pheno-forge-smoke,pheno-runtime-config,pheno-context}/README.md` | VERIFIED. Message says 4 crates; tree has exactly 4 |
| 3 | `KooshaPari/Configra` | direct | `crates/settly`, `crates/pheno-config`, `crates/configra-ops`, `crates/config-schema`, `crates/phenotype-config-loader`, `crates/phenoctl` | `9b9275f0` (2026-08-21, 137 added files); `audits/absorption-justifications/Configra-2026-07-17.md:3-4` | **GIT BEATS DOC.** The audit's final disposition is `ARCHIVE_ONLY` ("absorption failsafe"); git shows 6 crates migrated. The audit also lists a 5-crate workspace and does **not** mention `phenoctl`, which git did migrate |
| 4 | `KooshaPari/Apisync` | direct | `crates/apisync` | `76cb136b` (2026-09-13, 126 files); `crates/apisync/PROVENANCE.md:1-13`; `registry/absorbed-crates/apisync/ABSORPTION.md` | VERIFIED. `crates/apisync/PROVENANCE.md:11` dates it 2026-09-14; the commit is 2026-09-13. Git wins on the date |
| 5 | `KooshaPari/PhenoContracts` | direct | `crates/phenotype-contracts` (2 files), `crates/phenotype-port-interfaces` (2 files) | `df365465` (2026-09-15, 5 files changed / 4 added) | **MESSAGE OVERCLAIMS.** Subject names three crates (`contracts`, `port-interfaces`, `port-traits`); the diff contains two. `crates/phenotype-port-traits` was added by `121f79f6` instead. No ledger file exists for this absorption |
| 6 | `KooshaPari/zz-merge-unk-Stashly` | direct | `crates/stashly`, `crates/pheno-cache-adapter`, `crates/phenotype-cache-adapter` | `121f79f6` (2026-09-15, 457 added files); `registry/absorbed-crates/stashly/ABSORPTION.md:1-9`; `audits/absorption-justifications/Stashly-2026-07-17.md` | **SCOPE WILDLY UNDERSTATED.** The commit also lands **47 other crate directories** (`crates/Cmdra` 89 files, `crates/phenotype-infrakit` 85, `crates/phenotype-governance` 51, `crates/pheno-agent` 47, `crates/pheno-proc-runtime` 31, `crates/phenotype-router-monitor` 30, `crates/phenotype-hub` 22, …). The audit's own verdict is `ARCHIVE_ONLY` |
| 7 | `KooshaPari/Pine` | direct | `crates/pine-core`, `crates/pine-syscall`, `crates/pine-loader`, `crates/pine-nvms`, `crates/pine-compat`, `docs/specs`, `assets/brand` | `248874cd` (2026-09-15); `audits/absorption-justifications/Pine-2026-07-17.md` | VERIFIED |
| 8 | `KooshaPari/PhenoAI` | direct | `agents/phenoagent` (1532 files), `crates/argis-extensions` (1504), `crates/eidolon-{core,desktop,mobile,sandbox}`, `crates/llm-router`, `crates/phenotype-router`, `servers/external`, `servers/substrate`, `native/src` | `208b0523` (2026-09-15, 3870 files, 593,950 insertions); `registry/absorbed-crates/eidolon/ABSORPTION.md:1-9`; `docs/absorption/eidolon/README.md:4,11` | VERIFIED as a commit. **Only 3 of its ≥15 destinations have any ledger** (`eidolon`, `argis-extensions`, `llm-router` via the manifest) |
| 9 | Substrate | direct | `crates/Cmdra`, `crates/pheno-agent`, `crates/pheno-proc-runtime`, `crates/phenotype-*` (30+), plus **the entire `absorption/` staging tree** (272 files) and 155 `crates/*` directories | `33673213` (2026-09-15, 4643 files changed, 4564 added); `crates/ABSORPTION_MANIFEST.md:3` | **MISLABELLED / MEGA-COMMIT.** Subject names one source; the diff carries at least 20 distinct lineages (see 2.1). This single commit is the first-commit provenance for 152 of 362 `crates/*` directories |
| 10 | `phenotype-docset-v1.1` (docs-3) | direct | `docs/phenotype-docset-v1.1` (260 files) | `7202e1b2` (2026-09-15) | VERIFIED. **Duplicate**: `docs/atlas/` (`6c9b79ca`) is a second copy of the same 32-product docset |
| 11 | `KooshaPari/PhenoDesign` | direct | `packages/ui`, `packages/design-tokens`, `src/tokens`, `docs/{tokens,stories,journeys,guide,components,xdd}`, `worklog.md` | `9afc0cd4` (2026-09-16, 81 files); `docs/absorption/phenoDesign/README.md`; `audits/absorption-justifications/phenoDesign-2026-07-17.md` | VERIFIED |
| 12 | `KooshaPari/PhenoFabric` | direct | `crates/fabric-{frame-transport,gui,graph,daemon,cli,capability}`, `cmd/{checker,wire}`, `docs/{adr,ecosystem,research}`, `work/wbs.md` | `365a3572` (2026-09-16, 997 files) | **NO LEDGER.** No `ABSORPTION.md`, `PROVENANCE.md`, `docs/absorption/PhenoFabric/`, or justification file exists |
| 13 | `KooshaPari/PhenoInfra` | direct | `_archived/byteport`, `_archived/nanovms-core`, `infrakit/crates`, `docs/atlas`, `sites/*-landing`, `docs/research`, `docs/sessions`, `worklog/` | `6c9b79ca` (2026-09-16, 2382 files) | **NO LEDGER** for the absorption itself; `audits/absorption-justifications/phenotype-infra-2026-06-23.md` audits a different repo of a similar name |
| 14 | `KooshaPari/PhenoLab` | direct | `bench/{results,datasets,suites,runner,comparison}`, `kernels/qwen3.5-0.8b`, `eval/results`, `pheno/evidence`, `state/hf_scrape`, `docs/{okf,audits,plans}` | `a2437820` (2026-09-16, 1553 files) | **NO LEDGER** |
| 15 | `KooshaPari/PhenoGfx` | direct | `unity/{postfx,terrain,water,postfx-shaders}`, `src/{voxel,terrain,water,postfx}`, `phenotype-gfx/{ports,rendering}`, `tests/unity*` | `25c8dde1` (2026-09-16, 408 files) | **NO LEDGER.** Also a **duplicate destination**: `crates/phenotype-gfx` came from `9047e9dc` (2026-07-17) |
| 16 | `KooshaPari/PhenoRegistry` | direct | `audits/org-audits` (1221 files), `audits/org-audit-snapshots` (425), `audits/absorption-justifications` (**93**), `registry/absorbed-crates` (**89**), `archives/zz-archive-phenotype-registry` (224), `docs/specs` (478), `docs/{boundary,intent,sessions}`, `handbook/docs` | `f7ab4cdb` (2026-09-16, 3848 files) | VERIFIED as a commit. **This commit, not a ledger commit, is where the entire absorption-justification and absorbed-crates corpus enters the repo** |
| 17 | `KooshaPari/PhenoMLX` | direct | `python/omlx_research` (115), `apps/bench-cockpit`, `hfscope/*`, `evals/harbor`, `research/baselines`, `scripts/{tests,evals}` | `7a8ef302` (2026-09-16, 587 files); `hfscope/PROVENANCE.md:3-5` | PARTIAL LEDGER. Only the `hfscope` sub-component has provenance; the other ~15 destinations have none |
| 18 | frontier untracked-recovery snapshot | direct | `crates/hexa-kit` and 5414 other files | `618ffd3c` (2026-08-08, 5415 files changed; message claims 5421 and "16 commits") | **SQUASHED, NOT AN ABSORPTION.** `docs/audits/GIT-HISTORY-INTEGRITY.md` §2.3 records 16 commits collapsed here. `crates/hexa-kit/ABSORPTION_META.json` claims `absorbed_from: <REDACTED>/HexaKit`, `absorbed_at_utc: 2026-07-30T00:15:00Z` — a date **nine days before** the commit that lands the directory |
| 19 | `phenotype-gfx` (graphics kernel) | direct | `crates/phenotype-gfx` | `9047e9dc` (2026-07-17, 261 files) | **MISSING FROM THE COORDINATOR'S COMMIT LIST.** Found by `git log --grep=absorb` |
| 20 | `KooshaPari/FocalPoint` | direct | 52 `crates/*` directories (`focus-*` 42, `connector-*` 10) | `19f8e0eb` (2026-09-16, 310 files); `audits/absorption-justifications/FocalPoint-2026-07-17.md` | **MISSING FROM THE COORDINATOR'S COMMIT LIST.** Subject says "53 crates"; count of new `crates/*` dirs is 52 |
| 21 | `clap-ext` | direct | `crates/clap-ext`, `crates/clap-ext-examples` | `9f49359b` (2026-08-14, `#289`) | **MISSING FROM THE COORDINATOR'S LIST.** Attested only by that commit; no ledger |
| 22 | `phenoData` | direct | `crates/pheno-data-from-phenoData` (14 files) | `175afc87` (2026-06-08, 15 files); `docs/absorption/phenoData/README.md:6,17-21,32` | **GIT BEATS DOC, twice.** See §2.3 |

### 1b. Absorptions attested only by prose (no import commit, or a docs-only commit)

| # | Source repo | Hop chain | Destination | Evidence | Status |
|---|---|---|---|---|---|
| 23 | `KooshaPari/PhenoTooling` (the repo itself) | `phenotype-tooling` → `pheno` (here) | whole repo | `84613848` (2026-09-15) touches **one file**, `docs/phenotype-docset-v1.1/products/PhenoTooling/DOSSIER.md`; `crates/tokn/PROVENANCE.md:6`; `crates/datakit/PROVENANCE.md:12` | **PROSE-ONLY.** No commit imports the repo. `84613848`'s subject is the only evidence for the repo-level claim |
| 24 | `KooshaPari/phenoRouterMonitor` | **two-hop**: `phenoRouterMonitor` → `phenoAI` → here | `<REDACTED>/phenoAI/crates/llm-router/` → `crates/llm-router` | `crates/ABSORPTION_MANIFEST.md:14-20`; `crates/llm-router` first added by `208b0523` | **PROSE + GIT.** Hop 2 is provable; hop 1 is prose only, and the manifest itself says "Source repo was archived with only 0-byte placeholders; no code migration" |
| 25 | `KooshaPari/phenotype-router-monitor` | **two-hop**: → `phenotype-tooling` → here | `absorption/phenotype-router-monitor/` and `crates/phenotype-router-monitor/` | `crates/ABSORPTION_MANIFEST.md:52` ("canonical owner `phenotype-tooling/absorption/`"); `121f79f6` for `crates/`; `33673213` for `absorption/` | **THREE LIVE COPIES**, byte-identical: `phenotype-router-monitor/src/lib.rs`, `absorption/phenotype-router-monitor/src/lib.rs`, `crates/phenotype-router-monitor/src/lib.rs` all md5 `816d3875830c422157b8b65513f42be8` |
| 26 | `KooshaPari/BytePort` | two-hop | `absorption/byteport/` (stub) + `apps/byteport` + `_archived/byteport` + `sites/byteport-landing` | `absorption/byteport/README.md:3,5,7,16-17`; `audits/absorption-justifications/BytePort-2026-06-23.md:87-89` | **CLAIMED-BUT-ABSENT.** `absorption/byteport/README.md:17` says "`crates/byteport/` — interim subtree merge (history-preserving)"; `crates/byteport` does not exist. The BytePort audit targets `phenotype-infra/packages/byteport-rust-*`, a repo not present here |
| 27 | `KooshaPari/heliosBench` | two-hop | `absorption/helios-bench/` (stub) + `crates/heliosbench` | `absorption/helios-bench/README.md:3,5,18`; `crates/heliosbench` first added by `33673213` | **CLAIMED-BUT-ABSENT.** README §Paths implies a history-preserving subtree merge; the crate arrives inside a mega-commit instead |
| 28 | `KooshaPari/ResumeAll` (`resume-all`) | direct | `absorption/resume-all/` (101 files) | `33673213`; `absorption/resume-all/PROVENANCE.md:1-11` | PARTIAL. Provenance covers 2026-08-14/15 capture; the arrival date is the mega-commit |

### 1c. Multi-hop chains (called out explicitly, as required)

| Chain | Hops | Provable where | Broken where |
|---|---|---|---|
| `phenoRouterMonitor` → `phenoAI` → **here** | 2 | hop 2 = `208b0523` adds `crates/llm-router` | hop 1 is prose (`crates/ABSORPTION_MANIFEST.md:14-20`); the manifest says the source had "only 0-byte placeholders" |
| `zz-merge-unk-{Tokn,DataKit,PhenoPlugins,ArgisExtensions,local-ops,Tasken}` → `phenotype-tooling` → **here** | 2 | hops land in `33673213` / `121f79f6` / `208b0523` | hop 1 is prose only; see `crates/tokn/PROVENANCE.md:6`, `crates/datakit/PROVENANCE.md:12-13`, `crates/local-ops/PROVENANCE.md:17`, `crates/phenotype-plugins/PROVENANCE.md:5-14`, `crates/argis-extensions/PROVENANCE.md:5-9`, `crates/tasken/PROVENANCE.md:5-14` |
| `Apisync` → `apikit` → `phenotype-tooling` → **here** | 3 | `registry/absorbed-crates/apisync/ABSORPTION.md:5,17-18,43-49` (manifest of the rehoming); `76cb136b` lands the code | No commit records hop 1 or hop 2 inside this repo. `apikit` and `phenotype-tooling/docs/absorbed-from-apikit/` are both absent from this tree |
| `Stashly` → `pheno` (registry forensic copy) → **here** | 2 | `registry/absorbed-crates/stashly/ABSORPTION.md:9`; `121f79f6` | The registry copy is itself "for forensic audit"; the canonical target is described as living under `portage.git` federation — `crates/portage` does not exist here |
| `Eidolon` → `pheno` monorepo → **here** | 2 | `registry/absorbed-crates/eidolon/ABSORPTION.md:9`; `208b0523` | `pheno` in hop 1 means this repo, so the hop is nominal: the registry copy *is* the destination copy |
| `PhenoForge` → `docs/absorbed/schemaforge/` → **here** | 2 | `absorption/pheno-forge/PROVENANCE.md:20`; `33673213` | hop 1 is prose inside a PROVENANCE file, not a commit |
| `zz-archive-phenotype-registry` → `archives/zz-archive-phenotype-registry` → **here** | 2 | `f7ab4cdb` | Archived-name mapping only; the original repo name is not recoverable from the tree |

### 1d. The submodule era — 109 repos, all removed, none re-checked-out

`git show 8c85d576^:.gitmodules` lists **109** `[submodule]` entries. `8c85d576`
(2026-09-16 04:22) removed them all; `ab95ace` (04:30, eight minutes later)
deleted the remaining `.gitmodules`. **None of the 109 paths exists in the tree
today** (verified by existence test on each path). The commit subject says "94
broken submodules"; the file it deleted contained 109.

This is the third and largest import mechanism in this repo, and it is invisible
to every `ABSORPTION*.md` ledger. Full list, verbatim from
`git show 8c85d576^:.gitmodules`:

```
agileplus-plugin-core agileplus-plugin-git agileplus-plugin-sqlite bare-cua BytePort clikit
cloud Cmdra Cursora Datamold Dino Docuverse Duple Evalora Flagward Flowra Guardis helios-cli
helix-logging helMo Hexacore HexaGo hexagon-python hexagon-rs hexagon-ts HexaPy HexaType
Httpora KaskMan kits KodeVibeGo Kogito nanovms omniroute-temp org-github phenodocs phenoSDK
phenotype-agent-core phenotype-auth-ts phenotype-cipher phenotype-cli-extensions
phenotype-config-ts phenotype-dep-guard phenotype-docs-engine phenotype-evaluation
phenotype-forge phenotype-logging-zig phenotype-middleware-py phenotype-patch
phenotype-research-engine phenotype-sentinel phenotype-skills phenotype-task-engine
phenotype-templates phenotype-types phenotype-vessel phenotype-xdd-lib Planify
platforms/thegent-pr882 PolicyStack portage Portalis Profila Queris Quillr
repos/phenotype-bootstrap repos/phenotype-replication-engine Schemaforge Seedloom sharecli
template-domain-service-api template-domain-webapp template-lang-elixir-hex template-lang-go
template-lang-kotlin template-lang-mojo template-lang-python template-lang-rust
template-lang-swift template-lang-typescript template-lang-zig template-program-ops
templates/template-domain-service-api-remote-20260402
templates/template-domain-webapp-remote-20260402
templates/template-lang-elixir-hex-remote-20260402
templates/template-lang-kotlin-remote-20260402 templates/template-lang-mojo-remote-20260402
templates/template-lang-python-remote-20260402 templates/template-lang-rust-remote-20260402
templates/template-lang-swift-remote-20260402 templates/template-lang-zig-remote-20260402
templates/template-program-ops-remote-20260402 thegent-cache thegent-mesh thegent-metrics
thegent-plugin-host thegent-sharecli thegent-shm thegent-subprocess Tokn Tossy tracely
Tracera vendor/phenodocs vibeproxy vibeproxy-monitoring-unified worktree-manager zen Zerokit
```

A handful of these names reappear as absorbed destinations under different paths
(`Tokn` → `crates/tokn`; `Planify` → `registry/absorbed-crates/Planify`;
`PolicyStack` → `crates/policystack`; `nanovms` → `crates/nanovms`;
`Quillr` → `docs/absorption/Quillr`; `Tracera` → `audits/absorption-justifications/Tracera-*`).
For the remaining ~100, the submodule entry is the **only** record that the repo
was ever attached to this tree, and the entry is now only reachable through
`git show 8c85d576^:.gitmodules`.

---

## 2. Coverage reconciliation

### 2.1 Destinations present in the tree with NO absorption commit

`crates/` holds **362** first-level directories (README.md:20 claims 329
first-level `Cargo.toml` manifests; both can be true — 33 directories carry no
manifest). Grouping each directory by the commit that first added it:

| First commit | Dirs | What it is |
|---|---:|---|
| `33673213` "absorb Substrate" | 152 | mega-commit, §1a #9 |
| `121f79f6` "absorb stashly" | 47 | mega-commit, §1a #6 |
| `208b0523` "absorb PhenoAI" | 24 | §1a #8 |
| `365a3572` "absorb PhenoFabric" | 21 | §1a #12 |
| `618ffd3c` preserve snapshot | 2 | squashed 16-commit snapshot |
| `9b9275f0`, `248874cd`, `c3f47016`, `f7ab4cdb`, `76cb136b`, `df365465`, `25c8dde1` | 18 | minor absorptions |
| **Total attributable to the 20 known absorption commits** | **264** | |
| `19f8e0eb` "extract 53 crates from FocalPoint" | 52 | absorption missing from the coordinator's list |
| `5677bae9` `chore: consolidation (#439)` | 16 | 2026-03-30 bulk consolidation |
| `fd8e1158` `chore: ignore src (#437)` | 7 | housekeeping |
| `98d5aa42` `chore(pheno): lift ahead branch (#177)` | 4 | housekeeping |
| `6016c04a` `chore: apply phenotype governance standards` | 3 | housekeeping |
| other commits | 16 | scattered |
| **Total unattributed to a named absorption** | **98** | |

**98 of 362 crate directories (27%) have no absorption commit.** Of those, 52 are
explained by `19f8e0eb` (an absorption the coordinator's list omits), leaving
**46 crate directories whose arrival is explained only by generic workspace
churn commits** (`5677bae9`, `fd8e1158`, `98d5aa42`, `6016c04a`).

Beyond `crates/`, the same gap applies to these top-level destinations that exist
with no absorption commit naming them:

| Destination | Files | First commit | Ledger |
|---|---:|---|---|
| `crates/phenotype-gfx` | 261 | `9047e9dc` (2026-07-17) | none |
| `crates/pheno-data-from-phenoData` | 14 | `175afc87` (2026-06-08) | ledger says the opposite, §2.3 |
| `crates/clap-ext`, `crates/clap-ext-examples` | 42 | `9f49359b` (2026-08-14) | none |
| `infrakit/` | 53 dirs | `6c9b79ca` | none |
| `agents/phenoagent` | 1532 | `208b0523` | none for the Python side |
| `servers/{external,substrate,forge3-bridge}` | 382 | `208b0523` | none |
| `apps/byteport`, `apps/bench-cockpit`, `sites/byteport-landing` | — | `6c9b79ca`, `7a8ef302` | `apps/byteport` is named in no ledger |

### 2.2 Absorptions with NO ledger entry in any ABSORPTION.md / PROVENANCE.md

Determined by filename-level test (is there a ledger file named for the source?)
across `docs/absorption/`, `audits/absorption-justifications/`,
`registry/absorbed-crates/`, and every `*PROVENANCE*.md`:

| Source | Commit | Ledger file named for it |
|---|---|---|
| PhenoFabric | `365a3572` | **none** |
| PhenoLab | `a2437820` | **none** |
| PhenoInfra | `6c9b79ca` | **none** |
| PhenoRegistry | `f7ab4cdb` | **none** (it *carries* the 93-file audit corpus) |
| PhenoContracts | `df365465` | **none** |
| Substrate | `33673213` | **none** (only the generic `crates/ABSORPTION_MANIFEST.md`) |
| PhenoMLX | `7a8ef302` | **none** (only `hfscope/PROVENANCE.md`, one component) |
| PhenoAI | `208b0523` | **none** (only the Eidolon component) |
| PhenoGfx | `25c8dde1` | **none** |
| PhenoProc | (pre-history, wave 6) | **none** |
| PhenoTooling | `84613848` | **none** |
| ArgisExtensions | `208b0523` | none in the standard dirs (only `crates/argis-extensions/PROVENANCE.md`) |
| FocalPoint | `19f8e0eb` | only `audits/absorption-justifications/FocalPoint-2026-07-17.md` |

**12 of the 20 absorption commits have no per-source ledger at all.** The two
files the task asked about specifically are the whole story:
`crates/*/ABSORPTION.md` matches exactly **one** file, `crates/phinbox/ABSORPTION.md`
(604 lines), and its §"Code absorbed" says, twice, **"None."** — it is a
convention record, not an absorption. Every other `ABSORPTION.md` in the repo
lives outside `crates/*/`: `registry/absorbed-crates/{apisync,eidolon,stashly}/`,
and four copies under `audits/*/forge-runner-scripts/`.

### 2.3 Ledger claims with NO corresponding files (claimed but absent)

| Ledger claim | Claimed destination | Reality | Severity |
|---|---|---|---|
| `docs/absorption/phenotype-pm-core/README.md:8-9` | `crates/traceability-core/`, `crates/traceability-decorators/`, `crates/trace-gate/` | All three absent. `trace-gate.toml` exists at root and in 2 crates; no `trace-gate` crate. Only `crates/agile-plus/crates/traceability-core` exists, a different lineage | **HIGH** — a 3-crate absorption is documented as complete and left nothing |
| `docs/absorption/grapheon-bindings/README.md:7-8,48` | `packages/graphclient/` in `KooshaPari/phenotype-go-sdk` | Absent. `packages/` holds `auth, design-tokens, docs, github-fetcher, pheno-core, pheno-llm, pheno-resilience` | HIGH |
| `docs/absorption/phenoData/README.md:6,17-21,37-39` | `crates/pheno-data-{core,query,surreal,pg,smoke-tests}` | **All five absent.** Lines 32-33 claim 5 stale `crates/pheno-data-from-phenoData/` artefacts were *removed*; that directory exists with 14 files and is the only surviving phenoData code | **CRITICAL** — the ledger describes a complete migration that did not happen, and claims to have deleted the artefacts that are still the source of record |
| `docs/absorption/Benchora/README.md` | `crates/benchora/` | Absent. `audits/absorption-justifications/Benchora-2026-09-01.md` also exists | HIGH |
| `docs/absorption/pheno-forge-smoke/README.md` | `crates/pheno-sidecar-stub/` | Absent; the crate has 14 files under `registry/absorbed-crates/pheno-forge-smoke/sidecars/` | MEDIUM |
| `absorption/byteport/README.md:17` | `crates/byteport/` | Absent | MEDIUM |
| `docs/absorption/audit-tool/README.md:10`, `docs/absorption/scripts/README.md`, `docs/absorption/Sidekick/README.md:4`, `docs/absorption/template-commons/README.md:6`, `docs/absorption/PolicyStack/README.md:8`, `docs/absorption/PhenoSpecs/README.md:8`, `docs/absorption/{KodeVibe,KWatch,Quillr,utility-targets,curated-traces,localbase3,backend-melosviz}/README.md` | `KooshaPari/phenotype-python-sdk`, `phenokits-commons`, `phenotype-registry`, `phenotype-go-sdk`, `tools/kwatch/`, `tools/kodevibe/`, `crates/agent-user-status/` | None of these destinations exist in this repo (`tools/` has no `kwatch` or `kodevibe`; there is no `crates/agent-user-status`) | HIGH — 33 records, 11 with an explicit destination, and **none of the 11 destinations is in this tree** |
| `crates/ABSORPTION_MANIFEST.md:52` | `libs/phenotype-observability` → `PhenoObservability` | Absent (`libs/` exists, without that path) | MEDIUM |
| `crates/ABSORPTION_MANIFEST.md:26-27` | `adapters/web/agent-platform/` | Absent; `adapters/`, `web/` and `agent-platform/` are all absent | HIGH |
| `crates/ABSORPTION_MANIFEST.md:34` | `<REDACTED>/rich-cli-kit/crates/klipdot/` | Absent. Related survivors: `crates/klipdot-capture`, `crates/sharecli` | MEDIUM |
| `crates/ABSORPTION_MANIFEST.md:44` | root `agentkit` | Absent | LOW |
| `docs/ABSORPTION_INDEX.md:3,11-12,22` | `docs/absorbed-from/<repo>/README.md` for each index entry | Only **2** of 33 exist (`phenotype-hub`, `vibeproxy-monitoring-unified`) | MEDIUM — the index promises a disposition README per entry and carries 2 |
| `docs/audits/GIT-HISTORY-INTEGRITY.md:86,114` | `docs/audits/PII-SWEEP-DAMAGE.md` | **RESOLVED** — the artifact was written after this table was compiled and is present (committed in `eae02a5b`). Row retained as a worked example of how this class is found; re-run the check before relying on it | RESOLVED |
| `docs/absorption/pheno-forge-smoke/README.md:64-65` | repository URL rewritten to `<REDACTED>/pheno` | Cannot be checked; the repo is `PhenoShared` | LOW |

**Recovery status for this class (measured 2026-09-19).** Two facts, both
measured, and the second changes the conclusion:

1. The org is redacted in every record, so the documented restore command
   cannot be reconstructed from the ledger alone.
2. `git ls-remote` against `KooshaPari/agent-user-status` returns
   `Repository not found` over SSH and nothing over HTTPS. **This proves
   nothing about whether the repo still exists.** The SSH key authenticates
   account-wide (`ssh -T` reports `Hi KooshaPari!`) but is scoped as a
   **deploy key to PhenoShared only**: of three repos, `PhenoShared` is
   VISIBLE while `phenoAI` and `docs` — which certainly exist — both return
   the same `Repository not found`. A deploy key returns exactly this error
   for every repo outside its scope, so a private-but-intact source is
   indistinguishable from a deleted one from this host.

`gh auth status` reports the stored token **invalid** and neither `GH_TOKEN`
nor `GITHUB_TOKEN` is set. **Recovery is therefore blocked purely on
account-wide GitHub credentials, not on code and not on evidence that the
source is gone.** Re-authenticating the CLI (or adding an account-level SSH
key) is the first unblocking action; after that, every record in this class
becomes testable with one command.

**CAVEAT on the counts above (added 2026-09-19 after re-measuring).** This
section treats "destination" as one kind of thing. It is not. Re-measuring the
machine-readable registry (`projects/*.json`, 178 files) shows the destinations
fall into two kinds that must be counted separately:

| Destination kind | Behaviour | Correct classification |
|---|---|---|
| a repo-relative **path** (e.g. `crates/agent-user-status/`) | checkable with a filesystem test | absent ⇒ **violation** |
| a **repo slug or free text** (e.g. `phenotype-infra`, `pheno (crates/phench)`) | not checkable from this tree | absent ⇒ **unverifiable, NOT a violation** |

Of the 11 registry records with `status: "absorbed"`, only **one** supplies a
checkable path (`agent-user-status`, `absorbing_path: "crates/agent-user-status/"`,
absent — a genuine violation). Ten supply only free text, so their absence here
means nothing. Four of those ten do name local crates that exist
(`crates/logkit`, `crates/phench`, `crates/pheno-cdylib-bridge`,
`crates/pheno-forge-smoke`), i.e. those absorbs landed.

Consequence: the "none of the 11 destinations is in this tree" severity in
§2.3 is **inflated for the other-repo subset** and must not be quoted as a
count of defects until re-derived with the bucket rule. The genuine local-path
violations in that row are `tools/kwatch`, `tools/kodevibe` and
`crates/agent-user-status`.

### 2.4 Duplicate destinations (same code, two or three arrivals)
| Code | Copies | Arrivals |
|---|---|---|
| `phenotype-router-monitor/src/lib.rs` | **3**, byte-identical (md5 `816d3875…`) | `6016c04a` (2026-04-02, root), `33673213` (`absorption/`), `121f79f6` (`crates/`) |
| eyetracker crates | **2** | `2fe6b59a` (`crates/eyetracker/eyetracker-*`), `33673213` (`crates/eyetracker-*`) |
| 32-product docset | **2** | `7202e1b2` (`docs/phenotype-docset-v1.1/products/`), `6c9b79ca` (`docs/atlas/products/`) |
| PhenoGfx | **2** | `9047e9dc` (`crates/phenotype-gfx`), `25c8dde1` (`phenotype-gfx/`) |
| BytePort | **4 partial** | `absorption/byteport` (stub), `apps/byteport`, `_archived/byteport`, `sites/byteport-landing` |
| nanovms | **2** | `crates/nanovms`, `_archived/nanovms-core`, plus `_archived/nvms-ffi` |

---

## 3. Damage: provenance destroyed by redaction

### 3.1 Mechanism

Two commits, both 2026-09-16:

* `3b6d8798` `chore: PII sweep — redact names, emails, paths across all files` — 4214 files, 35,813 insertions / 35,813 deletions (pure 1:1 substitution).
* `eb6fd899` `chore: PII deep-clean pass 2 + GitHub URL restoration` — 1691 files. It restored `github.com/<REDACTED>/…` → `github.com/KooshaPari/…` but **did not** restore bare `<REDACTED>/Repo` source paths.

A third commit, `cf914698` (2026-09-17), mechanically sanitised the *filenames* the
sweep had produced: `com.<REDACTED>.resume-all-*.plist` → `com.REDACTED.resume-all-*.plist`,
because `<` and `>` are invalid in Windows paths.

The token is **polysemous**: `<REDACTED>` stands for the GitHub org `KooshaPari`,
the OS user `kooshapari`, and the bundle-id segment `kooshapari`, interchangeably.
That is why `eb6fd899` could restore URLs but not paths — a mechanical restore
cannot tell the three apart.

### 3.2 Scale (measured, and a correction to the existing audit)

| Measure | Value | Method |
|---|---:|---|
| Tracked files containing `REDACTED` | **3423** | `git grep -l REDACTED` |
| …of which markdown | **1986** | `git grep -l REDACTED -- '*.md'` |
| Occurrences | **40581** | `git grep -o REDACTED` |
| Distinct `<REDACTED>/<token>` values | **1714** | `grep -rhoI` over the working tree |
| …excluding hidden-file names (i.e. repo-ish tokens) | 1370 | same, filtered |
| Files with a repo-shaped `<REDACTED>/<Name>` token | 2400 | same |

`docs/audits/GIT-HISTORY-INTEGRITY.md:82` and `:170` state **2,541 tracked files
(1,985 markdown)**. That figure is **lower than what the tree measures now** and
its supporting artifact (`docs/audits/PII-SWEEP-DAMAGE.md`) is absent. My numbers
are higher by 882 files / 8911 occurrences. I cannot reproduce 2541 from the tree
at any commit I checked; treat 3423 / 40581 as the measured values and the 2541
claim as **unverified**.

### 3.3 Provenance-specific redaction sites (the unrecoverable-in-file list)

These are the sites where the *provenance itself* — the source repo identity —
was replaced. **51 ledger files contain the token; 37 of them carry no
`KooshaPari` URL anywhere in the file**, so the lost value cannot be inferred
from the document at all and is recoverable only from git (§3.4). The 37 are
listed below; the other 14 are listed after.

**Not recoverable from the same file** (no `KooshaPari` URL anywhere in the file):

| File:line | Redacted content | What was lost |
|---|---|---|
| `crates/ABSORPTION_MANIFEST.md:3` | `<REDACTED>/PhenoProc` | org for the wave-6 source |
| `crates/ABSORPTION_MANIFEST.md:7` | `<REDACTED>/PhenoAgent` | org for the PhenoAgent source |
| `crates/ABSORPTION_MANIFEST.md:14` | `<REDACTED>/phenoRouterMonitor` | **hop-1 source of a two-hop chain** |
| `crates/ABSORPTION_MANIFEST.md:15` | `<REDACTED>/phenoAI/crates/llm-router/` | **hop-1 intermediate repo** |
| `crates/ABSORPTION_MANIFEST.md:18` | `<REDACTED>/phenoAI/ports/` | **hop-1 intermediate repo** |
| `crates/ABSORPTION_MANIFEST.md:25` | `<REDACTED>/agent-platform` | source repo for the Agentora adapter |
| `crates/ABSORPTION_MANIFEST.md:34` | `<REDACTED>/rich-cli-kit/crates/klipdot/` | source repo for the KlipDot target |
| `crates/ABSORPTION_MANIFEST.md:45` | `<REDACTED>/AgilePlus` | canonical owner of `agileplus-*` |
| `crates/hexa-kit/ABSORPTION_META.json` (`absorbed_from`) | `<REDACTED>/HexaKit` | JSON — no URL field at all |
| `crates/apisync/PROVENANCE.md:10` | `Absorbed by <REDACTED>/pheno` | the absorbing repo's org name |
| `absorption/resume-all/PROVENANCE.md:5` and `absorption/resume-all/README.md:26` | `com.<REDACTED>.resume-all-*` | macOS bundle-id prefix |
| `absorption/pheno-forge/README.md:3` | "deleted from the `<REDACTED>` organization" | org name in a deletion notice |
| `absorption/phenotype-router-monitor-root/README.md:35` | `/Users/<REDACTED>/CodeProjects/Phenotype/repos/PhenoProc/phenotype-router-monitor` | local path; note this line **simultaneously proves** the `PhenoProc/phenotype-router-monitor` nesting |
| `registry/absorbed-crates/eidolon/ABSORPTION.md:1,7,52` | `<REDACTED>/Eidolon` ×3 | source repo, 3 sites |
| `registry/absorbed-crates/stashly/ABSORPTION.md:1,7,47` | `<REDACTED>/Stashly` ×3 | source repo, 3 sites |
| `docs/absorption/agent-user-status/README.md` | `<REDACTED>/agent-user-status` | **the rename-target of the source repo** |
| `docs/absorption/audit-tool/README.md:10,33,47` | `<REDACTED>/audit-tool` | source repo + local path |
| `docs/absorption/Benchora/README.md:7` | `<REDACTED>/Benchora` | source repo |
| `docs/absorption/curated-traces/README.md` | source repo | **entire source identity** |
| `docs/absorption/eidolon/README.md:4,11` | `<REDACTED>/Eidolon` | source repo |
| `docs/absorption/KodeVibe/README.md:7` | `<REDACTED>/KodeVibe` | source repo |
| `docs/absorption/localbase3/README.md` | source repo | **entire source identity** |
| `docs/absorption/phench/README.md:7,79-80` | `<REDACTED>/phench`, `<REDACTED>/phenotype-tooling` | source **and** intermediate repo |
| `docs/absorption/pheno-cdylib-bridge/README.md:7` | `<REDACTED>/pheno-cdylib-bridge` | source repo |
| `docs/absorption/pheno-context/README.md:3-4` | `<REDACTED>/pheno-context`, `<REDACTED>/pheno` | source and destination |
| `docs/absorption/pheno-forge-smoke/README.md:3,4,15,16,64,115,116` | 7 sites | source repo, target repo, repo URL |
| `docs/absorption/pheno-runtime-config/README.md:3,4` | source and target | — |
| `docs/absorption/phenoData/{README.md:5,13,56, ACTIVE_SOURCE_REVALIDATION_20260807.md:10,15,23,39}` | 8 sites | source repo for a **CRITICAL**-severity absent-destination claim |
| `docs/absorption/phenoDesign/README.md:11,13` | `<REDACTED>/phenoDesign`, `<REDACTED>/asset-engine` | source repo + a **second** repo (`asset-engine`) named nowhere else |
| `docs/absorption/phenoEvents/README.md` | source repo | entire source identity |
| `docs/absorption/PhenoKits/MATRIX.md` | matrix of sources | **whole matrix** |
| `docs/absorption/PhenoLang/README.md:4-5` | source repo + local path | — |
| `docs/absorption/PhenoPlugins/README.md` | source repo | — |
| `docs/absorption/phenoResearchEngine/README.md:7` | source repo | — |
| `docs/absorption/PhenoSpecs/README.md:7-8` | source + target repo | — |
| `docs/absorption/phenotype-pm-core/README.md:7-8` | source + target repo | — |
| `docs/absorption/phenotype-router-spec/README.md` | source repo | — |
| `docs/absorption/phenoUtils/README.md:4` | `<REDACTED>/phenoUtils` | — |
| `docs/absorption/PolicyStack/README.md:7-8` | source + target repo | — |
| `docs/absorption/Quillr/README.md` | source repo | — |
| `docs/absorption/scripts/README.md:4,32` | `<REDACTED>/scripts` | — |
| `docs/absorption/Sidekick/README.md:4,34` | source repo | — |
| `docs/absorption/template-commons/README.md:6,7,91,100` | source + target + GitHub API command | — |
| `docs/absorption/utility-targets/README.md` | source repo | — |

**Recoverable in-file** (a `KooshaPari` URL survived on a neighbouring line, so
the org is inferable without git): `crates/eyetracker-PROVENANCE.md:5`,
`crates/argis-extensions/PROVENANCE.md:5`, `crates/datakit/PROVENANCE.md:5`,
`crates/local-ops/PROVENANCE.md:16-17`, `crates/phenotype-plugins/PROVENANCE.md:5`,
`crates/tokn/PROVENANCE.md:5-6`, `absorption/pheno-forge/PROVENANCE.md:5`,
`absorption/byteport/README.md:3,5`, `absorption/helios-bench/README.md:3,5`,
`absorption/resume-all/README.md`,
`docs/absorption/backend-melosviz/README.md:104` (`https://github.com/KooshaPari/backend`),
`docs/absorption/grapheon-bindings/README.md:26`
(`github.com/KooshaPari/phenotype-go-sdk/packages/graphclient`),
`registry/absorbed-crates/apisync/ABSORPTION.md` (the only one of the three
registry entries that kept its URLs).

**Filename-level loss** (15 files): `absorption/resume-all/launchd/com.REDACTED.resume-all-*.plist`.
The original names were `com.kooshapari.resume-all-*.plist`, recoverable only via
`git show cf914698 --name-status` or `git ls-tree 3b6d8798^:absorption/resume-all/launchd`.

### 3.4 Recoverability — git beats the existing audit

`docs/audits/GIT-HISTORY-INTEGRITY.md:174-177` concludes:

> "**Unrecoverable:** the 16 commits collapsed into `618ffd3c`, the intermediate
> states of 415 squashed PRs, and **any provenance path the PII sweep redacted
> without a recorded original.**"

The first two are correct. **The third is wrong and must be corrected.** The PII
sweep is an ordinary forward content commit, so the pre-sweep bytes are the parent
tree:

```
$ git show 3b6d8798^:crates/ABSORPTION_MANIFEST.md | sed -n '3p'
Files under `crates/` from archived `KooshaPari/PhenoProc` (wave 6, 2026-06-17).

$ git show 3b6d8798^:docs/absorption/phenotype-pm-core/README.md | sed -n '7,9p'
| Source repo | `KooshaPari/phenotype-pm-core` |
| Target repo | `KooshaPari/phenotype-tooling` |
| Target paths | `crates/traceability-core/`, `crates/traceability-decorators/`, `crates/trace-gate/` |

$ git ls-tree --name-only 3b6d8798^:absorption/resume-all/launchd | head -1
com.kooshapari.resume-all-bridge-health.plist
```

**Every redaction in §3.3 that existed before `3b6d8798` is fully recoverable**,
verbatim, from `3b6d8798^`. The genuinely unrecoverable class is much smaller:
text that `3b6d8798` truncated rather than substituted — `<REDACTED>/Cod...`,
`<REDACTED>/CodeProj...`, `<REDACTED>/Conft.` — where an ellipsis appears inside
the token, meaning the sweep operated on already-truncated source text. Those
sites are unrecoverable from git too.

The remedy is one command per file, e.g.
`git show 3b6d8798^:<path> > <path>` for the 37 ledger files in §3.3, followed
by re-applying `eb6fd899`'s URL-restoration convention.

---

## 4. Dangling references

Relative links in the ledgers that do not resolve. Scanned: 242 ledger files
(`crates/ABSORPTION_MANIFEST.md`, `crates/phinbox/ABSORPTION.md`, all
`*PROVENANCE*.md`, all of `absorption/**/*.md`, `docs/absorption/**/*.md`, all 92
`audits/absorption-justifications/*.md`, all of `registry/absorbed-crates/**/*.md`).
**40 dangling links** total: **13 are lineage-relevant** (listed below) and 27 are
intra-crate VitePress nav stubs (`./quick-start`, `./core-integration`,
`../reference/api`, …) inside the copies under `absorption/pheno-forge/`, which
have nothing to do with provenance.

### 4.1 Lineage-relevant dangling references

| Ledger:line | Link | Where it would have pointed | Does the target exist anywhere in this repo? |
|---|---|---|---|
| `crates/ABSORPTION_MANIFEST.md:9` | `../absorption/PHENOAGENT_ABSORPTION_2026_06_18.md` | `absorption/PHENOAGENT_ABSORPTION_2026_06_18.md` — the only ledger for the PhenoAgent absorption | **NO.** Exhaustive `find` for `PHENOAGENT_ABSORPTION*` returns nothing. This was the sole record for one of the 50+ absorptions |
| `crates/ABSORPTION_MANIFEST.md:20` | `../../../migration-work/registry-wt/docs/operations/p5-4-phenoroutermonitor-absorption-2026-06-20.md` | from `crates/`, `../../../` climbs out of the repo to `Phenotype/migration-work/registry-wt/…`. Repo-root-equivalent: `../migration-work/registry-wt/docs/operations/p5-4-phenoroutermonitor-absorption-2026-06-20.md` | **YES — relocated.** The file exists at `docs/operations/p5-4-phenoroutermonitor-absorption-2026-06-20.md`. The absorption was absorbed; the link was not rewritten. `migration-work/` itself does not exist, here or in the parent directory |
| `absorption/byteport/README.md:24` | `../../docs/absorption/BYTEPORT_PORT.md` | `docs/absorption/BYTEPORT_PORT.md` | **NO.** No file of that name exists. `docs/boundary/BytePort.md` and `docs/intent/BytePort.md` exist but are different documents |
| `absorption/helios-bench/README.md:25` | `../../docs/absorption/HELIOS_BENCH_PORT.md` | `docs/absorption/HELIOS_BENCH_PORT.md` | **NO.** No file of that name exists |
| `registry/absorbed-crates/stashly/ADR.md:3` | `./docs/adr/001-initial-architecture.md` | `registry/absorbed-crates/stashly/docs/adr/001-initial-architecture.md` | **NO.** The registry copy kept `src/`, `benches/` and ADR.md but not `docs/` |
| `registry/absorbed-crates/apisync/README.md:153` | `./LICENSE` | `registry/absorbed-crates/apisync/LICENSE` | **NO.** `crates/apisync/LICENSE` likely exists; the registry pointer copy has no LICENSE |
| `registry/absorbed-crates/eidolon/README.md:44` | `assets/logo.svg` | within the registry copy | **NO** |
| `registry/absorbed-crates/eidolon/README.md:373-377` | `../Sidekick`, `../PhenoObservability`, `../Paginary`, `../phenoShared` | sibling entries under `registry/absorbed-crates/` | **NO for all four.** `registry/absorbed-crates/` holds only 7 entries (`apisync`, `DataKit`, `eidolon`, `pheno-forge-smoke`, `Planify`, `stashly`, `thegent`). These four links are the only trace of a much larger intended registry |
| `registry/absorbed-crates/eidolon/README.md:381` | `./LICENSE` | registry copy | **NO** |
| `registry/absorbed-crates/DataKit/README.md:4` | `./TOMBSTONE.md` | registry copy | **NO** |
| `docs/audits/GIT-HISTORY-INTEGRITY.md:86,114` | `docs/audits/PII-SWEEP-DAMAGE.md` | the damage audit that produced the `2,541` figure | **NO** |
| `docs/ABSORPTION_INDEX.md:3,22` | `docs/absorbed-from/<repo>/README.md` | per-repo disposition README | **31 of 33 absent** (only `phenotype-hub`, `vibeproxy-monitoring-unified` exist) |

### 4.2 Crate-to-crate references that dangle because the destination is absent

Not markdown links, but the same class of breakage: ledger-named destinations
that no other file in the repo can reach. Covered in §2.3. The most consequential
are `crates/traceability-{core,decorators}`, `crates/trace-gate`,
`packages/graphclient`, and the five `crates/pheno-data-*`.

---

## 5. What we can and cannot prove

### Provable from git (commit hash + path, reproducible)

1. **That a path arrived.** `git log --diff-filter=A -- <path>` gives the exact
   commit for all 362 `crates/*` directories and every top-level destination.
2. **When.** All 693 commits, timestamps monotonic; `docs/audits/GIT-HISTORY-INTEGRITY.md`
   §1 independently confirms single-root, no rewrite, no force-push evidence.
3. **That the import was additive.** Every absorption commit is `--diff-filter=A`
   only; nothing in the absorption cluster deletes >500 files.
4. **Where each absorption commit put things** — exactly: `git show --name-status --diff-filter=A <hash>`.
5. **That the PII redaction is reversible.** `git show 3b6d8798^:<path>` for every
   ledger in §3.3. This contradicts the "unrecoverable" verdict at
   `docs/audits/GIT-HISTORY-INTEGRITY.md:174-177`.
6. **That 109 repos were submodule-attached and are now gone.** `git show 8c85d576^:.gitmodules`.
7. **That 3 byte-identical copies of `phenotype-router-monitor` exist.** md5 comparison.
8. **That `phenoData`'s documented migration produced nothing.** The 5 claimed
   crates have no commit; `crates/pheno-data-from-phenoData` does (`175afc87`).

### Provable only from prose (a doc says so; no commit corroborates)

1. Hop 1 of every two-hop chain (§1c): `phenoRouterMonitor → phenoAI`,
   `zz-merge-unk-* → phenotype-tooling`, `Apisync → apikit → phenotype-tooling`.
   The intermediate repos are named in PROVENANCE files and in
   `registry/absorbed-crates/apisync/ABSORPTION.md`; no commit in this repo
   records the move into the intermediate.
2. The repo-level claim that `PhenoTooling` was "fully absorbed into pheno"
   (`84613848`, one file, a dossier edit).
3. Source repo identities where the commit message is generic and the ledger is
   generic: everything arriving via `33673213` and `121f79f6` except the handful
   with a per-crate `PROVENANCE.md`.
4. `crates/hexa-kit/ABSORPTION_META.json`'s `2026-07-30T00:15:00Z` timestamp
   (git says the directory lands 2026-08-08).
5. Capture dates in `absorption/resume-all/PROVENANCE.md` and
   `absorption/pheno-forge/PROVENANCE.md` — the provenance is a narrative of what
   was copied from where, not a commit.

### Not provable at all, from anything in this repo

1. **Which of the 109 former submodules became which current destination.**
   The `.gitmodules` names and the current paths do not line up (`template-lang-go`
   vs `template-go`; `Tokn` vs `crates/tokn`; ~100 with no counterpart). The
   mapping, if it existed, was in the submodules' own histories, which were never
   fetched.
2. **The 16 commits squashed into `618ffd3c`.** Their intermediate states are gone.
3. **The intermediate states of the 415 squash-merged PRs** (60% of the ledger),
   including every absorption PR (#281, #282, #289, #334). Only the squashed
   result exists.
4. **The true source of the 152 `crates/*` directories landed by `33673213`.**
   The commit says "Substrate"; the tree carries PhenoProc, PhenoAgent, Tokn,
   DataKit, Tasken, PhenoPlugins, ArgisExtensions, eyetracker, Configra and others.
   The mix is provable; the per-directory attribution is not.
5. **Truncated redactions.** Any `<REDACTED>/Cod...`-style token (literal ellipsis
   inside the placeholder) — the original was already truncated before the sweep.
6. **`docs/audits/PII-SWEEP-DAMAGE.md`** and the arithmetic behind the `2,541`
   figure.
7. **`absorption/PHENOAGENT_ABSORPTION_2026_06_18.md`** — the only PhenoAgent
   ledger, referenced and never present.
8. **Whether `crates/byteport`, `crates/pheno-data-*`, `crates/trace-gate`,
   `packages/graphclient`, `adapters/web/agent-platform` ever existed here.**
   No commit adds them and no commit removes them; they are absent, not deleted.

---

## 6. Corrections this document makes to the existing record

| Existing claim | Correction | Evidence |
|---|---|---|
| `docs/audits/GIT-HISTORY-INTEGRITY.md:174-177`: redacted provenance is "unrecoverable" | Recoverable from `3b6d8798^` | `git show 3b6d8798^:<ledger>` |
| `docs/audits/GIT-HISTORY-INTEGRITY.md:82,170`: 2,541 files contain `REDACTED` | Measured: 3423 tracked files, 40581 occurrences; the cited supporting artifact is absent | `git grep` |
| `docs/audits/GIT-HISTORY-INTEGRITY.md:150`: absorption commit `f6ab4cdb` | Bad object; the commit is `f7ab4cdb` | `git cat-file -t f6ab4cdb` → fatal |
| `docs/audits/GIT-HISTORY-INTEGRITY.md:3`: 692 commits | 693 at HEAD `925ab5ce` | `git rev-list --count HEAD` |
| `docs/audits/GIT-HISTORY-INTEGRITY.md:148-155`: "the absorption commits … each is additive, well-titled, and scoped to its source project" | True for 8 of them; `33673213` and `121f79f6` are neither well-titled nor scoped (152 and 47 crate directories from unnamed sources), and `df365465` names a crate its diff does not contain | §1a #5, #6, #9 |
| `audits/absorption-justifications/Configra-2026-07-17.md:4`: `ARCHIVE_ONLY` | Git shows the 6-crate migration happened | `9b9275f0` |
| `audits/absorption-justifications/Stashly-2026-07-17.md`: `ARCHIVE_ONLY` failsafe | Same; `crates/stashly` exists | `121f79f6` |
| `docs/absorption/phenoData/README.md:32`: removed 5 stale `crates/pheno-data-from-phenoData/` artefacts | Still present, 14 files, and they are the only phenoData code in the repo | `175afc87` |
| `crates/phinbox/ABSORPTION.md` | Describes no absorption ("Code absorbed: None"); it is the only `crates/*/ABSORPTION.md` | file content, §2.2 |
| Coordinator's list of absorption commits | Incomplete: `9047e9dc`, `19f8e0eb`, `9f49359b`, `175afc87` are absorptions too | `git log --grep=absorb`, per-directory `--diff-filter=A` |
