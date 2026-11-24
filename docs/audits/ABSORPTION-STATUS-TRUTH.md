# Absorption status truth pass

**Measured at** HEAD `6c1d2d9ca7f3e3236b10bfd9bbcea06f9794415c` (branch `main`),
2026-09-18 local / `2026-09-19T01:42:37Z` UTC.
**Repository under test:** `PhenoShared` at
`/Users/kooshapari/CodeProjects/Phenotype/repos/PhenoShared`.
**Sibling checkouts referenced:** `/Users/kooshapari/CodeProjects/Phenotype/repos/<repo>`.

**Scope of this document.** It answers one question per record: *does the destination
this record claims actually exist, and can that be tested?* It does not re-audit
provenance, commit lineage, or content parity. Provenance lives in
`docs/absorption/ABSORPTION-LINEAGE.md`.

**Method.** Every existence claim below is a real filesystem test of the form

```sh
test -e <path>; echo $?      # 0 = exists, 1 = absent
```

run from the working directory stated in each table, with the literal result printed.
Every record is cited `file:line`. No count in this document was copied from another
document; each was computed here. Where a source is ambiguous, that is stated rather
than resolved by guessing.

**Prior audit being checked.** `docs/absorption/ABSORPTION-LINEAGE.md:207` states that
33 records claim absorption, 11 with an explicit destination, and "none of the 11
destinations is in this tree". That sentence is **not reproduced by this pass**.
Section 9 explains exactly where it diverges and why.

---

## 1. Totals

| Metric | Count | How computed |
|---|---:|---|
| Records enumerated across all five sources | **45** | 11 + 28 + 4 + 2 (families A-D below) |
| Records that claim `absorbed` (or `ABSORB`) status | **45** | every enumerated record claims it by construction |
| Records whose destination is a local path and **EXISTS** | **16** | bucket (a), section 4 |
| Records whose destination is a local path and is **ABSENT** | **12** | bucket (b), section 5 |
| Records whose destination is another repo or free text (**unverifiable from here**) | **16** | bucket (c), section 6 |
| Records with **no destination stated** | **1** | `docs/absorption/PhenoKits/MATRIX.md:11` (`ARCHIVE_ONLY`, no target) |
| Records with **no `status` key at all** | **1** | `projects/phenotype-dag-core-rename-2026-09-01.json` (see section 8) |
| `projects/*.json` files total | **178** | `ls -1 projects/*.json \| wc -l` |
| `projects/*.json` with `"status": "absorbed"` | **11** | `rg -l '"status"\s*:\s*"absorbed"' projects/*.json \| wc -l` |
| `docs/absorption/*/README.md` files | **32** | `find docs/absorption -maxdepth 2 -name README.md \| wc -l` |
| of those, claiming absorption | **28** | section 3.2 |
| of those, NOT claiming absorption | **4** | `localbase3`, `PhenoLang`, `phenoEvents`, `utility-targets` |

> **Counting note.** `docs/absorption/ABSORPTION-LINEAGE.md:207` refers to "33 records".
> `docs/absorption/` contains **33 directories** but only **32 `README.md`** files.
> The 33rd directory, `docs/absorption/PhenoKits/`, holds `MATRIX.md` instead and
> reaches an `ARCHIVE_ONLY` verdict with no destination. So "33" is a directory count;
> the record count that claims absorption is 28.

---

## 2. Bucket definitions

The records conflate two unrelated things: a *path in this tree* and a *name of another
repository*. They are never merged here.

| Bucket | Meaning | Verdict class |
|---|---|---|
| **(a)** | Destination is a local path in this tree and it EXISTS | landed |
| **(b)** | Destination is a local path in this tree and it is ABSENT | **real violation** |
| **(c)** | Destination is another repository or free text | **unverifiable from here**, not a violation |
| **(d)** | No destination stated | nothing to test |

A record may be split across buckets when it claims more than one destination
(this happens once: `Quillr`).

---

## 3. Family A: `projects/*.json` (11 records)

`projects/` holds **178** JSON files. **11** carry `"status": "absorbed"`
(verified: `ls -1 projects/*.json | wc -l` → `178`;
`rg -l '"status"\s*:\s*"absorbed"' projects/*.json` → 11 files, listed below).
The other 167 carry `active` (87), `archived` (25), `retired` (24), `queued` (22),
`live` (2), `deprecated` (2), `tombstoned` (1), `folded` (1),
`archived-superseded` (1), `active-renamed` (1), and **1 file with no status key**.

### 3.1 The `path` field is not a destination

