# E2.4 Complex Belief-Errors: Categorization and Disposition

**Date:** 2026-10-09
**Author:** base chat (orchestrator) for operator review
**Status:** Audit complete; mechanical fix deferred to operator disposition
**Parent:** E2 "Pilot mass-fix for 230 belief-error manifests"
**Sibling:** E2.3 "156 simple belief-errors + 5 no-source" (closed 2026-10-09, 10 greens)

---

## 1. Summary

After E2.3 closed at 100% of mechanically-fixable subset (161/161 = 156 simple
`[workspace]` additions + 5 no-source fixes), E2.4 covers the remaining
**belief-error manifests that could not be safely auto-fixed**.

| Pattern | Live count | Archived | Total | Operator disposition required |
|---|---:|---:|---:|---|
| Pattern A (designed as workspace member) | 62 | 2 | 64 | Yes — add to `workspace.members` or convert fields to concrete |
| Pattern B (broken deps, root has no entry) | 31 | 2 | 33 | Yes — fix dep versions or add entries to `[workspace.dependencies]` |
| Anomaly (no `workspace=true` deps) | 1 | 0 | 1 | Yes — manual diagnosis |
| **Total still broken** | **94** | **4** | **98** | |

The original 60 estimate in WBS is an undercount; actual is 94 (live) or 98
(including archived). E2.3 + E2.4 pilot is at 161/230 fixed (70%).

---

## 2. Pattern A: Designed as workspace members (62 live)

**Symptom:** `[package]` section uses `version.workspace = true` and other
`package.*.workspace = true` fields; the parent workspace (root
`Cargo.toml` or `absorption/PhenoInfra/Cargo.toml`) was supposed to provide
the concrete values via `[workspace.package]`.

**Why this errors now:** these manifests are NOT in the parent workspace's
`members = []` list, so cargo emits `current package believes it's in a workspace
when it's not`.

**Why it's not safe to auto-fix mechanically:**

1. Adding to `workspace.members` (62 entries) would make them workspace
   members. Some have `[package] workspace = "..."` already pointing at a
   different parent (e.g. `agile-plus` is a sub-workspace). Need parent-aware
   routing.
2. Converting `version.workspace = true` to concrete values breaks the
   version-sync invariant the project likely depends on. Need a project-wide
   version (e.g. `0.1.0` or `0.5.0`).
3. Pattern A manifests often reference sibling workspace members via
   `{ workspace = true }` in deps (e.g. `serde_json.workspace = true`).
   Even after `version` is inlined, the dep refs still need entries in
   `[workspace.dependencies]` of whatever workspace they end up in.

**Two disposition options:**

**Option A.1 (lowest risk):** Add all 62 to root `workspace.members` + add
their sibling deps to root `[workspace.dependencies]`. Requires expanding
root `[workspace.dependencies]` from 2 entries (`substrate-core`,
`substrate-serve-lock`) to ~10 entries (serde, serde_json, tokio,
thiserror, chrono, tracing, anyhow, reqwest, async-trait, futures, etc.).

**Option A.2 (more invasive):** Convert all `package.*.workspace = true` and
`workspace = true` deps in these 62 manifests to concrete values. Risk:
duplicates version-stamping work that would need to be re-done on every
release.

**Recommendation:** Option A.1. It is the less invasive change and matches
the project's apparent design (these 62 were *meant* to be workspace
members). One operator approval, one PR.

### Pattern A full list (62)

