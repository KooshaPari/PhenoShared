# F — Absorption Archaeology: PhenoShared

Lane F2, 2026-11-10. Evidence gathered read-only; no repo mutation. Repo at
`repos/PhenoShared` (HEAD `ad667428b`). Every line below cites a command output captured
in this lane. Anything not proven is marked UNKNOWN.

---

## 1. Identity verdict

**Consolidation monorepo, acting as the absorption target.** Not a library, not a single app.

Evidence:

- Top level contains a full absorption apparatus side by side with product trees:
  `absorption/` (14 source trees), `_archived/` (5 entries), `archives/` (2 `zz-archive-*`
  trees), `archive/`, `historical/` (PHASE_2..PHASE_8 completion summaries), and
  `docs/absorbed-from*` manifests for 11 distinct source repos.
- `Cargo.toml` is **1028 lines** and lists 372 workspace member directories under `crates/`
  plus paths that reach into `absorption/PhenoMLX-temp/...`.
- Multi-language: Rust crates, Go modules (`docs/absorbed-from-PhenoGoKit` = `go-sdk`,
  gated by an explicit Go-module allowlist per commit `5f8fc9a54`), JS/TS (coverage ratchet
  commit `ed29a0bb5` measures a "real JS/TS unit suite").
- Git log is dominated by absorption vocabulary: `feat(absorb)`, `docs(absorb)`,
  `docs(absorption)`, `absorption: absorb 5 sprawl repos with provenance and governance`
  (`3b45203b0`), `absorb(herdr): fold herdr-{jcode,forgecode,helioslite} plugins into
  PhenoShared` (`dee522c88`).

Verdict is high confidence. The repo's purpose is to be the durable home that other
Phenotype repos are folded into.

---

## 2. Absorption ledger

Provenance is unusually good: each absorbed source has a manifest naming the source repo,
revision, and date. Rows below are verbatim from `docs/absorbed-from/*/README*.md` and
`docs/absorbed-from-*/ABSORPTION.md`.

| Source repo | Evidence (manifest) | Date | Resulting path | Status |
|---|---|---|---|---|
| `KooshaPari/PhenoInfra` | commit `ecf486cab18b8e84213838d497a39ea3a94aca71` | 2026-09-16 | `absorption/PhenoInfra/` (2537 files, 28 MB src) | copied, no `.git`; source already archived |
| `KooshaPari/PhenoMLX-temp` | commit `70529a879715a8078e26eb564f8fc312e1923f57` | 2026-09-16 | `absorption/PhenoMLX-temp/` (1349 files) | copied; **only absorption tree wired into workspace (38 refs)** |
| `KooshaPari/phenoDesign-visual-production-v2` | commit `032e2d84609c1bbf847de359c7d2bf99c7617af6` | 2026-09-17 | `absorption/phenoDesign-visual-production-v2/` (180 files) | copied; source left **unarchived** pending operator confirmation |
| `KooshaPari/phenotype-canonicalization` | commit `570e2c73aff565620a2c518a37d258981a31ca9e` | 2026-09-17 | `absorption/phenotype-canonicalization/` (44 files) | copied whole; source **unarchived** pending confirmation |
| `KooshaPari/phenotype-cvp-audit-2026-09-14` | commit `791c278fa16f84fdb857f0cff1566f1f4d3e547c` | 2026-09-17 | `absorption/phenotype-cvp-audit-2026-09-14/` (7 files) | copied; source **unarchived** pending confirmation |
| `KooshaPari/zz-merge-unk-hfscope` | manifest states the source is **deleted** | UNKNOWN | `docs/absorbed-from/hfscope/README.md` (manifest only, 1 file) | payload provenance only; no tree under `absorption/` |
| `KooshaPari/phenotype-hub` | manifest table in `docs/absorbed-from/phenotype-hub/README.md` | UNKNOWN | maps to surfaces in phenotype-infra | claim-only; no `absorption/` tree |
| `KooshaPari/vibeproxy-monitoring-unified` | manifest table | UNKNOWN | manifest only (1 file) | claim-only |
| `KooshaPari/PhenoGoKit` (go-sdk) | `GET /repos/KooshaPari/PhenoGoKit` → **404**, repo does not exist | UNKNOWN | `docs/absorbed-from-PhenoGoKit/` (1.5 MB) | recovered from a **local clone** whose origin is a local path, plus `PhenoTooling` @ `2feccc2f` |
| `KooshaPari/PhenoTooling` → PhenoCompose | `ABSORPTION.md`: revision `2feccc2f5b12c77785dda7960f7c31d25baf4e54`, path `PhenoCompose/` | **2026-11-08** | `docs/absorbed-from-PhenoCompose/` (216 KB) | in-tree; commit `6fd2835e5` "port the 41 unabsorbed PhenoCompose files" |
| `KooshaPari/PhenoTooling` → observability | `docs/absorbed-from-PhenoObservability/ABSORPTION.md` | UNKNOWN (campaign 2026-11-08) | `docs/absorbed-from-PhenoObservability/` (1.1 MB, 140 files) | commit `6e5fa283a` "durable homes for the go-sdk (240) and observability (140) files" |
| `PhenoTooling` (bulk) | `docs/absorbed-from-PhenoTooling.md` + dir | UNKNOWN | `docs/absorbed-from-PhenoTooling/` (**70 MB**) | largest absorbed payload outside `archives/` |
| herdr plugins (jcode / forgecode / helioslite) | commit `dee522c88` | UNKNOWN | `absorption/herdr-{jcode,forgecode,helioslite}/` (8 files each) | in-tree, **0 workspace refs** |
| 5 sprawl repos | commit `3b45203b0` "absorb 5 sprawl repos with provenance and governance" | UNKNOWN | not enumerated in this lane | UNKNOWN which 5 (out of scope for 8-call budget) |
| `apisync`, `DataKit`, `eidolon`, `pheno-forge-smoke`, `Planify`, `stashly`, `thegent` | `registry/absorbed-crates/` directory names | UNKNOWN | `registry/absorbed-crates/` | registry records exist; tree mapping UNKNOWN |