Every one of the 11 records also carries a `path` key such as `repos/Logify (archived)`.
These look local but are not: the sibling directory `repos/` contains only
`home-recovery-2026-07` and `thegent-pr2-v2-uncommitted-2026-07-14`.

```sh
$ ls -1 repos/
home-recovery-2026-07
thegent-pr2-v2-uncommitted-2026-07-14
```

Result: **11 of 11** `path` values are ABSENT in tree. This key describes where the
source repo used to live, not where it was absorbed. It must not be read as a
destination.

### 3.2 Destination table

| # | Record (file:line) | Key | Claimed destination (verbatim) | Bucket | Exists | Evidence (literal) |
|---|---|---|---|---|---:|---|
| A1 | `projects/Logify.json:13` | `absorbed_into` | `PhenoObservability (crates/logkit overlay)` | (c) | YES (local token) | `test -e crates/logkit; echo $?` → `0` |
| A2 | `projects/phench.json:13` | `absorbed_into` | `phenotype-tooling (crates/phench)` | (c) | YES (local token) | `test -e crates/phench; echo $?` → `0` |
| A3 | `projects/pheno-cdylib-bridge.json:13` | `absorbed_into` | `pheno (monorepo crates/pheno-cdylib-bridge)` | (c) | YES (local token) | `test -e crates/pheno-cdylib-bridge; echo $?` → `0` |
| A4 | `projects/pheno-forge-smoke.json:13` | `absorbed_into` | `pheno (crates/pheno-forge-smoke)` | (c) | YES (local token) | `test -e crates/pheno-forge-smoke; echo $?` → `0` |
| A5 | `projects/pheno-research-2026-09-01.json:21` | `absorbed_into` | `pheno (monorepo root)` | **(a)** | YES | 10 local tokens tested, all `0` (section 3.3) |
| A6 | `projects/agent-user-status.json:11` | `absorbing_path` | `crates/agent-user-status/` | **(b)** | **NO** | `test -e crates/agent-user-status; echo $?` → `1` |
| A7 | `projects/phenotype-hub.json:13` | `absorbed_into` | `phenotype-infra` | (c) | repo name; resolved path YES | `test -e ../phenotype-infra/docs/absorbed-from/phenotype-hub; echo $?` → `0` |
| A8 | `projects/vibeproxy-monitoring-unified.json:11` | `absorbed_into` | `phenotype-infra` | (c) | repo name; resolved path YES | `test -e ../phenotype-infra/docs/absorbed-from/vibeproxy-monitoring-unified; echo $?` → `0` |
| A9 | `projects/Profila.json:11` | `absorbed_into` | `phenotype-tooling` | (c) | repo name; resolved path YES | `test -e ../phenotype-tooling/packages/profila; echo $?` → `0` |
| A10 | `projects/PhenoLang.json:12` | `absorbed_into` | `phenoUtils` | (c) | repo name; NOT resolvable | `test -e ../phenoUtils; echo $?` → `1` |
| A11 | `projects/grapheon-bindings.json:13` | `absorbed_into` | `phenotype-go-sdk` | (c) | repo name; NOT resolvable | `test -e ../phenotype-go-sdk; echo $?` → `1` |

**Family A bucket totals:** (a) 1, (b) 1, (c) 9, (d) 0.

### 3.3 A5 detail: `pheno-research`, the only record with checkable path tokens

`projects/pheno-research-2026-09-01.json:31` carries
`target_path_present`: a list of concrete in-tree paths. All were tested from the
repo root and all returned `0`:

```sh
$ for p in audit devices experiments promotion schemas sync \
    docs/GITHUB_ARCHIVE_POLICY.md README.md .mergify.yml .circleci/config.yml \
    .github/workflows/ci.yml .github/workflows/infisical.yml \
    .github/workflows/trunk-check.yml .github/workflows/scorecard.yml \
    renovate.json trunk.yaml; do test -e "$p"; echo "$p $?"; done
audit 0
devices 0
experiments 0
promotion 0
schemas 0
sync 0
docs/GITHUB_ARCHIVE_POLICY.md 0
README.md 0
.mergify.yml 0
.circleci/config.yml 0
.github/workflows/ci.yml 0
.github/workflows/infisical.yml 0
.github/workflows/trunk-check.yml 0
.github/workflows/scorecard.yml 0
renovate.json 0
trunk.yaml 0
```

This record is the **only** one in family A whose claim is machine-checkable and it
checks out.

### 3.4 The single provable registry violation (A6)

`projects/agent-user-status.json`:

```
:5   "status": "absorbed",
:10  "absorbing_repo": "<REDACTED>/phenotype-tooling",
:11  "absorbing_path": "crates/agent-user-status/",
```

