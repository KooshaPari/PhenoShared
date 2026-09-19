# Registry invariant: absorbed records must have a destination that exists

**Checker:** `scripts/audit/registry-invariant.sh`
**Status:** implemented, self-tested (negative + positive control), 18 real violations today
**Date:** 2026-09-18

## 0. Coordinator verification and one fix (2026-09-19)

Built by a worker; verified by running it, not by reading it.

**Confirmed by execution.** Real repo: exit **1**, `files=214 projects_absorbed=11
claims=128 ok=40 violations=18 unverifiable=70 skipped_no_status=1`. Self-test:
negative control exits **1** with 4 violations, positive control exits **0** —
**PASS**. The three-category design (path-absent ⇒ VIOLATION; repo slug or free
text ⇒ UNVERIFIABLE) is correct and is what stops the gate firing on
legitimate cross-repo destinations.

**Fix applied.** The wildcard defect in limit 3 was real. I diagnosed the cause
wrongly at first (I assumed unquoted shell expansion); the worker corrected me —
the checker is Python, and the false `OK` came from its own explicit
`glob.glob()` fallback inside `exists()`. Same wrong verdict, different
mechanism, and the worker was right. The fallback is now removed and interior
wildcards are classified explicitly in `resolve()`. Re-run after the fix:
`phenoData:6` moved **OK → UNVERIFIABLE**, `ok` 41 → 40, `unverifiable` 69 → 70,
violations unchanged at 18, self-test still PASS.

**The number 18 is a lower bound.** A second, larger hole was found while
verifying: prose path lists are not scanned at all. See limit 12 — five absent
crates in `phenoData/README.md` lines 37-41 are invisible to the checker, so the
true count is at least 23. The fix is deliberately deferred rather than rushed,
because a scanner that flags illustrative paths would fire on correct data.

**Cross-check against an independent method.** A separate per-record pass over
four ledger families reported **12 records** with an absent local path. The
checker reports **18 paths**. These agree exactly: two records name several
destinations on one line (`PhenoPlugins/README.md:19-23` = 5 paths,
`phenotype-pm-core/README.md:9` = 3), so 12 + 4 + 2 = 18. Recorded so neither
number is later "corrected" to match the other.

## 1. The invariant

> A record may not claim to be absorbed unless the destination path it names
> actually exists in this repository.

The absorption registry (`projects/*.json`) and the absorption documentation
surface (`docs/absorption/*/README.md`, `docs/ABSORPTION_INDEX.md`,
`docs/absorbed-from/*/README.md`, `crates/ABSORPTION_MANIFEST.md`) contain
records that assert a repository was absorbed **into a specific location**.
Nothing verified that the location exists. A record could therefore read
`"status": "absorbed"` while its destination was never created or was later
deleted, and no tool would notice.

This checker makes that class of error impossible to hide silently: it turns the
claim into an assertion that fails a build.

## 2. How to run it

```bash
# from the repository root
./scripts/audit/registry-invariant.sh              # check this repository
./scripts/audit/registry-invariant.sh --self-test  # negative + positive control, then the real repo
./scripts/audit/registry-invariant.sh --root DIR   # check an alternate root
./scripts/audit/registry-invariant.sh --help
```

Exit codes:

| Exit | Meaning |
|------|---------|
| `0` | no VIOLATION (`UNVERIFIABLE` does not affect the exit code) |
| `1` | at least one VIOLATION |
| `2` | usage or harness error (including a failed self-test control) |

Output grammar, one line per claim site:

```
OK            <source>:<line> path <p> exists
VIOLATION     <source>:<line> absorbed-but-absent <p>
UNVERIFIABLE  <source>:<line> destination is not a local path: <text>
SUMMARY       files=<n> projects_absorbed=<n> claims=<n> ok=<n> violations=<n> unverifiable=<n> skipped_no_status=<n>
```