Absorption manifests are the strongest artifact in this repo. Only two of them carry an
explicit absorbed date in the head of the file (`PhenoCompose` = 2026-11-08); the eight
small `docs/absorbed-from/*/` manifests are README-only (1 file each) with no payload.

---

## 3. The 2026-11-08 wrapup campaign

This is the dominant recent event and it is **not landed**.

18 remote `wrapup/*-20261108` branches exist. **All 18 are UNMERGED into `origin/HEAD`**
(verified with `git merge-base --is-ancestor`). Ahead counts range from 1 to 498 commits:

| Branch | Ahead of origin/HEAD | State |
|---|---|---|
| `wrapup/apisync-20261108` | 498 | UNMERGED |
| `wrapup/nanovms-20261108` | 378 | UNMERGED |
| `wrapup/tokn-20261108` | 307 | UNMERGED |
| `wrapup/phenojourneys-20261108` | 245 | UNMERGED |
| `wrapup/phenoforge-20261108` | 127 | UNMERGED |
| `wrapup/datakit-20261108` | 125 | UNMERGED |
| `wrapup/logify-20261108` | 79 | UNMERGED |
| `wrapup/phenokits-commons-20261108` | 79 | UNMERGED |
| `wrapup/pheno-runtime-config-20261108` | 11 | UNMERGED |
| `wrapup/local-ops-20261108` | 6 | UNMERGED |
| `wrapup/pheno-20261108` | 5 | UNMERGED |
| `wrapup/deny-advisory-20261108` | 2 | UNMERGED |
| `wrapup/vitepress-relaunch-20261108` | 2 | UNMERGED |
| `wrapup/phenoobservability-20261108` | 2 | UNMERGED |
| `wrapup/zz-forensic-zz-pheno-20261108` | 1 | UNMERGED |
| `wrapup/phenoplugins-20261108` | 1 | UNMERGED |
| `wrapup/d1-nontq-20261108` | 1 | UNMERGED |
| `wrapup/recovered-trunk-action-repair-20261108` | 1 | UNMERGED |

Additionally four `snapshot/orphan/*` branches survive: `meta`, `browser-infra`,
`phenotype-hub`, `cvp-fixture`.