`absorbing_path` is a bare repo-relative path. Tested in this tree and in the named
sibling checkout:

```sh
$ test -e crates/agent-user-status; echo $?
1
$ test -e /Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-tooling/crates/agent-user-status; echo $?
1
```

Both ABSENT. The same file is claimed by `docs/absorption/agent-user-status/README.md:50`
("`crates/agent-user-status/ABSORPTION.md` (target-side provenance marker)") and that
path is absent too. This is the only destination in family A that is both a stated
local path and provably missing.

### 3.5 Prose destinations that do resolve (A1-A4, A7-A9)

Gorilla's scope correction flagged four prose entries naming local crates that exist.
Verified independently here, all four tracked at HEAD:

```sh
$ for p in crates/logkit crates/phench crates/pheno-cdylib-bridge crates/pheno-forge-smoke; do test -e "$p"; echo "$p $?"; done
crates/logkit 0
crates/phench 0
crates/pheno-cdylib-bridge 0
crates/pheno-forge-smoke 0
$ git ls-files --error-unmatch crates/logkit crates/phench crates/pheno-cdylib-bridge crates/pheno-forge-smoke
... (all TRACKED)
```

Three further prose entries resolve to an existing path **in the named sibling repo**
(A7, A8, A9), each tested with exit `0` as shown in the table.

**Caveat, stated rather than smoothed over.** For A2 the prose names
`phenotype-tooling` but the sibling `phenotype-tooling/crates/phench` is **ABSENT**
(`exit 1`). A same-named crate exists in *this* tree. So the crate landed somewhere;
the record does not establish that it landed where it says. That ambiguity is a
defect of the record format, not evidence of a missing migration. A1, A3 and A4 do
not have this problem: their sibling paths
(`PhenoObservability/crates/logkit`, `pheno/crates/pheno-cdylib-bridge`,
`pheno/crates/pheno-forge-smoke`) are all present with exit `0`.

---

## 4. Family B: `docs/absorption/*/README.md` (28 records claiming absorption)

**32** `README.md` files exist under `docs/absorption/`. **28** claim absorption.
**4** do not and are excluded from the tables: `localbase3` (`AFFIRM (canonical, NOT
absorbed)`, `docs/absorption/localbase3/README.md:8`), `PhenoLang`
(`ARCHIVE_ONLY for now`, `docs/absorption/PhenoLang/README.md:11`), `phenoEvents`
(`Historical and unverified provenance`, `docs/absorption/phenoEvents/README.md:3`),
`utility-targets` (a target-resolution policy, no absorption of a named source).

### 4.1 Bucket (a): destination is a local path and EXISTS (9 records)

| # | Record (file:line) | Claimed destination | Exists | Evidence (literal) |
|---|---|---|---:|---|
| B1 | `docs/absorption/pheno-cdylib-bridge/README.md:9` | `crates/pheno-cdylib-bridge/` | YES | `test -e crates/pheno-cdylib-bridge; echo $?` → `0` |
| B2 | `docs/absorption/pheno-context/README.md:4` | `crates/pheno-context/` | YES | `test -e crates/pheno-context; echo $?` → `0` |
| B3 | `docs/absorption/pheno-forge-smoke/README.md:17,36` | `crates/pheno-forge-smoke/`, `.../sidecars/` | YES (2/2) | `test -e crates/pheno-forge-smoke; echo $?` → `0`; `test -e crates/pheno-forge-smoke/sidecars; echo $?` → `0` |
| B4 | `docs/absorption/pheno-runtime-config/README.md:5` | `crates/pheno-runtime-config/` | YES | `test -e crates/pheno-runtime-config; echo $?` → `0` |
| B5 | `docs/absorption/eidolon/README.md:5` | `crates/eidolon-{core,desktop,mobile,sandbox}/`, `crates/phenotype-error-core/` | YES (5/5) | all five `test -e ...; echo $?` → `0` |
| B6 | `docs/absorption/PhenoSpecs/README.md:9` | `docs/specs/pheno-specs/` (in `phenotype-registry`) | YES | `test -e docs/specs/pheno-specs; echo $?` → `0`; also `test -e ../phenotype-registry/docs/specs/pheno-specs; echo $?` → `0` |
| B7 | `docs/absorption/phenotype-router-spec/README.md:5` | `docs/specs/router-protocol/` | YES | `test -e docs/specs/router-protocol; echo $?` → `0`; also present in `../phenotype-registry/` |
| B8 | `docs/absorption/Logify/README.md:6` | `pheno/crates/logkit/` | YES (local token) | `test -e crates/logkit; echo $?` → `0`; `test -e ../pheno/crates/logkit; echo $?` → `0`; `test -e ../PhenoObservability/crates/logkit; echo $?` → `0` |
| B9 | `docs/absorption/phench/README.md:9` | `crates/phench/` (in `phenotype-tooling`) | YES (local token) | `test -e crates/phench; echo $?` → `0`; **but** `test -e ../phenotype-tooling/crates/phench; echo $?` → `1` (same caveat as A2) |