```
[1]  absorption/PhenoInfra/infrakit/crates/phenotype-event-sourcing/phenotype-event-sourcing/Cargo.toml
[2]  crates/agent-forecast/Cargo.toml
[3]  crates/agile-plus/crates/agileplus-artifacts/Cargo.toml
[4]  crates/agile-plus/crates/agileplus-benchmarks/Cargo.toml
[5]  crates/agile-plus/crates/agileplus-convoy/Cargo.toml
[6]  crates/agile-plus/crates/agileplus-factory/Cargo.toml
[7]  crates/agile-plus/crates/agileplus-grpc/Cargo.toml
[8]  crates/agile-plus/crates/agileplus-hook/Cargo.toml
[9]  crates/agile-plus/crates/agileplus-import/Cargo.toml
[10] crates/agile-plus/crates/agileplus-integration-tests/Cargo.toml
[11] crates/agile-plus/crates/agileplus-nats/Cargo.toml
[12] crates/agile-plus/crates/agileplus-p2p/Cargo.toml
[13] crates/agile-plus/crates/agileplus-pipeline/Cargo.toml
[14] crates/agile-plus/crates/agileplus-refinery/Cargo.toml
[15] crates/agile-plus/crates/agileplus-spec-harmonizer/Cargo.toml
[16] crates/agile-plus/crates/agileplus-witness/Cargo.toml
[17] crates/agile-plus/crates/phenotype-mcp-sdk-rs/Cargo.toml
[18] crates/agile-plus/crates/shared-traceability/Cargo.toml
[19] crates/agileplus-api/Cargo.toml
[20] crates/agileplus-benchmarks/Cargo.toml
[21] crates/agileplus-graph/Cargo.toml
[22] crates/agileplus-nats/Cargo.toml
[23] crates/agileplus-sqlite/Cargo.toml
[24] crates/agileplus-telemetry/Cargo.toml
[25] crates/airlock-v2/Cargo.toml
[26] crates/anthropic-usage-poll/Cargo.toml
[27] crates/bench-guard/Cargo.toml
[28] crates/clap-ext-examples/Cargo.toml
[29] crates/connector-testkit/Cargo.toml
[30] crates/focus-always-on/Cargo.toml
[31] crates/focus-asset-fetcher/Cargo.toml
[32] crates/focus-calendar/Cargo.toml
[33] crates/focus-connectors-mock-familycontrols/Cargo.toml
[34] crates/focus-demo-seed/Cargo.toml
[35] crates/focus-ir/Cargo.toml
[36] crates/focus-mascot/Cargo.toml
[37] crates/focus-release-bot/Cargo.toml
[38] crates/focus-replay/Cargo.toml
[39] crates/focus-rituals/Cargo.toml
[40] crates/focus-rules/Cargo.toml
[41] crates/focus-scheduler/Cargo.toml
[42] crates/focus-storage/Cargo.toml
[43] crates/focus-sync/Cargo.toml
[44] crates/focus-sync-store/Cargo.toml
[45] crates/focus-transpilers/Cargo.toml
[46] crates/gateway/Cargo.toml
[47] crates/gateway-tools/Cargo.toml
[48] crates/klipdot-capture/Cargo.toml
[49] crates/perfharness/Cargo.toml
[50] crates/pheno-context/Cargo.toml
[51] crates/pheno-errors/Cargo.toml
[52] crates/phenotype-cache-adapter/Cargo.toml
[53] crates/phenotype-diff/Cargo.toml
[54] crates/phenotype-flags/Cargo.toml
[55] crates/phenotype-logging/Cargo.toml
[56] crates/phenotype-resilience/Cargo.toml
[57] crates/phenotype-shared-config/Cargo.toml
[58] crates/phenotype-state-machine/Cargo.toml
[59] crates/phenotype-telemetry/Cargo.toml
[60] crates/phenotype-test-fixtures/Cargo.toml
[61] crates/sidekick-messaging/Cargo.toml
[62] crates/teamcomm-mcp/Cargo.toml
[63] crates/temporal-grounding/Cargo.toml
[64] infrakit/crates/phenotype-event-sourcing/phenotype-event-sourcing/Cargo.toml
```

**Sub-workspace candidates (3):**
- `absorption/PhenoInfra/infrakit/crates/phenotype-event-sourcing/phenotype-event-sourcing/Cargo.toml` (1)
- `infrakit/crates/phenotype-event-sourcing/phenotype-event-sourcing/Cargo.toml` (1)
- 16 under `crates/agile-plus/crates/...` — this is a sub-workspace
  (root `agile-plus/Cargo.toml`)

