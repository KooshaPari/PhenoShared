# SessionLedger 5-day long-horizon loop

**Repo:** [KooshaPari/SessionLedger](https://github.com/KooshaPari/SessionLedger)  
**Horizon:** 2026-07-18 → 2026-07-23 (5 days)  
**Cadence:** audit → exec every **10 minutes**  
**Phase:** Wave-40 closure → Wave-41+

## Horizon summary

| Window    | Focus                                | Exit signal                                           |
| --------- | ------------------------------------ | ----------------------------------------------------- |
| Jul 18–20 | Wave-40 merge chain + red CI triage  | #328 → #325 → #327 → reaudit PR green and mergeable   |
| Jul 20–22 | Wave-40 reaudit merge; score refresh | Reaudit merged at **≥396/402** (≥98% A)               |
| Jul 22–23 | Wave-41 scope lanes + org mirror     | Org mirror unblocked; Wave-41 width-5 lanes advancing |

**Base score (Wave-39 closure):** 394/402 (98% A) per [`audit/SCORECARD.md`](../../audit/SCORECARD.md).

---

## 10-minute tick prompt (copy-paste)

Run this verbatim each loop tick:

```
Execute SESSION_LEDGER_5DAY_LOOP.md 10m tick for KooshaPari/SessionLedger.

1) Wave-40 merge chain — via gh, in order:
   - gh pr view 328 --json state,mergeable,statusCheckRollup,headRefName,baseRefName
   - gh pr view 325 --json state,mergeable,statusCheckRollup,headRefName,baseRefName
   - gh pr view 327 --json state,mergeable,statusCheckRollup,headRefName,baseRefName
   - Find open reaudit PR (search: "Wave-40" OR "w40-reaudit" OR label:w40-reaudit)
   Report: which PR is next to merge; if blocked, one concrete fix to unblock.

2) CI triage — for the active PR in the chain:
   - gh pr checks <num> --watch=false
   - Treat CodeRabbit review comments and Kilo/agent-CLI flakes as NON-BLOCKING unless they map to a failing required check.
   - For each RED required check: name, log URL, smallest fix (rebase, script, workflow, test).

3) Advance one unit of work this tick:
   - If merge chain unblocked: merge exactly ONE PR (lowest number still open), then stop.
   - Else: push one fix commit to the blocked PR branch OR rebase onto origin/main.

4) Stale lane scan:
   - gh pr list --repo KooshaPari/SessionLedger --state open --limit 30
   - List worktrees: git -C C:\workspace\SessionLedger worktree list
   - Flag lanes with no commit in >24h, failing required checks >6h, or branch behind main >3 commits.

5) Wave-41 ROI pick (if Wave-40 chain waiting on human/creds):
   - If WAVE41_*_SCOPE.md exists at repo root, read it and pick highest-ROI stability/perf/dx item not yet in-flight.
   - Else skim docs/ops/GAP_QA_MATRIX.md partial rows (C04, C08, C11) for machine-actionable gaps.

6) Disk hygiene (when C: or worktree disk >85%):
   - Remove stale build dirs: Get-ChildItem C:\workspace\SessionLedger-wtrees -Directory -Filter 'target-*' -Recurse -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
   - Never delete in-use worktrees; skip dirs with active cargo processes.

7) End report (required):
   - main SHA: git -C C:\workspace\SessionLedger rev-parse --short origin/main
   - score: latest from audit/SCORECARD.md (x/402, grade)
   - next PERT step: from docs/ops/WAVE40_PERT.md or WAVE41_PERT.md if present
   - blockers: human gates, creds, archived org mirror, disk, CI
```

---

## Wave-40 merge chain (reference)

Sequential merge order (rebase siblings after each `main` move):

```
#328 (first feature) → #325 → #327 → Wave-40 reaudit PR
```

After each merge:

```powershell
git -C C:\workspace\SessionLedger fetch origin
# Rebase open siblings onto origin/main before merging the next PR
```

---

## Parallel lane template (width-5 waves)

Use for Wave-41+ scope waves. Mirror Wave-39 structure.

### Scope file

Create `WAVE41_SCOPE.md` at repo root with:

- Base `origin/main` SHA
- Five prioritized gaps from GAP_QA_MATRIX / SCORECARD unpaid list
- Lane table (branch, worktree, cluster/pillar, score expectation)
- Merge order (lowest conflict risk first)
- Rules: no audit file edits in feature PRs; reaudit PR only

### Five lanes

| Slot | Branch pattern       | Worktree path                                    | Lane doc                          |
| ---- | -------------------- | ------------------------------------------------ | --------------------------------- |
| L1   | `feat/sl-w41-<slug>` | `C:\workspace\SessionLedger-wtrees\w41-<slug>` | `lanes/w41-<slug>/WAVE41_LANE.md` |
| L2   | `feat/sl-w41-<slug>` | `...\w41-<slug>`                                 | same                              |
| L3   | `feat/sl-w41-<slug>` | `...\w41-<slug>`                                 | same                              |
| L4   | `feat/sl-w41-<slug>` | `...\w41-<slug>`                                 | same                              |
| L5   | `feat/sl-w41-<slug>` | `...\w41-<slug>`                                 | same                              |

### Lane bootstrap (per lane)

```powershell
$slug = '<slug>'
$wt = "C:\workspace\SessionLedger-wtrees\w41-$slug"
git -C C:\workspace\SessionLedger worktree add -B "feat/sl-w41-$slug" $wt origin/main
$env:CARGO_TARGET_DIR = "target-w41-$slug"
```

### Lane PR checklist

- [ ] `lanes/w41-<slug>/WAVE41_LANE.md` with gap, acceptance, verify commands
- [ ] No edits to `audit/SCORECARD.md`, `GAP_QA_MATRIX.md`, `TRACEABILITY.json`, `WBS.md` status
- [ ] `CARGO_TARGET_DIR=target-w41-*`; never `git add -A` with target dirs
- [ ] CHANGELOG Unreleased bullet on feature PRs
- [ ] `pwsh ./docs/ops/traceability_lint.ps1` + `cargo test --locked` before push

### PERT companion

Add `docs/ops/WAVE41_PERT.md`:

| ID         | Activity                 | Pred  | Est (h)  | Owner   |
| ---------- | ------------------------ | ----- | -------- | ------- |
| W41-A      | Scope + WBS/DAG/PERT     | —     | 1        | machine |
| W41-B1..B5 | Parallel impl (5 lanes)  | W41-A | 2–4 each | machine |
| W41-C      | Sequential merge (5 PRs) | B1–B5 | 2        | machine |
| W41-D      | Reaudit + traceability   | W41-C | 2        | machine |
| W41-E      | Org mirror               | W41-D | 1        | human   |

**Parallel width:** 5. **Critical path:** A → slowest B* → C → D.

---

## Stop conditions

Stop the 10-minute loop when **all** of the following are true:

1. **Wave-40 reaudit merged** with score **≥396/402** (≥98% A) recorded in `audit/SCORECARD.md`.
2. **Org mirror unblocked** — `phenotype-org-audits` mirror PR merged or explicitly N/A with human sign-off in WBS-9.x.
3. **No open Wave-40 PRs** in the merge chain (#328, #325, #327, reaudit).
4. **Wave-41 scope PR merged** OR horizon date **2026-07-23** reached (whichever comes first).

If stopped early for score target, leave a final tick note: main SHA, final score, Wave-41 next action.

---

## Loop sentinel (agent wake)

Background tick emits:

```
AGENT_LOOP_TICK_SESSIONLEDGER {"prompt":"Execute SESSION_LEDGER_5DAY_LOOP.md 10m tick: merge chain, CI triage, Wave-41 scope, disk hygiene. Report main SHA and next action."}
```

Arm with:

```powershell
while ($true) {
  Start-Sleep -Seconds 600
  Write-Output 'AGENT_LOOP_TICK_SESSIONLEDGER {"prompt":"Execute SESSION_LEDGER_5DAY_LOOP.md 10m tick: merge chain, CI triage, Wave-41 scope, disk hygiene. Report main SHA and next action."}'
}
```

---

## Related docs

- [`WAVE39_SCOPE.md`](../../WAVE39_SCOPE.md) — prior wave template
- [`docs/ops/WAVE39_PERT.md`](WAVE39_PERT.md) — PERT pattern
- [`docs/ops/GAP_QA_MATRIX.md`](GAP_QA_MATRIX.md) — gap priorities
- [`WORK_DAG.md`](../../WORK_DAG.md) — dependency graph