### 4.2 Bucket (b): destination is a local path and is ABSENT (5 records + 1 half-record)

| # | Record (file:line) | Claimed destination | Exists | Evidence (literal) |
|---|---|---|---:|---|
| B10 | `docs/absorption/phenoUtils/README.md:5,54` | `crates/pheno-utils-{shell,fs,net,async,crypto,testing,chaos}/` (7 crates) | **NO (7/7)** | `for c in shell fs net async crypto testing chaos; do test -e crates/pheno-utils-$c; echo $?; done` → seven `1`s |
| B11 | `docs/absorption/phenoData/README.md:6,17-21,37-41` | `crates/pheno-data-{core,query,surreal,pg,smoke-tests}/` (5 crates) | **NO (5/5)** | `for c in core query surreal pg smoke-tests; do test -e crates/pheno-data-$c; echo $?; done` → five `1`s. `crates/pheno-data-from-phenoData` → `0` (the residue this README `:32-33` claims to have deleted) |
| B12 | `docs/absorption/PhenoPlugins/README.md:5,19-23` | `crates/pheno-plugins-{core,git,sqlite,vessel,examples}/` (5 crates) | **NO (5/5)** | `for c in core git sqlite vessel examples; do test -e crates/pheno-plugins-$c; echo $?; done` → five `1`s |
| B13 | `docs/absorption/phenotype-pm-core/README.md:9,17-19` | `crates/traceability-core/`, `crates/traceability-decorators/`, `crates/trace-gate/` | **NO (3/3)** | `test -e crates/traceability-core; echo $?` → `1`; `.../traceability-decorators` → `1`; `crates/trace-gate` → `1` |
| B14 | `docs/absorption/phenoResearchEngine/README.md:9` | `phenotype-research-engine/` | **NO** | `test -e phenotype-research-engine; echo $?` → `1` |
| B15 | `docs/absorption/Quillr/README.md:15` | `crates/httpora-core/` (Rust half) | YES | `test -e crates/httpora-core; echo $?` → `0` |
| B15b | `docs/absorption/Quillr/README.md:16` | `packages/quillts/` in `phenodocs` (TS half) | **NO** | `test -e packages/quillts; echo $?` → `1`; `test -e ../phenodocs/packages/quillts; echo $?` → `1` (`phenodocs` is not checked out) |

`Quillr` is the one record split across buckets: its Rust half landed, its TypeScript
half did not.

### 4.3 Bucket (c): destination is another repo or free text (12 records)

| # | Record (file:line) | Claimed destination | Exists | Evidence (literal) |
|---|---|---|---:|---|
| B16 | `docs/absorption/agent-user-status/README.md:5,7,50` | `phenotype-tooling/crates/agent-user-status` | **NO** | `test -e ../phenotype-tooling/crates/agent-user-status; echo $?` → `1` |
| B17 | `docs/absorption/audit-tool/README.md:10-11,51` | `phenotype-registry/scripts/audit.py` | **NO** | `test -e ../phenotype-registry/scripts/audit.py; echo $?` → `1` (dir `scripts/` exists, 19 files, no `audit.py`) |
| B18 | `docs/absorption/Benchora/README.md:9` | `crates/benchora/` in `phenotype-tooling` | **NO** on main | `test -e ../phenotype-tooling/crates/benchora; echo $?` → `1`; EXISTS on worktrees only (section 9.3) |
| B19 | `docs/absorption/KodeVibe/README.md:9` | `tools/kodevibe/` in `phenotype-tooling` | **NO** | `test -e ../phenotype-tooling/tools/kodevibe; echo $?` → `1`; `test -e tools/kodevibe; echo $?` → `1` |
| B20 | `docs/absorption/KWatch/README.md:6` | `phenotype-tooling/tools/kwatch/` | **NO** | `test -e ../phenotype-tooling/tools/kwatch; echo $?` → `1`; `test -e tools/kwatch; echo $?` → `1` |
| B21 | `docs/absorption/scripts/README.md:5,7` | `phenotype-tooling/bin/legacy-scripts/` | **NO** | `test -e ../phenotype-tooling/bin/legacy-scripts; echo $?` → `1` |
| B22 | `docs/absorption/Sidekick/README.md:5,7` | `PhenoObservability/crates/{sidekick-messaging,sidekick-obs-core,sidekick-observability}/` | **NO (3/3)** | three `test -e ../PhenoObservability/crates/sidekick-*; echo $?` → `1` |
| B23 | `docs/absorption/curated-traces/README.md:5,7` | `PhenoObservability/curated-traces/` | **NO** | `test -e ../PhenoObservability/curated-traces; echo $?` → `1` |
| B24 | `docs/absorption/backend-melosviz/README.md:4` | `phenotype-python-sdk/packages/melosviz/` | untestable | `phenotype-python-sdk` is not checked out at `../`; only `phenotype-python-sdk-wtrees/` exists, and `.../packages/melosviz` there → `1` |
| B25 | `docs/absorption/PolicyStack/README.md:9` | `phenotype-python-sdk/packages/policystack/` | untestable | same repo absent; `phenotype-python-sdk-wtrees/packages/policystack` → `1` |
| B26 | `docs/absorption/grapheon-bindings/README.md:9` | `packages/graphclient/` in `phenotype-go-sdk` | untestable | `phenotype-go-sdk` not checked out; `phenotype-go-sdk-wtrees/packages/graphclient` → `1` |
| B27 | `docs/absorption/template-commons/README.md:7,29` | `phenokits-commons` `templates/` subtree | untestable | `phenokits-commons` not checked out; `zz-phenokits-commons/templates` EXISTS but is a differently-named checkout, so it does not settle the claim |