The script is read-only for the repository. `--self-test` writes its fixtures
under `$JCODE_SCRATCH_DIR` only.

## 3. What counts as a violation, and what does not

A gate that fires on correct data gets disabled, so the checker distinguishes
three outcomes instead of two.

| Destination written as | Example | Outcome |
|---|---|---|
| path-shaped, present | `crates/phench/` | `OK` |
| path-shaped, absent | `crates/benchora/` | `VIOLATION` |
| explicit path field, absent | `absorbing_path: "crates/agent-user-status/"` | `VIOLATION` |
| repo slug | `phenotype-infra`, `phenoUtils` | `UNVERIFIABLE` |
| repo slug + path prose | `phenotype-tooling (crates/phench)` | `UNVERIFIABLE` |
| repo-qualified path, tail present | `pheno/crates/logkit/` | `OK` |
| repo-qualified path, tail absent | `phenotype-tooling/tools/kwatch/` | `UNVERIFIABLE` |
| anything else | `(NOT transferred — generated SBOM)` | `UNVERIFIABLE` |

Rules that produce this table:

1. A **path-shaped** destination (two or more segments whose first segment is a
   known content root such as `crates/`, `packages/`, `libs/`, `tools/`, or any
   existing top-level entry) **must exist**. Absent means `VIOLATION`.
2. A value under an **explicit path label** (`Target path`, `Target paths`,
   `Absorbing path`, `Canonical path`, `Canonical target`, `Canonical home`, or a
   `Path` column) **must exist**, even when it is a single segment.
3. A **repo-qualified** path (`<repo-slug>/<content-root>/...`) is read as "that
   repo, this path". The slug is stripped and the tail is checked locally; a
   present tail is `OK`, an absent tail is `UNVERIFIABLE`, never a violation.
4. A **repo slug or free text** is `UNVERIFIABLE`. This repository cannot see
   another repository, so absence here is expected and is not evidence of a
   defect.
5. **Relative markdown links** in `docs/ABSORPTION_INDEX.md`,
   `docs/absorbed-from/*/README.md` and `crates/ABSORPTION_MANIFEST.md` must
   resolve inside this repository. A link that escapes the repository is
   `UNVERIFIABLE`; a link that points inside but is missing is a `VIOLATION`.
6. Content inside **fenced code blocks** is ignored, because absorption records
   embed verification transcripts that contain commands and paths from the
   source environment (`python3 scripts/audit.py /Users/.../phenotype-registry`).
7. Files with **no `status` key** are counted as `skipped_no_status` and are
   never a violation. Explicit decision: no status key means no absorption claim
   to verify. Today this is exactly one file,
   `projects/phenotype-dag-core-rename-2026-09-01.json`, a rename record with
   `old_path` / `new_path` and no `status`. Its `new_path` is not checked.

## 4. The negative control (proves the checker fails on broken data)

`--self-test` builds a fixture under `$JCODE_SCRATCH_DIR` that deliberately
contains an absorbed record whose destination is absent, runs the checker against
it, and asserts that the checker exits `1`. The same fixture is then rebuilt with
the destinations made present and asserted to exit `0`, so the control also
proves the checker is not simply always failing.

