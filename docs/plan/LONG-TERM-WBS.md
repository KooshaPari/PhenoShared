# PhenoShared — long-term WBS

**Baseline:** `925ab5ce`, 29,057 tracked files, 694 commits, 494 package
manifests under `crates/` + `tools/`, 84 workflow files.

**Read with:** `docs/audits/GIT-HISTORY-INTEGRITY.md`,
`docs/audits/IDENTITY-CLAIMS.md`, `docs/atlas/codebase/INVENTORY.md`,
`docs/absorption/ABSORPTION-LINEAGE.md`, `docs/audits/PII-SWEEP-DAMAGE.md`.

Task IDs follow the house convention (`E.N` ≈ 10 minutes; `E.0` = epic;
deeper levels allowed). Owner is **HOST** (this machine) or **DESK** (the other
machine) per the two-machine split in §5.

---

## Why this plan exists

Four episodes in this repo share one shape: **a mechanism was built, it never
worked, and nothing detected that.**

| Episode | Built | Actually happened |
|---|---|---|
| `clippy.toml` | A lint config | `cargo clippy` exited 101 for every crate; `make check` could not run |
| `rustfmt.toml` | A style config | 19 options are nightly-only; CI runs stable; stable `cargo fmt --all --check` exits 1 wanting **288** distinct files changed (nightly wants **456**; **168** nightly-only, **0** stable-only) |
| `tray-native` | A tray feature, its own binary, SPEC acceptance criteria | Never compiled (until now); still fails at runtime — `muda::Menu` off the main thread |
| `bc7c0ad7` | "Add unit tests for DurationExt" | Committed 3,763 files, 3,757 of them zero-byte |

Every one was invisible because **the check that would have caught it was
itself broken or absent**. That is the program thesis: *gates first, then
content.*

---

## E1 — Make every gate actually run (HOST, critical path)

The only epic that blocks the others.