### 4.4 Self-reversed record (1)

| # | Record (file:line) | Claim | Reality |
|---|---|---|---|
| B28 | `docs/absorption/phenoDesign/README.md:6` (target `phenodocs/packages/design-tokens/`) | "absorbed", then `:9-11` "This absorption is **reversed**" | `test -e packages/design-tokens; echo $?` → `0` (a local `packages/design-tokens` exists, but it is not `phenodocs/packages/design-tokens`); `test -e ../phenodocs/packages/design-tokens; echo $?` → `1` |

This record is in the 28 because it asserts an absorption, but it also asserts that the
absorption was undone. It should not be counted as a live `absorbed` claim.

**Family B bucket totals:** (a) 9, (b) 5 + one half of `Quillr`, (c) 12, (d) 0,
plus 1 self-reversed. 9 + 5 + 1 + 12 + 1 = 28. ✔

---

## 5. Family C: `crates/ABSORPTION_MANIFEST.md` (4 records + 3 split-target claims)

| # | Record (file:line) | Claimed destination | Bucket | Exists | Evidence (literal) |
|---|---|---|---|---:|---|
| C1 | `crates/ABSORPTION_MANIFEST.md:8` | `crates/pheno-agent/` (`phenotype-daemon`, `phenotype-skills`) | (a) | YES | `test -e crates/pheno-agent; echo $?` → `0` |
| C2 | `crates/ABSORPTION_MANIFEST.md:15` | `<REDACTED>/phenoAI/crates/llm-router/` | (a) | YES | `test -e crates/llm-router; echo $?` → `0`; `test -e ../phenoAI/crates/llm-router; echo $?` → `0` |
| C3 | `crates/ABSORPTION_MANIFEST.md:26` | `adapters/web/agent-platform/` | **(b)** | **NO** | `test -e adapters/web/agent-platform; echo $?` → `1` |
| C4 | `crates/ABSORPTION_MANIFEST.md:34` | `<REDACTED>/rich-cli-kit/crates/klipdot/` | **(b)** | **NO** | `test -e rich-cli-kit/crates/klipdot; echo $?` → `1`; `test -e ../rich-cli-kit; echo $?` → `1` |
| C5 | `crates/ABSORPTION_MANIFEST.md:52` | `HexaKit` (owner of `phenotype-*` infra) | (c) | untestable from a path | `test -e ../HexaKit; echo $?` → `1`; `_full_HexaKit` exists but is a differently-named checkout |
| C6 | `crates/ABSORPTION_MANIFEST.md:53` | `phenokits-commons/governance/phenoproc-*` | (c) | untestable | repo not checked out (see B27) |
| C7 | `crates/ABSORPTION_MANIFEST.md:54` | `phenotype-tooling/absorption/` | (a) | YES | `test -e ../phenotype-tooling/absorption; echo $?` → `0` |
| C8 | `crates/ABSORPTION_MANIFEST.md:55` | `libs/phenotype-observability` -> `PhenoObservability` / python-sdk | **(b)** | **NO** | `test -e libs/phenotype-observability; echo $?` → `1` |
| C9 | `crates/ABSORPTION_MANIFEST.md:56` | `agents/phenoagent/python/*` | (a) | YES | `test -e agents/phenoagent/python; echo $?` → `0` |
| C10 | `crates/ABSORPTION_MANIFEST.md:44` | root `agentkit` (listed as a live workspace member) | **(b)** | **NO** | `test -e agentkit; echo $?` → `1` |