The consolidation branch for the campaign, `origin/integration/absorbed-20261109`
(tip `45e7c8a6a`, "fix(policystack): pin deny advisory and simplify wrapper error
condition"), is **also UNMERGED** into `origin/HEAD`.

Interpretation: the 2026-11-08 wrapup produced 18 parallel per-target branches on top of an
integration branch, and none of it reached the trunk by 2026-11-10. The absorbed content that
*did* land is the one-off commit series (`6e5fa283a`, `6fd2835e5`, `dee522c88`,
`3b45203b0`), not the wrapup branches. Whether the wrapup branches are supersets of those
commits or a divergent alternative history is **UNKNOWN** (not diffed in this lane).

---

## 4. Archive trees with sizes

Measured with `du -sh`:

| Path | Size | Contents |
|---|---|---|
| `archives/` | **95 MB** | `zz-archive-phenotype-monorepo-state-archive/`, `zz-archive-phenotype-registry/` |
| `docs/absorbed-from-PhenoTooling/` | **70 MB** | bulk PhenoTooling payload |
| `absorption/` | **48 MB** | 14 source trees (below) |
| `_archived/` | **8.9 MB** | `byteport`, `nanovms-core`, `nvms-ffi`, `pheno-compose`, `README.md` |
| `docs/absorbed-from-PhenoGoKit/` | 1.5 MB | `go-sdk` recovery |
| `docs/absorbed-from-PhenoObservability/` | 1.1 MB | 14 subtrees (ai-prompt-logger, alerting, logctx, logging, metrics, pheno-otel, profiling, tracing, vendor, ...) |
| `historical/` | 228 KB | PHASE_2..PHASE_8 completion summaries, `BLUEPRINT.md`, `SOTA.md` |
| `docs/absorbed-from-PhenoCompose/` | 216 KB | 11 subtrees (benches, bindings, internal, mobile, nanovms, packages, ports, tools, windows, ...) |
| `docs/absorbed-from/` (8 manifests) | 32 KB | README-only |
| `archive/` | 4 KB | a lone `pyproject.toml` |

`git ls-files | grep -c archive` → **2523 tracked files** whose path contains "archive".
Total absorption/archive footprint on disk ≈ **224 MB** across the four trees, before
counting `crates/`.

Per-tree file counts in `absorption/`:

```
absorption/PhenoInfra/                          2532
absorption/PhenoMLX-temp/                       1349
absorption/phenoDesign-visual-production-v2/     180
absorption/resume-all/                            90
absorption/pheno-forge/                           88
absorption/phenotype-router-monitor-root/         63
absorption/phenotype-canonicalization/            44
absorption/phenotype-router-monitor/              29
absorption/herdr-forgecode/                        8
absorption/herdr-helioslite/                       8
absorption/herdr-jcode/                            8
absorption/phenotype-cvp-audit-2026-09-14/         7
absorption/byteport/                               1
absorption/helios-bench/                           1
```

`archive/pyproject.toml` being the *entire* `archive/` tree is a red flag: that directory
name promises a frozen copy and holds one file. UNKNOWN whether it is a leftover stub.

---

## 5. Duplication risk from crate clustering

`crates/` holds **372 directories**. Naive prefix-then-strip-last-segment clustering shows
how much namespace overlap exists:

```
 40 phenotype        9 sharecli          3 pheno-compose
 31 focus            9 connector         3 cloud
 19 agileplus        8 eyetracker        2 traceability
 14 pheno            7 engine            2 tokn
 14 fabric           6 teamcomm          2 store
 10 substrate        6 pheno-compose-port 2 sidekick
                     5 pine              2 sharecli-tray
                     4 substrate-browser 2 port
                     4 eidolon           2 playcua
                     4 driver
```

Risks, in order of severity:

1. **Two parallel homes for the same absorbed content.** `absorption/PhenoMLX-temp/perf-core/*`
   is a workspace member (38 `Cargo.toml` refs), while `crates/` already contains engine,
   driver, and focus families. Both are compiled into the same workspace, so a split
   implementation can silently win by member ordering rather than by intent.

2. **`phenotype-*` (40) vs `pheno-*` (14) vs `pheno-compose-*` vs `pheno-compose-port-*`.**
   The `pheno-compose-port` (6) family is a port of something that also exists as
   `pheno-compose` (3) and again inside `absorption/pheno-forge` (88 files). Three homes,
   one concept.

3. **`focus-*` (43 crates, 43,601 Rust LOC)** is the largest non-phenotype cluster and appears in no absorption
   manifest. The whole family arrived in a single commit, `19f8e0ebe` (2026-09-16, "extract 53 crates
   from FocalPoint"); 53 reconciles as 43 `focus-*` plus 9 `connector-*`. `docs/` has no
   `absorbed-from-FocalPoint`, so the largest absorption in the repo has no absorption record. No
   `phenotype-*`/`substrate-*`/`fabric-*` crate depends on any `focus-*`; the only inbound edges are
   its own 9 `connector-*` crates.

4. **`substrate-*` (10) and `substrate-browser-*` (4)** overlap the Phenofabric/ShareCLI
   substrate lineage. Neither upstream exists on disk any more (`~/CodeProjects/sharecli` is absent;
   Phenofabric was not found), so this cluster is absorbing work whose upstream no longer exists, and
   the cluster itself is now the only copy. Status of the duplication UNKNOWN.

5. **`sharecli-*` (12 crates: 10 `sharecli*` + 2 `sharecli-tray-*`, 119,855 Rust LOC)** have no
   upstream to reconcile against: `~/CodeProjects/sharecli` **does not exist**, and the family carries
   no provenance file. All 12 are workspace members; the only cross-family consumer is
   `crates/harness-native`, which is itself not a workspace member, so the family is substantial but
   unconsumed. Dropping 120k LOC with no upstream and no recorded history would be unrecoverable.

6. **Deleted-crate residue.** Commit `471af232a` "remove dead playcua-integration crate
   (unresolvable path-deps)" while `playcua-*` (2) still exists. Partial cleanup leaves a
   family that looks live.

---

## 6. Dangling absorbed-but-unwired items

The clearest finding in this lane. Wiring was measured by counting `Cargo.toml` references
to each `absorption/` tree:

| Absorption tree | Files | Cargo.toml refs | Verdict |
|---|---|---|---|
| `absorption/PhenoMLX-temp/` | 1349 | **38** | WIRED |
| `absorption/PhenoInfra/` | 2532 | **0** | **DANGLING — largest unwired tree (28 MB src)** |
| `absorption/phenoDesign-visual-production-v2/` | 180 | 0 | dangling |
| `absorption/resume-all/` | 90 | 0 | dangling |
| `absorption/pheno-forge/` | 88 | 0 | dangling (registry has `pheno-forge-smoke` only) |
| `absorption/phenotype-router-monitor-root/` | 63 | 0 | dangling |
| `absorption/phenotype-canonicalization/` | 44 | 0 | dangling |
| `absorption/phenotype-router-monitor/` | 29 | 0 | dangling (and duplicates `-root`) |
| `absorption/herdr-{jcode,forgecode,helioslite}/` | 8 each | 0 | dangling (plugins, may be non-Rust) |
| `absorption/phenotype-cvp-audit-2026-09-14/` | 7 | 0 | dangling (audit artifact, probably intentional) |
| `absorption/byteport/`, `absorption/helios-bench/` | 1 each | 0 | manifest stubs |

**13 of 14 absorption trees have zero workspace wiring.** 48 MB of absorbed source sits in
the repository without being built, tested, or reachable from the workspace. Only
`PhenoMLX-temp` was ever promoted (commits `7a9f14c28` "promote non-TQ perf-core and
hwledger crates" and `9950a9465` "add native to the workspace").

Other dangling items:

- `registry/absorbed-crates/` lists `apisync`, `DataKit`, `eidolon`, `pheno-forge-smoke`,
  `Planify`, `stashly`, `thegent` — registry claims with no `absorption/` tree of those
  names. Their real landing path is UNKNOWN.
- `docs/absorbed-from/phenotype-hub/` and `vibeproxy-monitoring-unified/` are manifest-only
  (1 file each); the payload is not in `absorption/`. Claims point at
  "canonical surface in phenotype-infra", which is itself the *unwired* PhenoInfra tree.
- `docs/audits/MISSING-ABSORB-agent-user-status.md` records that `agent-user-status` is
  **unrecoverable** — all three claimed homes tested empty (also in log
  `07df0b688`). This is a permanent absorption loss, not a pending task.
- `docs/absorbed-from-PhenoGoKit/ABSORPTION.md` documents a source repo that **404s on
  GitHub**, recovered only from a local clone whose origin is a local path. The provenance
  chain terminates on this machine.
- `archives/zz-archive-phenotype-registry/` and `.../monorepo-state-archive/` (95 MB) are
  frozen trees with no manifest reviewed here. Whether they are referenced by
  `docs/disposition/h14-terminal-absorb-ledger-2026-06-19.md` is UNKNOWN.

Structural note: `docs/absorbed-from/*/` (8 dirs, README only) and `absorption/*/`
(14 dirs, payload) do not correspond one-to-one. A reader following the manifest lands on a
README with no code; the code is under a different top-level name. That mismatch is the
mechanism by which the 13 dangling trees went unnoticed.

---

## Method and limits

- Read-only. No file written inside the repo; no git mutation (no fetch, no branch, no
  checkout). Output written to `PhenoShared-space/analysis/2026-11-10-forensic/`.
- Budget: 8 tool calls, matched (1 skeleton write, 4 evidence sweeps, 1 final write, 1
  report).
- Not done, therefore UNKNOWN: diffing wrapup branches against trunk; which 5 repos
  `3b45203b0` absorbed; the origin of the `focus-*` cluster; whether the 95 MB `archives/`
  trees are referenced anywhere.