- **E1.1** Decide the fmt policy: point the CI fmt step at nightly (honours
  `rustfmt.toml`'s intent) **or** trim `rustfmt.toml` to stable-only options.
  Record the decision in `docs/decisions/`.
  Measured inputs (verified 2026-09-19, `docs/audits/FMT-GATE.md`): stable
  `cargo fmt --all -- --check` exits **1** and wants **288** distinct files
  changed; the same command under nightly exits **1** and wants **456**, of
  which **168 are nightly-only and 0 are stable-only** — so the stable set is a
  strict subset of the nightly set. `crates/phinbox` alone accounts for **69**
  of the 288 (83% of its 83 tracked `.rs` files).
  **Trap:** the rustup **default** toolchain on this host is `nightly`, so any
  `cargo fmt` run from a directory outside this repo silently formats with
  nightly. Any instruction to "run cargo fmt" must state the toolchain
  explicitly, or the result is not reproducible.
- **E1.2** Implement the decision; confirm `cargo fmt --check` exits 0.
- **E1.3** Reformat in a dedicated, message-scoped commit (never mixed with
  logic changes) — this is a **288-file** change under stable (456 under
  nightly), of which 69 are in `phinbox`, so it must not be mixed with the
  phinbox work in E3/E4.
- **E1.4** Measure `cargo clippy --workspace --locked -- -D warnings`
  (what `quality-gate.yml` runs). Until this passes, **`main` cannot merge**.
- **E1.5** Fix or allow-with-reason the workspace clippy findings; ban blanket
  `#![allow]` in favour of scoped ones (see E4).
- **E1.6** Confirm `make check` is green end to end.
- **E1.7** Generalise `crates/phinbox/scripts/check-targets.sh` into
  `scripts/check-cross-targets.sh` for every crate with `cfg`-gated modules.
- **E1.8** Wire E1.6 + E1.7 into one Linux-only CI job; delete or gate the
  redundant ones (see E6).

**Done when:** a fresh clone runs `make check` green, and CI is red if it
would not.

---

## E2 — Prove the workspace builds and tests at all (HOST)

- **E2.1** `cargo build --workspace --locked` — record the failure set.
- **E2.2** `cargo test --workspace --locked` — record pass/fail per package.
- **E2.3** Triage into: never compiled / compiles, tests fail / compiles,
  untested. Publish the table in `docs/atlas/codebase/`.
- **E2.4+** One 10-minute task per broken package (unknown count until E2.3).

**Unknown:** the true number. 494 manifests exist; the root workspace has 79
packages and 5 auto-included path members. Everything else is either a nested
workspace (26 found) or unbuilt.

---

## E3 — Provenance: what we actually have and where it came from (HOST)

- **E3.1** Land `docs/absorption/ABSORPTION-LINEAGE.md` (in flight) —
  source repo → hop chain → destination → evidence.
- **E3.2** Reconcile against the 20 known absorption commits; list
  destinations with no absorption commit, and absorptions with no ledger entry.
- **E3.3** Repair the ledger where the PII sweep destroyed source paths
  (`<REDACTED>/PhenoProc`), using `git log` to recover originals.
- **E3.4** Fix dangling relative links in the ledgers (they point outside the
  repo, e.g. `../../../migration-work/registry-wt/...`).
- **E3.5** Correct `README.md`'s crate-family table: the counts are wrong
  (claims 192 for 115 directories; `pheno-*` claimed 117, actual 38 manifests)
  and the `pheno-*` family is attributed to PhenoAI when PhenoCompose is the
  dominant contributor (`docs/audits/IDENTITY-CLAIMS.md`).
- **E3.6** Land the "authority" doc: which project owns which domain, so
  "who owns `inference`" has one answer.

---

## E4 — Undo the redaction collateral damage (HOST + DESK)

- **E4.1** Finish classification of the `REDACTED` corpus (3,402 files,
  40,471 occurrences per the identity audit). Classes: real PII /
  destroyed non-PII / syntactically broken / degenerate nesting.
- **E4.2** Repair the highest-value non-PII losses first: project names in
  document H1s (`ECOSYSTEM_MAP.md:1` = `# <REDACTED> Ecosystem Map`), the owner
  handle in `.github/CODEOWNERS` (`* @<REDACTED>`).
- **E4.3** Fix anything currently broken by redaction: URLs, npm scopes,
  package names, TOML values, code identifiers.
- **E4.4** Replace blanket `#![allow(dead_code)]` / `#![allow(missing_docs)]`
  introduced by `d0fe3aa3` with deletion or scoped allows + reasons.
- **E4.5** Add a redaction rule to `CONTRIBUTING.md`: never redact paths,
  repo names, or provenance; only personal data — and record the mapping.

---

## E5 — Repository hygiene at scale (DESK)

- **E5.1** Land the atlas generator and artifacts (`scripts/atlas/`,
  `docs/atlas/codebase/`) — in flight.
- **E5.2** Work the file-size list: every file >500 lines is a hard breach
  (house rule); >350 is the target. Split by concern, not by size.
- **E5.3** Rename test files violating the naming rule (`_v2`, `_new`, `_old`,
  `_final`, `_temp`, `_backup`, `_draft`, `*_complete`, `test_*_unit`,
  `test_*_fast`, arbitrary numbering).
- **E5.4** Delete the 13 remaining zero-byte tracked files (verify each).
- **E5.5** Consolidate `_archived/` (632 files), `archives/` (225),
  `.archive/` — three archive trees is two too many.
- **E5.6** Decide the fate of root-level debris (`_grade_three.py`, `_sc.json`,
  `_sc_runs.json`, `_tmp_deny.b64`, `_typos.toml`, 128 root-level `*.md`).
- **E5.7** Resolve duplicate trees: root `agileplus/` (1,102 files) vs
  `crates/agileplus-*` (78 packages); `docs/adr/` vs `docs/adrs/`.
- **E5.8** Fix the 39 documents whose H1 names a different project while
  living in this repo.

---

## E6 — CI cost and signal (HOST)

- **E6.1** Inventory the 84 workflows: what runs on push, what is
  `workflow_dispatch`-only (81 are), what is dead.
- **E6.2** Note that only 3 workflows are reusable (`workflow_call`) — the
  rest cannot be consumed by the fleet, which undercuts the "reusable
  workflows" claim in `README.md`.
- **E6.3** Prune; keep a Linux-only gate. AGENTS.md states Actions billing is
  exhausted and warns about swarm burn — 84 workflows per push is the largest
  controllable cost in this repo.
- **E6.4** Make the fleet-facing workflows actually reusable, or stop claiming
  they are.

---

## E7 — Absorption pipeline hardening (HOST)

So the next absorption does not repeat `bc7c0ad7` / `618ffd3c`.

- **E7.1** A scripted absorption: import → strip empty files → exclude
  scratch dirs (`.agileplus/`, `.trunk/`, editor state) → emit a ledger entry.
- **E7.2** Message template requiring: source repo, commit range, file count,
  verification performed.
- **E7.3** A pre-commit guard rejecting zero-byte additions and `git add -A`
  sweeps in a single commit over a threshold.
- **E7.4** Record the squash-merge policy explicitly, or stop squashing.

---

## E8 — Product-domain triage (DESK, per family)

One epic per absorbed family; each family gets the same three questions:
*does it build, does it test, does it have a home?*

- **E8.1** `focus-*` (43)
- **E8.2** `fabric-*` (20)
- **E8.3** `agileplus*` (78 + root tree)
- **E8.4** `eyetracker-*` (14)
- **E8.5** `sharecli-*` (12)
- **E8.6** `substrate-*` (10) + `driver-*`/`engine-*`
- **E8.7** `connector-*` (9)
- **E8.8** `eidolon-*`, `playcua-*`, `port-*` (the PhenoAI workload)
- **E8.9** non-Rust assets: `sites/` (603), `servers/` (386), `python/` (314),
  `unity/` (166), `bench/` (391), `agents/` (1,534), `registry/` (147)

Each: build ✓/✗, tests ✓/✗, docs ✓/✗, owner, and a keep/absorb/split/delete
recommendation. That is ~16 tasks per family; the count is the point.

---

## E9 — Continuous truth (HOST)

- **E9.1** Make the atlas a scheduled job; diff it and open an issue on drift.
- **E9.2** Extend the doc-claim audit pattern to every README (the identity
  audit found 39 mis-titled docs and a wrong crate table in one pass).
- **E9.3** A `docs/audits/README.md` index so audits are discoverable rather
  than scattered.

---

## E10 — The ledger overstates what was migrated (HOST)

### What is actually measurable (measured 2026-09-19, `projects/*.json`)

178 registry files. **11** carry `status: "absorbed"`. An earlier draft of this
epic claimed all 11 names an absent destination. That was wrong — it came from
testing a free-text field with `os.path.exists()`. The real split:

| Bucket | Count | Meaning |
|---|---|---|
| destination is a local path and **exists** | 0 via `absorbing_path` (4 via prose, see below) | absorb landed |
| destination is a local path and is **ABSENT** | **1** | the only *provable* registry violation: `agent-user-status`, `absorbing_path: "crates/agent-user-status/"` |
| destination is another repo / free text | **10** | **unverifiable from this tree** — absence here is expected, not a defect |

Four of those ten name local crates that **do** exist, so those absorbs landed:
`crates/logkit` (`Logify`), `crates/phench` (`phench`),
`crates/pheno-cdylib-bridge`, `crates/pheno-forge-smoke`.

Separately, `projects/phenotype-dag-core-rename-2026-09-01.json` has **no
`status` key at all**.

### The systemic problem (this is the real finding)

The registry **cannot express a checkable claim**. Destinations are free text —
`"phenotype-infra"`, `"phenoUtils"`, `"pheno (crates/phench)"` — held in
`absorbing_repo` / `absorbed_into`, with a real path field (`absorbing_path`)
used by exactly one record. Because a destination could be either a path or a
repo slug and nothing distinguished them, **no invariant was ever possible**,
which is why this went undetected. The fix is schema-level, not data-level.

### The wider set from the lineage audit

`docs/absorption/ABSORPTION-LINEAGE.md` §2.3 reports a larger figure: 33
records across *all* ledger sources (`docs/absorption/*/README.md`,
`crates/ABSORPTION_MANIFEST.md`, `docs/ABSORPTION_INDEX.md`), 11 naming an
explicit destination and none present. That set is real but **heterogeneous**:
it mixes other-repo destinations (whose absence here is expected and not
evidence of anything) with genuine local paths (`tools/kwatch`,
`tools/kodevibe`, `crates/agent-user-status` — these *are* real violations).
Its severity is therefore inflated for the other-repo subset and should be
re-derived with the same three-bucket rule before being quoted as a count.

### Cross-verified violation count (two independent methods, 2026-09-19)

Two independent passes over the ledger now agree, and the reconciliation is
exact — record it so neither number is later "corrected" to match the other:

| Method | Unit | Result |
|---|---|---|
| Per-record bucket pass over **4** ledger families (`ABSORPTION-STATUS-TRUTH.md`) | records | **12** records name an absent local path |
| Executable invariant over **5** sources, negative-controlled (`scripts/audit/registry-invariant.sh`) | paths | **18** absent paths, exit 1 |

`12 records = 18 paths` because two records name several destinations on one
line: `docs/absorption/PhenoPlugins/README.md:19-23` names **5** crates (+4) and
`docs/absorption/phenotype-pm-core/README.md:9` names **3** (+2). 12+4+2 = 18.
Both counts are right; they differ only in what they count.

The same pass also lists **16-69 unverifiable** claims depending on source set
(destinations that are repo slugs or free text), which the schema cannot check
at all. Those are not defects; they are the reason no invariant was possible
before the split in **E10.4**.

Worst individual case remains `phenoData` (**CRITICAL**): the record describes a
completed migration to five crates that do not exist *and* claims to have
deleted the stale artefacts that are still the only surviving copy of that code.

- **E10.1** Re-derive every count above using the three-bucket rule (path+exists
  / path+absent / not-a-local-path). No bucket may be merged into another.
- **E10.2** Correct the one provable false `absorbed` status
  (`agent-user-status` → `AFFIRM`/`PENDING`), and decide the ten unverifiable
  records: either supply a real `absorbing_path` or record that they cannot be
  verified from this tree.
- **E10.3** Recover what can be recovered. Sources are archived on GitHub;
  recovery is currently blocked on account-wide credentials (see §2.3 note).
- **E10.4** Schema first: require `absorbing_path` (a repo-relative path) or
  `absorbing_repo` (a repo slug) as **distinct typed fields**, then add the
  invariant test (no record may read `absorbed` with an absent
  `absorbing_path`). Without the schema split the test is unrepresentable.
- **E10.5** Give `phenoData` a human decision: the ledger says the surviving
  `crates/pheno-data-from-phenoData/` was superseded, but it is the only copy.

**Done when:** destination kind is typed, no record claims `absorbed` with an
absent `absorbing_path`, and unverifiable records say so explicitly.

---

## 5. Two-machine split

Disjoint by path prefix, so the two machines never edit the same file.

| | **HOST (here)** | **DESK (other machine)** |
|---|---|---|
| **Theme** | gates, governance, provenance, CI | product domains, hygiene at scale |
| **Epics** | E1, E2, E3, E4, E6, E7, E9 | E5, E8 |
| **Paths owned** | `docs/`, `audits/`, `absorption/`, `.github/`, `scripts/`, `Cargo.toml`, `Cargo.lock`, `rustfmt.toml`, `clippy.toml`, `crates/phinbox/**`, `crates/pheno-tracing/**`, `crates/phenotype-tooling-observability/**` | `crates/focus-*`, `crates/fabric-*`, `crates/agileplus*`, `crates/eyetracker-*`, `crates/sharecli-*`, `crates/substrate-*`, `crates/connector-*`, `crates/eidolon-*`, `crates/playcua-*`, `agileplus/`, `sites/`, `servers/`, `python/`, `unity/`, `bench/`, `agents/`, `registry/` |
| **Rule** | never edit a DESK path | never edit a HOST path |

Handoff prompt: `docs/plan/DESKTOP-HANDOFF-PROMPT.md`.

---

## Critical path

```
E1.1 fmt decision ─► E1.2/E1.3 reformat ─► E1.4 clippy --workspace ─► E1.6 make check green
                                    │
                                    └─► E2 workspace build/test ─► E8 product triage (DESK)
E3 lineage (parallel)   E4 redaction repair (parallel)   E5 atlas (parallel)
```

Nothing in E8 can be merged reliably until E1 lands, because there is
currently no gate that would reject a bad change.

## Definition of done

- `make check` green from a fresh clone.
- `cargo clippy --workspace --locked -- -D warnings` exit 0.
- `cargo fmt --check` exit 0 under a stated toolchain.
- Cross-target guard green for every `cfg`-gated crate.
- Every crate in `docs/atlas/codebase/INVENTORY.md` has a build/test verdict.
- No `<REDACTED>` in a path, repo name, URL, or provenance field.
- One archive tree, no zero-byte files, no mis-titled documents.