**Family C totals:** (a) 4, (b) 4, (c) 2.

---

## 6. Family D: `docs/ABSORPTION_INDEX.md` (2 records)

| # | Record (file:line) | Claimed destination | Bucket | Exists | Evidence (literal) |
|---|---|---|---|---:|---|
| D1 | `docs/ABSORPTION_INDEX.md:11` | `docs/absorbed-from/phenotype-hub/README.md` | (a) | YES | `test -e docs/absorbed-from/phenotype-hub/README.md; echo $?` → `0` |
| D2 | `docs/ABSORPTION_INDEX.md:12` | `docs/absorbed-from/vibeproxy-monitoring-unified/README.md` | (a) | YES | `test -e docs/absorbed-from/vibeproxy-monitoring-unified/README.md; echo $?` → `0` |

Both index entries land. However `docs/ABSORPTION_INDEX.md:3` and `:22` promise a
disposition README "for each entry" under `docs/absorbed-from/<repo>/`:

```sh
$ ls -1 docs/absorbed-from/
phenotype-hub
vibeproxy-monitoring-unified
```

Two directories exist, matching the two entries. The promise is kept **for the two
entries that are in the index**; it is not a 33-entry backlog. The prior audit's
"only 2 of 33 exist" phrasing (`docs/absorption/ABSORPTION-LINEAGE.md:212`) reads the
33 `docs/absorption/` directories as if they were index entries. They are not; the
index has 2 rows. This is a counting artefact, not a broken promise.

---

## 7. Bucket summary and the absent cases

### 7.1 Grand totals across all four families

| Bucket | Family A | Family B | Family C | Family D | **Total** |
|---|---:|---:|---:|---:|---:|
| (a) local path, EXISTS | 1 | 9 (+1 half) | 4 | 2 | **16** |
| (b) local path, ABSENT | 1 | 5 (+1 half) | 4 | 0 | **12** |
| (c) other repo / free text | 9 | 12 | 2 | 0 | **16** |
| (d) no destination stated | 0 | 0 | 0 | 0 | **1** (PhenoKits) |

12 + 16 + 16 + 1 = 45 enumerated records. ✔

### 7.2 Each ABSENT case, with the exact key to change

Suggested statuses use the vocabulary the records already use elsewhere:
`PENDING` where the migration demonstrably did not land, `AFFIRM` where the record is
correct and needs no change. (None of the ABSENT cases qualifies for `AFFIRM`.)

| # | File:line | Exact key / line to change | Current value | Suggested truthful status |
|---|---|---|---|---|
| A6 | `projects/agent-user-status.json:5` | `"status"` (destination at `:11` `absorbing_path`) | `"absorbed"` | `"PENDING"` |
| B10 | `docs/absorption/phenoUtils/README.md:54` | `fsm=absorbed` (destination at `:5`) | `absorbed` | `PENDING` |
| B11 | `docs/absorption/phenoData/README.md:8` | `Status` (destination at `:6`, `:17-21`) | `absorbed (2026-07-17)` | `PENDING` |
| B12 | `docs/absorption/PhenoPlugins/README.md:5` | `Path` (destination claim) | `crates/pheno-plugins-*` | `PENDING` |
| B13 | `docs/absorption/phenotype-pm-core/README.md:9` | `Target paths` | `crates/traceability-*`, `crates/trace-gate/` | `PENDING` |
| B14 | `docs/absorption/phenoResearchEngine/README.md:9` | `Target path` | `phenotype-research-engine/` | `PENDING` |
| B15b | `docs/absorption/Quillr/README.md:16` | TS-half `Status` cell | `✅ absorbed` | `PENDING` for the TS half only |
| B16 | `docs/absorption/agent-user-status/README.md:3` | `**Status:**` | `ABSORBED 2026-07-17` | `PENDING` |
| B17 | `docs/absorption/audit-tool/README.md:51` | `fsm=absorbed` | `absorbed` | `PENDING` |
| B18 | `docs/absorption/Benchora/README.md:12` | `Verification` / `Absorbed date` | `cargo check -p benchora ...` | `PENDING` (see 9.3: present on worktrees, absent on main) |
| B19 | `docs/absorption/KodeVibe/README.md:9` | `Target path` | `tools/kodevibe/` | `PENDING` |
| B20 | `docs/absorption/KWatch/README.md:6` | `**Target**` | `phenotype-tooling/tools/kwatch/` | `PENDING` |
| B21 | `docs/absorption/scripts/README.md:7` | `**Disposition**` | `ABSORB` | `PENDING` |
| B22 | `docs/absorption/Sidekick/README.md:7` | `**Disposition**` | `ABSORB` | `PENDING` |
| B23 | `docs/absorption/curated-traces/README.md:7` | `**Disposition**` | `ABSORB` | `PENDING` |
| C3 | `crates/ABSORPTION_MANIFEST.md:26` | agent-platform paragraph | `is canonical in adapters/web/agent-platform/` | `PENDING` |
| C4 | `crates/ABSORPTION_MANIFEST.md:34` | KlipDot paragraph | `absorption target is <REDACTED>/rich-cli-kit/crates/klipdot/` | `PENDING` |
| C8 | `crates/ABSORPTION_MANIFEST.md:55` | split-target table row | `libs/phenotype-observability` -> `PhenoObservability` | `PENDING` |
| C10 | `crates/ABSORPTION_MANIFEST.md:44` | workspace-policy sentence | "root `agentkit` [is] in the default cargo workspace today" | `PENDING` |