Every scanner gets its own broken record in the fixture, and the fixture embeds a
fenced-code trap (`crates/never-a-path-zzz/` inside a ```` ```bash ```` block).
If fenced transcripts were scanned, the control counts would change and the
self-test would fail.

### Literal command

```bash
./scripts/audit/registry-invariant.sh --self-test
```

### Real observed output, negative control

```
=== NEGATIVE CONTROL (fixture with deliberately absent destinations) ===
fixture=/Users/kooshapari/.jcode/scratch/registry-invariant-selftest/broken
UNVERIFIABLE projects/zz-free-text.json:4 destination is not a local path: phenotype-tooling (crates/phench)
VIOLATION projects/zz-negative-control.json:4 absorbed-but-absent crates/definitely-absent-zzz
UNVERIFIABLE projects/zz-negative-control.json:5 destination is not a local path: some-other-org/some-other-repo
OK projects/zz-positive-control.json:4 path crates/present-zzz exists
VIOLATION docs/absorption/zz-field/README.md:6 absorbed-but-absent packages/absent-zzz
VIOLATION docs/ABSORPTION_INDEX.md:5 absorbed-but-absent docs/absorbed-from/zz-missing/README.md
OK docs/absorbed-from/zz-present/README.md:5 path docs exists
VIOLATION crates/ABSORPTION_MANIFEST.md:3 absorbed-but-absent libs/absent-zzz
SUMMARY files=8 projects_absorbed=3 claims=8 ok=2 violations=4 unverifiable=2 skipped_no_status=1
observed_exit_code=1 expected_exit_code=1 | observed_violations=4 expected_violations=4
```

Reading it: one deliberately broken record per scanner produced exactly four
violations (JSON `absorbing_path`, markdown `Target path`, index link, manifest
`canonical in`), the repo-slug and free-text values stayed `UNVERIFIABLE`, and the
fenced trap produced nothing. The checker exited `1`.

### Real observed output, positive control

```
=== POSITIVE CONTROL (same fixture, destinations made present) ===
fixture=/Users/kooshapari/.jcode/scratch/registry-invariant-selftest/clean
UNVERIFIABLE projects/zz-free-text.json:4 destination is not a local path: phenotype-tooling (crates/phench)
OK projects/zz-negative-control.json:4 path crates/present-zzz exists
UNVERIFIABLE projects/zz-negative-control.json:5 destination is not a local path: some-other-org/some-other-repo
OK projects/zz-positive-control.json:4 path crates/present-zzz exists
OK docs/absorption/zz-field/README.md:6 path crates/present-zzz exists
OK docs/ABSORPTION_INDEX.md:5 path docs/absorbed-from/zz-present/README.md exists
OK docs/absorbed-from/zz-present/README.md:5 path docs exists
OK crates/ABSORPTION_MANIFEST.md:3 path crates/present-zzz exists
SUMMARY files=8 projects_absorbed=3 claims=8 ok=6 violations=0 unverifiable=2 skipped_no_status=1
observed_exit_code=0 expected_exit_code=0 | observed_violations=0 expected_violations=0
```

### Self-test verdict

```
=== CONTROL VERDICT ===
SELF-TEST: PASS (negative control exited 1 with 4 violations; positive control exited 0)
```

## 5. Real repository result

`./scripts/audit/registry-invariant.sh` exits **1** with **18 violations**:

```
SUMMARY files=214 projects_absorbed=11 claims=128 ok=41 violations=18 unverifiable=69 skipped_no_status=1
```

| Source | OK | VIOLATION | UNVERIFIABLE |
|---|---:|---:|---:|
| `projects/*.json` | 0 | 1 | 11 |
| `docs/absorption/*/README.md` | 28 | 16 | 52 |
| `crates/ABSORPTION_MANIFEST.md` | 0 | 1 | 6 |
| `docs/ABSORPTION_INDEX.md` + `docs/absorbed-from/*/README.md` | 13 | 0 | 0 |
| **total** | **41** | **18** | **69** |

The 18 violations, verbatim:

```
VIOLATION projects/agent-user-status.json:11 absorbed-but-absent crates/agent-user-status
VIOLATION docs/absorption/Benchora/README.md:9 absorbed-but-absent crates/benchora
VIOLATION docs/absorption/KodeVibe/README.md:9 absorbed-but-absent tools/kodevibe
VIOLATION docs/absorption/PhenoPlugins/README.md:19 absorbed-but-absent crates/pheno-plugins-core
VIOLATION docs/absorption/PhenoPlugins/README.md:20 absorbed-but-absent crates/pheno-plugins-git
VIOLATION docs/absorption/PhenoPlugins/README.md:21 absorbed-but-absent crates/pheno-plugins-sqlite
VIOLATION docs/absorption/PhenoPlugins/README.md:22 absorbed-but-absent crates/pheno-plugins-vessel
VIOLATION docs/absorption/PhenoPlugins/README.md:23 absorbed-but-absent crates/pheno-plugins-examples
VIOLATION docs/absorption/PolicyStack/README.md:9 absorbed-but-absent packages/policystack
VIOLATION docs/absorption/Quillr/README.md:16 absorbed-but-absent packages/quillts
VIOLATION docs/absorption/backend-melosviz/README.md:4 absorbed-but-absent packages/melosviz
VIOLATION docs/absorption/grapheon-bindings/README.md:9 absorbed-but-absent packages/graphclient
VIOLATION docs/absorption/phenoResearchEngine/README.md:9 absorbed-but-absent phenotype-research-engine
VIOLATION docs/absorption/phenoUtils/README.md:5 absorbed-but-absent crates/pheno-utils-*
VIOLATION docs/absorption/phenotype-pm-core/README.md:9 absorbed-but-absent crates/traceability-core
VIOLATION docs/absorption/phenotype-pm-core/README.md:9 absorbed-but-absent crates/traceability-decorators
VIOLATION docs/absorption/phenotype-pm-core/README.md:9 absorbed-but-absent crates/trace-gate
VIOLATION crates/ABSORPTION_MANIFEST.md:9 absorbed-but-absent absorption/PHENOAGENT_ABSORPTION_2026_06_18.md
```

Notes on the real findings:

- `projects/agent-user-status.json:11` is the single absorbed project record that
  states a real local path (`"absorbing_path": "crates/agent-user-status/"`). It
  is absent. The other 10 absorbed project records name a destination repo, so
  they are `UNVERIFIABLE`, not violations. This matches the independent
  measurement of the same 11 records.
- 17 of the 18 are "claimed destination path is not in the tree".
- `crates/ABSORPTION_MANIFEST.md:9` is a broken relative link: the manifest
  writes ``[`docs/absorption/PHENOAGENT_ABSORPTION_2026_06_18.md`](../absorption/PHENOAGENT_ABSORPTION_2026_06_18.md)``,
  which resolves to `absorption/...` at the repository root. The link needs a
  second `../` to reach `docs/absorption/`. The target file does exist; the link
  does not point at it.
- `docs/absorption/phenotype-pm-core/README.md:9` is three violations on one
  line: the cell lists three destination paths and all three are absent.

Representative `UNVERIFIABLE` lines (69 total, not violations):

```
UNVERIFIABLE projects/PhenoLang.json:12 destination is not a local path: phenoUtils
UNVERIFIABLE projects/phench.json:13 destination is not a local path: phenotype-tooling (crates/phench)
UNVERIFIABLE docs/absorption/curated-traces/README.md:5 destination is not a local path: PhenoObservability/curated-traces/
UNVERIFIABLE docs/absorption/KWatch/README.md:6 destination is not a local path: phenotype-tooling/tools/kwatch/
```

## 6. Honest limits (what this checker cannot see)

1. **Cross-repo destinations are unverifiable from here.** All 11 absorbed project
   records name a destination *repository*; only one also names a local path. A
   record can be factually wrong in the other repository and this checker stays
   silent. It verifies claims about *this* tree only.
2. **The same defect can land in either bucket depending on how it was written.**
   `docs/absorption/agent-user-status/README.md:1` claims
   `phenotype-tooling/crates/agent-user-status` in its title arrow and is reported
   `UNVERIFIABLE`, while the same missing destination in
   `projects/agent-user-status.json` is reported `VIOLATION`. Repo-qualified
   paths are never violations by design, because most of them legitimately refer
   to other repositories.
3. **FIXED 2026-09-19 — wildcard destinations could pass by accident.** Any
   single glob match used to satisfy a claim: `docs/absorption/phenoData/README.md:6`
   claims `crates/pheno-data-*` and passed, because the stale
   `crates/pheno-data-from-phenoData/` directory matched — while all five
   claimed crates are in fact absent. The cause was a `glob.glob()` fallback
   inside `exists()`, not shell expansion. Removed; a wildcard now yields
   `UNVERIFIABLE` (naming what it matched) or `VIOLATION` when the pattern is
   repo-anchored, and never `OK`. Observed effect: `phenoData:6` OK →
   `UNVERIFIABLE`, `ok` 41 → 40, `unverifiable` 69 → 70, violations unchanged at
   18, self-test still PASS.
4. **Top-level directory names in free text are ambiguous.**
   `phenotype-research-engine/` is claimed under an explicit `Target path` label
   and is therefore a violation; the bare slug `phenoUtils` is not. A missing
   *new-style* top-level directory used as a bare destination would be reported
   `UNVERIFIABLE` rather than `VIOLATION`, unless it appears under a path label.
5. **It checks existence, not correctness.** A directory existing at the claimed
   path proves nothing about whether the code was actually migrated, is complete,
   or is the canonical copy. An empty or stale directory passes.
6. **It does not verify absorption provenance.** `absorbed_commit`,
   `absorbed_branch`, `source_commit`, GitHub archive state and remote 404 status
   are out of scope.
7. **Only `status == "absorbed"` records are checked.** Records with
   `disposition: "ABSORB"` but a non-absorbed status (for example `active`,
   `queued`, `archived`) carry `absorbed_into` values that this invariant does not
   examine. A destination asserted on a queued row can be absent without failing.
8. **Files without a `status` key are skipped** (`skipped_no_status=1` today). If
   such a file ever carries an absorption claim, the checker will not see it.
9. **Extraction is pattern-based.** A destination expressed in a shape not covered
   by the scanner (only inside a fenced block, inside an image, in a table whose
   header is not a destination column, or in prose with no absorption marker) is
   invisible. Fenced blocks are skipped on purpose, which cuts both ways: a
   destination mentioned *only* in a fenced block is never checked.
10. **Counts are claim sites, not distinct defects.** One line per
    `(source, line, destination text)`. Three absent paths in one markdown cell
    count as three violations; the same claim repeated in a title and a field
    counts twice unless the text and line match exactly.
11. **It remediates nothing.** It reports. Fixing a violation means either
    correcting the record to match reality or downgrading the record's status;
    that judgement is the reviewer's, not the checker's.
12. **The 18 is a LOWER BOUND — prose path lists are not scanned.** A destination
    named in ordinary prose rather than under a destination key is invisible.
    Concrete, verified example: `docs/absorption/phenoData/README.md` lines
    **37-41** list five transferred crates as backticked local paths
    (`crates/pheno-data-core/`, `-query/`, `-surreal/`, `-pg/`, `-smoke-tests/`).
    **All five are absent**, and the checker reports **none** of those lines
    (verified: lines 37-41 produce no output at all). So the real violation count
    is **at least 23, not 18**. Line 32 of the same file also asserts that five
    stale `crates/pheno-data-from-phenoData/` artefacts were *removed* — that
    directory still exists with 14 files — and a *removal* claim is not a
    destination claim, so no version of this invariant would catch it.
    Widening the scanner to all path-shaped prose is deliberately **not** done
    here: it would flag illustrative paths and make the gate fire on correct
    data, which is how gates get switched off. That remains an open task.

## 7. Using it

```bash
# gate: fails (exit 1) while any absorbed record points at a path that is absent
./scripts/audit/registry-invariant.sh

# regression proof that the gate still detects a broken record
./scripts/audit/registry-invariant.sh --self-test
```

A violation is resolved by making the registry honest: either the destination
path is created (restore the absorbed content) or the record stops claiming
`absorbed` at that location. The checker is deliberately not able to do that
itself, because both resolutions are content decisions.