The 16 `crates/agile-plus/crates/...` Pattern A entries likely need to be
added to `crates/agile-plus/Cargo.toml` `members = []`, not root. (This
requires verifying the agile-plus sub-workspace has the right
`[workspace.package]` and `[workspace.dependencies]` set up.)

---

## 3. Pattern B: Concrete version but broken deps (31 live)

**Symptom:** `[package] version = "0.1.0"` (concrete) is present, but deps
reference `workspace = true` for crates not in the workspace's
`[workspace.dependencies]`.

**Why it's not safe to auto-fix mechanically:** the parent workspace
(root or PhenoInfra) only has 2 entries in `[workspace.dependencies]`
(`substrate-core`, `substrate-serve-lock`). The 31 Pattern B manifests
reference common deps like `tokio`, `serde`, `tracing` etc. with
`workspace = true`, but those don't exist as workspace deps. The right
fix is one of:

**Option B.1:** Add the needed deps to root `[workspace.dependencies]`
(similar to Option A.1) and keep all 31 manifests as workspace members.

**Option B.2:** Convert `workspace = true` deps to concrete mode versions
in each of the 31 manifests. Mode versions from cargo metadata analysis
(2026-10-09):
```
tokio      ^1.42   (55 occurrences across all 230 manifests)
anyhow     ^1.0    (20)
thiserror  ^2.0    (39)
serde      ^1.0    (67)
serde_json ^1.0    (61)
reqwest    ^0.12   (12)
url        ^2.5    (n/a, not in top 20)
chrono     ^0.4    (29)
tracing    ^0.1    (25)
axum       ^0.8    (n/a, not in top 20)
uuid       ^1.0    (n/a, not in top 20)
```

A pilot fix script (B.2) was attempted 2026-10-09 and reverted
immediately because (a) 22/33 still failed after the dep conversion
(package.*.workspace=true fields also needed inlining) and (b) some
manifests reference unknown workspace deps (e.g. workspace-internal
path deps). B.2 needs a per-manifest hand audit to be safe.

**Recommendation:** Option B.1 if going down the workspace-membership
route; B.2 only with operator sign-off and a per-manifest audit script
that can detect the workspace-internal path deps.

### Pattern B full list (31 live, 2 in absorption/PhenoInfra)

```
[1]  absorption/PhenoInfra/iac/oci-helpers/Cargo.toml
[2]  absorption/PhenoInfra/infrakit/crates/phenotype-contract/Cargo.toml
[3]  crates/clap-ext/Cargo.toml
[4]  crates/configra-ops/Cargo.toml
[5]  crates/focus-ci-watcher/Cargo.toml
[6]  crates/focus-observability/Cargo.toml
[7]  crates/llm-router/Cargo.toml
[8]  crates/logkit/Cargo.toml
[9]  crates/mcp-server/Cargo.toml
[10] crates/pheno-compose-pheno-config/Cargo.toml
[11] crates/pheno-config/Cargo.toml
[12] crates/pheno-embedding/Cargo.toml
[13] crates/pheno-fs/Cargo.toml
[14] crates/phenoctl/Cargo.toml
[15] crates/phenotype-casbin-wrapper/Cargo.toml
[16] crates/phenotype-config-loader/Cargo.toml
[17] crates/settly/Cargo.toml
[18] crates/stashly/Cargo.toml
[19] crates/teamcomm-smoke/Cargo.toml
[20] _archived/nvms-ffi/Cargo.toml  (archived, exclude)
[21] _archived/pheno-compose/Cargo.toml  (archived, exclude)
[22] infrakit/crates/phenotype-contract/Cargo.toml  (path-relative; possibly stale)
... 11 more in scripts below ...
```

Full reproducible list: `python3 /tmp/categorize-complex.py > /tmp/e24-full.txt`
or run `/tmp/categorize-complex.py` (committed in `~/.jcode/scratch/`).

---

## 4. Anomaly (1)

`crates/.../Cargo.toml` — passes Pattern A and Pattern B filters but still
emits "current package believes it's in a workspace when it's not". Likely
an edge case (e.g. a stale `[workspace]` table in a non-workspace manifest,
or a `package.workspace = "..."` field pointing at a non-existent
workspace). Needs hand diagnosis.