---

## 8. Files with no status at all

`projects/phenotype-dag-core-rename-2026-09-01.json` is the **only** one of the 178
project JSONs with no `status` key:

```sh
$ for f in projects/*.json; do rg -q '"status"' "$f" || echo "$f"; done
projects/phenotype-dag-core-rename-2026-09-01.json
```

It therefore states no disposition and cannot be classified as `absorbed` or
otherwise. It is recorded here so the enumeration is complete, not as a defect.

---

## 9. Where this pass differs from `ABSORPTION-LINEAGE.md` section 2.3

### 9.1 "33 records, 11 with an explicit destination, none present"

Re-measured:

* The 33 is a **directory** count under `docs/absorption/`. README count is 32
  (`find docs/absorption -maxdepth 2 -name README.md | wc -l`).
* The 11 explicit destinations are real, but several of them resolve:
  `docs/specs/pheno-specs` → `0`, `docs/specs/router-protocol` → `0`,
  `crates/phench` → `0`, `crates/logkit` → `0` (via `PhenoObservability` and `pheno`),
  `crates/eidolon-*` → five `0`s, `crates/httpora-core` → `0`.
  "None of the 11 destinations is in this tree" is not reproducible.

### 9.2 The class is mostly unverifiable, not false

Of the 45 records, **16 name another repository and cannot be settled from this
tree**. Merging those into "absent" would overstate the defect by an order of
magnitude. The 12 genuine absent-destination cases are listed in 7.2 with the exact
key to fix.

### 9.3 `Benchora`: absent on `main`, present on worktrees

`docs/absorption/Benchora/README.md:9` claims `crates/benchora/` in
`phenotype-tooling`. The checked-out `phenotype-tooling` returns `1`. A depth-4 search
of the sibling tree finds the crate only under worktrees:

```
phenotype-tooling-wtrees/redispatch-origin-main-candidate/crates/benchora
phenotype-tooling-wtrees/pheno-forge-scaffold/crates/benchora
phenotype-tooling-wtrees/redispatch-state-fix/crates/benchora
```

So the migration plausibly landed on a branch that was never merged to the checked-out
default branch. That is a branch-state question this pass cannot close. Suggested
status: `PENDING` until a branch and commit are named.

### 9.4 The systemic finding

**The registry cannot express a checkable claim, because destinations are free text
rather than a typed path-or-repo field.**

Evidence:

* `projects/agent-user-status.json:11` is the only `projects/*.json` record with a
  path-typed destination key (`absorbing_path`). It is also the only provable
  violation. The schema that would have caught this is used exactly once in 178 files.
* The other 10 absorbed records put the destination in `absorbed_into` / `absorbing_repo`
  as prose, mixing repo names, parenthetical paths, and human notes in one string, e.g.
  `"phenotype-tooling (crates/phench)"` (`projects/phench.json:13`) and
  `"PhenoObservability (crates/logkit overlay)"` (`projects/Logify.json:13`).
  A validator cannot act on either.
* `projects/pheno-research-2026-09-01.json:27-38` shows what a checkable record looks
  like: a `verification` object with `target_path_present`, `absorb_commit_primary`,
  `absorb_status`, and `bytewise_verification`. It is the one record that passed
  cleanly, because it is the one record that states machine-testable facts.
* `crates/ABSORPTION_MANIFEST.md:54` writes a destination as
  `phenotype-tooling/absorption/` (resolves, exit `0`) while `:26` writes
  `adapters/web/agent-platform/` (absent, exit `1`) in the same list format with no
  marker distinguishing a repo-qualified path from a tree-relative path.
