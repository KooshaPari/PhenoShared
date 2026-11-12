# host-ops closure ledger — read-only reconnaissance (2026-11-12)

TARGET: `/Users/kooshapari/CodeProjects/host-ops` (branch `main`, HEAD `9cef881`).

## 1. Schema of INTENTS.md

Top: header block + rules + "Add an intent" instructions. Then one section per
intent:

```
## I<n> — <title>

**Intent.** <prose, may include a quoted operator prompt>

| ID | Deliverable | Closed when |
|----|-------------|-------------|
| D<n>.<m> | <deliverable name> | <closure definition / check command> |
```

- Intent heading: `## I<n> — <title>` (H2). Deliverables: markdown table with
  columns `ID | Deliverable | Closed when`. IDs are `D<n>.<m>` (e.g. `D11.4`).
  The "Closed when" cell is the executable acceptance condition, usually a
  literal command + expected value. Optional trailing prose paragraphs after the
  table are allowed (I10, I14).
- Intent title is also registered in `scripts/config.sh` via `intent_title()`
  (case statement keyed on `I<n>`).

Complete template (I14, trimmed):

```
## I14 — Delegation routing stays within policy and has a healthy route

**Intent.** ...at any moment the fleet must be able to route work...

| ID | Deliverable | Closed when |
|----|-------------|-------------|
| D14.1 | A healthy route exists | `agent-routes --pick` exits 0 and names a route |
| D14.2 | The route that would serve is policy-legal | the picked model id is not one of `ROUTING_FORBIDDEN` (exact match) |
```

File: `closure/INTENTS.md` (full file, 240 lines).

## 2. Cell vocabulary

Defined in `closure/scripts/render.py` ORDER list and STATE.json policy.cells:

`PASS, FAIL, NOT_RUN, UNKNOWN, STALE, BLOCKED, NOT_APPLICABLE` (7 cells).
MARK maps them to display strings (e.g. `NOT_RUN` -> `NOT RUN`, `NOT_APPLICABLE` -> `N/A`).

Rollup (worst-first) in render.py:

```
ORDER = ["FAIL", "BLOCKED", "UNKNOWN", "NOT_RUN", "STALE", "NOT_APPLICABLE", "PASS"]
def worst(states): for s in ORDER: if s in states: return s
```

So an intent's rollup is the first (worst) cell in ORDER that appears among its
deliverables. `STALE` is applied per-deliverable in render.py when a deliverable
has stayed in `FAIL/UNKNOWN/BLOCKED/NOT_RUN` for >= STALE_DAYS (14, from
config.sh) since the previous STATE.json timestamp.

Exit codes (closure-check header): 0 if all PASS/N/A; 1 if any FAIL; 2 if any
UNKNOWN/BLOCKED/STALE/NOT_RUN.

## 3. Check row contract

Checks are declarative `bash` calls to `row()`:

```
row() { # id intent state evidence source
  printf '%s\t%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$4" "$5" >>"$ROWS"
}
```

Invocation form: `row <ID> <INTENT> <STATE> <EVIDENCE> <SOURCE>` (tab-separated
into `$ROWS` mktemp file). Example (closure-check:234):

```
MERGED) row D1.1 I1 PASS "PR #267 state=MERGED" "gh pr view 267 --json state" ;;
```

So checks are shell-command-driven (each cell computes a state by running a
command such as `gh`, `probe`, `find`, `git`), then calls `row` with one of
the 7 states. The "source" field is the command string cited in TREE.md/STATE.json.

Checks live in `closure/scripts/closure-check` (main) plus sourced files
`checks/{estate,launchd,ledger,routing}.sh`. `config.sh` holds constants
(EXPECT_CRED_MD5, STALE_DAYS, ROUTING_FORBIDDEN, intent_title, etc.).

## 4. How to add an intent

Per `closure/INTENTS.md` "Adding an intent" section:

1. Append `## I<n> — <title>` section + deliverable table to `closure/INTENTS.md`.
2. Add one `row` call per deliverable in `closure/scripts/closure-check`
   (and/or a sourced checks/*.sh), using IDs `D<n>.<m>`.
3. Register the title in `scripts/config.sh` `intent_title()` case statement.
4. Run `closure/scripts/closure-check` (it writes TREE.md + STATE.json via
   render.py; exits non-zero if FAIL).
5. Commit all three together (INTENTS.md + closure-check + config.sh + the
   generated TREE.md + STATE.json). The Markdown tree and JSON sidecar must
   never disagree.

Invariants:
- IDs in INTENTS.md must match IDs in closure-check row calls (script prints
  the ID).
- TREE.md and STATE.json are regenerated together by render.py from the same
  $ROWS; never hand-edit either.
- intent_title() in config.sh must have a case for the new I<n> (else
  "Unregistered intent").

## 5. The dirty five (5 modified + 3 untracked)

`git diff --stat` (closure/INTENTS.md +1; closure/STATE.json +53/-42;
closure/TREE.md +51/-41; closure/scripts/closure-check +33/-1;
closure/scripts/desk-probe.sh +29/-0). Untracked: `bin/desk-watchdog.sh`,
`systemd/desk-watchdog.service`, `systemd/desk-watchdog.timer`.

Changes:
- INTENTS.md: added D11.4 deliverable row (estate guard running) to I11.
- closure-check: added D11.4 check block probing watchdog timer/log age.
- desk-probe.sh: added watchdog_last_raw / watchdog_trigger_age_s /
  watchdog_timer_active / watchdog_log_age_s / watchdog_log_size probes.
- TREE.md + STATE.json: regenerated sidecar pair reflecting the new D11.4 row.
- New untracked watchdog unit files + script (estate guard being added).

Safety: this looks like a half-finished, in-progress edit. closure-scheduled
explicitly SKIPS evaluation when `closure/scripts` is dirty (it says "never
evaluate a tree that is being edited"). The new watchdog code references
`watchdog_service_status` in INTENTS.md but the probe emits `watchdog_timer_active`,
not `watchdog_service_status` — an internal inconsistency that has not been
reconciled. DO NOT commit/stage/push on top; another actor is mid-work.

## 6. Scheduler

- Job label: `com.kooshapari.closure-check`.
- Plist: `launchd/com.kooshapari.closure-check.plist` (in repo).
- ProgramArguments runs `/bin/bash .../closure/scripts/closure-scheduled`.
- StartCalendarInterval: 00:23, 06:23, 12:23, 18:23 (4x/day). RunAtLoad true.
- PhenoAuditExitIsProgress=1,2 (exit 1 = FAIL, 2 = UNKNOWN are progress codes).
- closure-scheduled runs closure-check, then commits ONLY closure/TREE.md +
  closure/STATE.json (path-scoped), then pushes. It skips entirely if
  closure/scripts is dirty.

A second scheduler would duplicate: (a) the evaluation itself, (b) the
path-scoped commit of TREE.md/STATE.json, (c) the push — causing commit
races/conflicts and a permanent false alarm. The repo explicitly forbids a
second copy ("one ledger, one evaluator"; `bin/scope-closure` was written and
deleted for this reason).

## Final report (one line each)

1. INTENTS.md schema: H2 `## I<n> — <title>`, `**Intent.**` prose, deliverable table `| ID | Deliverable | Closed when |` with IDs `D<n>.<m>`; title also registered in config.sh intent_title().
2. Cell vocab: PASS/FAIL/NOT_RUN/UNKNOWN/STALE/BLOCKED/NOT_APPLICABLE in render.py ORDER; rollup = worst cell in ORDER among deliverables.
3. Check row: `row <ID> <INTENT> <STATE> <EVIDENCE> <SOURCE>` tab-separated into $ROWS; shell-command-driven (gh/probe/find/git), defined in closure-check + checks/*.sh.
4. Add intent: append to INTENTS.md, add row calls + config.sh title, run closure-check (regenerates TREE.md+STATE.json), commit all together; IDs must agree, sidecar pair must not disagree.
5. Dirty five: in-progress D11.4 watchdog addition (INTENTS + closure-check + desk-probe + regenerated TREE/STATE + 3 untracked watchdog files); half-finished, do not touch.
6. Scheduler: launchd label `com.kooshapari.closure-check`, plist `launchd/com.kooshapari.closure-check.plist`, fires 00/06/12/18:23, commits only TREE.md+STATE.json then pushes; a second copy duplicates evaluation+commit+push and is explicitly forbidden.

Written: `/Users/kooshapari/CodeProjects/Phenotype/repos/PhenoShared-space/feat/researchledger-ingest-v2/wtree/docs/sessions/2026-11-11-asks-instinct-closure-ledger/evidence/hostops_closure_recon.md`
`, file_path="/Users/kooshapari/CodeProjects/Phenotype/repos/PhenoShared-space/feat/researchledger-ingest-v2/wtree/docs/sessions/2026-11-11-asks-instinct-closure-ledger/evidence/hostops_closure_recon.md", intent="Write read-only reconnaissance findings to target evidence file