---

## 5. Archived (4)

```
_archived/nvms-ffi/Cargo.toml
_archived/pheno-compose/Cargo.toml
```

(plus 2 in Pattern B; all 4 are in `_archived/`, already excluded by E2.3
`.gitignore` style logic). These are kept for historical reference but
should not be touched.

---

## 6. Disposition recommendations (operator decision)

**Recommended single-batch fix (Option A.1 + B.1 combined):**

1. **Add 62 Pattern A to root `workspace.members`** (or per-sub-workspace
   if sub-workspace-specific).
2. **Expand root `[workspace.dependencies]`** from 2 to ~12 entries:
   `substrate-core`, `substrate-serve-lock`, `serde`, `serde_json`, `tokio`,
   `thiserror`, `chrono`, `tracing`, `anyhow`, `reqwest`, `async-trait`,
   `futures`.
3. **Add `[workspace.package] version = "0.1.0"` (or whatever the project
   version is) to root `Cargo.toml`.**
4. **Add 31 Pattern B to root `workspace.members` too** (they have
   concrete versions but their `workspace = true` deps will resolve once
   the deps are added to `[workspace.dependencies]`).
5. Verify `cargo metadata` passes for the full workspace.
6. Run Quality Gate.

**Risk estimate:** low. The change is additive (new entries to existing
tables) and well-bounded. The only risk is that some of the 93 added
members have inter-dependencies that fail to resolve, but cargo's
metadata will catch that before commit.

**Alternative smaller-batch fix (2 PRs):**

PR 1 (lower risk): 62 Pattern A only — add to members + add `[workspace.package]`
+ add `[workspace.dependencies]`.
PR 2 (medium risk): 31 Pattern B — same change as PR 1 but for B only.

Either way, this is 1-2 PRs of work, not 9. The mechanical subset
(Pattern B dep-only fix) is too brittle to commit.

---

## 7. Reproduction

```bash
cd /Users/kooshapari/CodeProjects/Phenotype/repos/PhenoShared

# Recategorize
python3 /tmp/categorize-complex.py

# Pilot script (DEPRECATED, reverted)
# python3 /tmp/fix-pattern-b.py  # only fixed 11/33, broke 22

# Verify
for mf in $(cat /tmp/e24-pattern-b.txt); do
  cargo metadata --no-deps --offline --manifest-path "$mf" --format-version=1 \
    > /dev/null 2>&1 || echo "STILL BROKEN: $mf"
done
```

Scripts:
- `/tmp/categorize-complex.py` — current categorization (Pattern A, B, anomaly, archived)
- `/tmp/fix-pattern-b.py` — pilot script (DEPRECATED, 11/33)
- `/tmp/recategorize.py` — re-categorize after fix attempt

---

## 8. Gate impact

- **Quality Gate:** currently at 10 consecutive greens on main
  (HEAD `23f25ad9`).
- **No change to Quality Gate from this audit.** E2.4 is *not* a CI
  blocker — the 94 broken belief-error manifests don't run as part of the
  gate (they're excluded from `cargo metadata` scope or don't have
  `[package] workspace` set up for the gate to traverse).
- **However:** if/when someone runs `cargo metadata` against the whole
  repo (e.g. a `cargo workspaces` invocation or a future `all-features`
  gate), the 94 will surface as errors.

---

## 9. Operator sign-off requested

Recommended actions (any one of):

**A.** Approve Option A.1 + B.1 batch fix; I'll generate the patch in
a 10m task, run Quality Gate, push.

**B.** Approve 2-PR split (Pattern A first, Pattern B second).

**C.** Defer E2.4 to a later session (current E1 streak is the priority;
E2.4 can be a separate piece of work).

**D.** Other — please specify.

---

*End of audit. Ledger refs: E1 10-greens `23f25ad9`; E2.3 161/161
`93818948`; pilot B script `/tmp/fix-pattern-b.py` (reverted).*