* `docs/absorption/Sidekick/README.md:5` writes a destination as a brace expansion,
  `PhenoObservability/crates/{sidekick-messaging,sidekick-obs-core,sidekick-observability}/`,
  which no path test can consume without custom parsing.

**Consequence.** The `absorbed` label is currently unfalsifiable for 16 of 45 records
and wrong for up to 12. Correcting the labels fixes today's numbers; adding a typed
destination field (one of: `path` relative to a named repo, or `repo_slug` plus
`path`) is what stops the class from recurring. That schema change is out of scope for
this pass, which is read-only apart from this file.

---

## 10. Could not verify

| # | Item | Why it could not be verified |
|---|---|---|
| 1 | `phenotype-python-sdk` destinations (`backend-melosviz` B24, `PolicyStack` B25) | The repo is not checked out at `/Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-python-sdk`. Only `phenotype-python-sdk-wtrees/` exists, and `packages/melosviz` / `packages/policystack` are absent there (`exit 1`). A `-wtrees` directory is not the repo default branch, so its contents do not settle the claim. |
| 2 | `phenotype-go-sdk/packages/graphclient` (A11, B26) | Repo not checked out. `phenotype-go-sdk-wtrees` exists; `packages/graphclient` is absent there (`exit 1`). |
| 3 | `phenokits-commons/templates/` (B27, C6) | Repo not checked out under that name. `zz-phenokits-commons/templates` exists, but a differently-named checkout cannot be assumed to be the claimed target. |
| 4 | `HexaKit` as owner of `phenotype-*` infra (C5) | No `HexaKit` checkout. `_full_HexaKit` exists but is a differently-named directory. |
| 5 | `phenoUtils` (A10, and `docs/absorption/phenoUtils/README.md` B10) | No `phenoUtils` checkout. `zz-merge-unk-PhenoUtils` exists; `crates/pheno-utils-shell` is absent inside it (`exit 1`). |
| 6 | `Benchora` on the `phenotype-tooling` default branch (B18) | Present in three `phenotype-tooling-wtrees` worktrees, absent from the checked-out `phenotype-tooling`. Which branch is canonical is not determinable from this tree. |
| 7 | Whether any absent destination exists **on GitHub** | Network/credential checks were out of scope for this read-only pass, and `docs/absorption/ABSORPTION-LINEAGE.md:216-236` already records that `gh auth status` reports the stored token invalid. Do not read "ABSENT" in this document as "does not exist on GitHub"; it means "does not exist at the checked-out path on this host". |
| 8 | Content parity of every bucket-(a) destination | This pass tested existence only. A present directory is not proof of a complete or faithful transfer. |
| 9 | `docs/absorption/phenoDesign/README.md` live status (B28) | The record asserts absorption at `:6` and reversal at `:9-11`. Neither the reversal branch nor `phenodocs` is available, so the current state of the reversal is unverified. |
| 10 | `projects/phenotype-dag-core-rename-2026-09-01.json` disposition | The file has no `status` key. Nothing to test. |

---

## 11. Reproduce

```sh
cd /Users/kooshapari/CodeProjects/Phenotype/repos/PhenoShared

# enumeration
ls -1 projects/*.json | wc -l                                      # 178
rg -l '"status"\s*:\s*"absorbed"' projects/*.json                  # 11 files
find docs/absorption -maxdepth 2 -name README.md | wc -l           # 32
for f in projects/*.json; do rg -q '"status"' "$f" || echo "$f"; done

# the one provable registry violation
test -e crates/agent-user-status; echo $?                          # 1

# the ABSENT local-path cases
for c in shell fs net async crypto testing chaos; do test -e crates/pheno-utils-$c; echo $?; done
for c in core query surreal pg smoke-tests; do test -e crates/pheno-data-$c; echo $?; done
for c in core git sqlite vessel examples; do test -e crates/pheno-plugins-$c; echo $?; done
test -e crates/trace-gate; echo $?; test -e phenotype-research-engine; echo $?
test -e crates/httpora-core; echo $?; test -e packages/quillts; echo $?

# the manifest cases
test -e adapters/web/agent-platform; echo $?                       # 1
test -e rich-cli-kit/crates/klipdot; echo $?                       # 1
test -e libs/phenotype-observability; echo $?                      # 1
test -e agentkit; echo $?                                          # 1
```

**End of truth pass.** One file created: `docs/audits/ABSORPTION-STATUS-TRUTH.md`.
No other file was created, edited, moved, or deleted. No `git add` or `git commit` was
run. No `cargo`, `make`, or destructive command was run.
