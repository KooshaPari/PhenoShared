# dagrun — forward WBS

Reporting rule (operator, 2026-10-28): this WBS is printed at the end of every
working turn. The unit of reporting is the **epic / feature / improvement**.
Ephemeral work — PR merges, typo fixes, single-file edits, one-command chores —
is deliberately **not** a line item; it is a subtask of a subtask and is implied
by whatever feature is marked in progress.

States: `DONE` · `WIP` · `NEXT` · `LATER` · `BLOCKED(by x)`.

Every `DONE` below cites the artefact that proves it. A state that cannot name
its evidence is `UNKNOWN`, not `DONE`.

## Where we are

v1.2.0 on `main`. `plan / run / next / claim / done / fail / skip / status /
validate / trace / export / submit / import / detect / viz / draft / explain /
doctor / gc / workspace / timeline / stats / lint / critique / review / template
/ skill / query / recover / mcp` all work, and the offline path is proven end to
end: a 9-node plan installs with PERT/WBS numbers, runs, verifies each node from
the filesystem, fails closed on an unsatisfiable contract, propagates blocked
dependencies, and exports to both Tracera and AgilePlus shapes.

Live-model dispatch is proven for three harness families and blocked for two,
for reasons outside dagrun (see 1.1). The suite is green on a host whose global
git config installs a commit hook.

This revision is a reconciliation pass: the previous version had drifted behind
the code, listing nine shipped features as `NEXT` or `LATER`, which made the
"next three" list wrong. Every state below was re-derived by reading the code,
not by reading the previous roadmap.

## Epics

```
1.0  VERIFIED AUTONOMY ......................... PARTIAL 4/5 harness families blocked externally
2.0  FLEET CONCURRENCY ......................... DONE    20 x 4 held, cross-process proven
3.0  PLAN AUTHORING ............................ DONE    draft, lint, replan, templates
4.0  CONTRACTS THAT CATCH SLOP ................. DONE    kind checks, coherence, anti-gaming
5.0  TRACE AS A PRODUCT ........................ PARTIAL submit + query + OTel exporter
6.0  AGILEPLUS INTEROP ......................... PARTIAL import yes, round trip no
7.0  MULTI-REPO INTENTS ........................ DONE    sub-plans, cross-repo gate, budgets
8.0  EXTENSIBILITY SURFACES .................... DONE    MCP, skill, hooks
9.0  OPERATIONAL HARDENING ..................... PARTIAL recover + schema yes, disk-full no
10.0 DECISION QUALITY .......................... DONE    calibration, CVP, marginal, review
11.0 DYNAMIC DECOMPOSITION ..................... DONE    discover / fan_out / fan_in
```

## 1.0 VERIFIED AUTONOMY — can an operator walk away?

Gate: an unattended overnight run finishes or fails with a reason the operator
can act on without reading logs.

```
1.1 Real-harness proof across families                         PARTIAL 3/5
    1.1.1 jcode: one RESEARCH node, verified, usage recorded        DONE
    1.1.2 codex: one IMPL node, sandbox=workspace-write, verified   DONE
    1.1.3 forge: one DOC node, exit-code semantics confirmed        DONE
    1.1.4 kcode parity vs jcode        BLOCKED(external: the fork's credential store is empty)
    1.1.5 helioslite                   BLOCKED(external: needs a pty, then still prompts)
    ▸ evidence: docs/harness-proof.md — jcode 18.5s · codex 22.4s · forge 12.0s, each
      ending done=1 failed=0 after verify.Node read the file off disk

1.2 Cost and time accounting                                  DONE
    1.2.1 usage parsed from harness JSON into NodeState             DONE
    1.2.2 `stats`: p50/p95 by kind, adoption rate, retry rate       DONE
    1.2.3 plan-level max_cost_usd; no new node claimed past it      DONE
    ▸ evidence: internal/harness/usage.go + usage_parse.go (jcode/kcode/codex streams),
      internal/plan/budget.go (Budget, cost clamping), cmd_stats.go,
      internal/plan/plan.go MaxCostUSD, cmd_run.go maxCostUSD
    GATE: any run can be budgeted before it starts                  PASS

1.3 Failure taxonomy                                          DONE
    1.3.1 classify: harness_missing | harness_error | timeout |
          contract_miss | cap_blocked | dep_blocked                DONE
    1.3.2 class persisted; surfaced in status and explain            DONE
    1.3.3 retry policy per class; contract_miss never blind-retried  DONE
    ▸ evidence: internal/run/failure.go (Classify, isProviderFailureClass),
      exec.go retryOrFail(n, class), store.SetFailureClass,
      a provider throttle becomes a retryable pause with backoff and a cooldown
    GATE: every failure names one class and one action               PASS

1.4 Crash-recovery proof                                      DONE
    1.4.1 SIGKILL a contender mid-claim; assert exactly one claim survives  DONE
    1.4.2 truncated state is refused, never half-read                        DONE
    1.4.3 rerun adopts a completed node; side effects happen once            DONE
    ▸ evidence: internal/store/crash_test.go; the re-exec helper spawns the test
      binary itself rather than a separate program
    GATE: recovery is tested, not asserted                                  PASS
```

## 2.0 FLEET CONCURRENCY — does it hold at N x M?

Gate: 20 executor processes x 4 workers on one repo for an hour, zero
corruption, zero duplicate node executions.

```
2.1 State scaling                                             DONE
    2.1.1 benchmark state rewrite at 500 nodes                      DONE
    2.1.2 lock-wait measured under load; no sharding needed yet      DONE
    2.1.3 backoff + contention report                               DONE
    ▸ evidence: internal/store/scale_test.go — BenchmarkClaim500Nodes,
      TestLockWaitUnderLoad, TestLockTransitionCost, TestStateSizeAt500Nodes;
      scale_on.go / scale_off.go behind the `scale` build tag
    GATE: p95 lock wait under the target load is MEASURED            PASS

2.2 Working-tree isolation                                    DONE
    2.2.1 git worktree + branch per node                            DONE
    2.2.2 merge-back policy: leave the branch, manual by design      DONE
    2.2.3 plan-time rejection of overlapping file_scope              DONE
    ▸ evidence: internal/run/worktree.go, internal/plan/overlap.go + overlap_test.go
    GATE: two IMPL nodes edit in parallel without touching each other PASS

2.3 Admission control                                         DONE
    2.3.1 role -> provider map; cap per provider, not just per role  DONE
    2.3.2 queue depth in the run summary; `run --wait D` bounds the
          wait for capacity instead of exiting on a partial run      DONE
    2.3.3 graceful drain on SIGTERM                                 DONE
    ▸ evidence: internal/plan/provider.go (NewAdmission/ApplyPolicy),
      internal/run/provider_admission_test.go, cmd_run.go reportQueue + --wait,
      signal.NotifyContext in cmd_run/cmd_mcp/cmd_workspace, procgroup SIGTERM
    GATE: a rate limit degrades throughput, never correctness         PASS

2.4 Multi-executor safety                                     DONE
    2.4.1 N independent processes on one .dagrun: exactly one winner  DONE
    2.4.2 no singleton assumption; every mutation goes through the lock DONE
    2.4.3 `status --watch D` live view, stops when every node is terminal DONE
    ▸ evidence: store_test.go TestClaimHasExactlyOneWinnerAcrossProcesses +
      TestClaimHelperProcess; cmd_view.go watchStatus/allTerminal
    GATE: 5 executors, one run, no duplicate work                     PASS
```

## 3.0 PLAN AUTHORING — how does the DAG get written?

Gate: an agent goes from one paragraph of intent to a validated plan without
hand-writing YAML.

```
3.1 Draft from intent                                         DONE
    3.1.1 `draft --intent FILE` emits a taxonomy-complete skeleton   DONE
    3.1.2 always emit INTENT, SPEC, TEST, GATE; infer the rest       DONE
    3.1.3 a model proposes the decomposition; dagrun validates        DONE
    ▸ evidence: cmd_draft.go, internal/plan/draft.go
    note: the emitted YAML is re-parsed and re-validated before it is written,
    so a draft that does not validate is never handed over
    GATE: paragraph in, runnable plan out                            PASS

3.2 Plan linter                                               DONE
    3.2.1 actionable messages per finding                            DONE
    3.2.2 semantic checks: impl_no_spec, unreachable, orphan_discovery,
          fanout_no_template, fanin_no_expansion, gate_soft,
          estimate_defaulted                                       DONE
    3.2.3 `critique` writes CRITIQUE.md as a non-blocking artefact    DONE
    ▸ evidence: cmd_lint.go, internal/plan/semantic.go, cmd_report.go cmdCritique
    GATE: a deliberately wrong plan gets a specific, fixable complaint PASS

3.3 Replanning                                                DONE
    3.3.1 diff old/new; unchanged node keeps its completion          DONE
    3.3.2 a changed contract invalidates the node and blocks         DONE
    3.3.3 `wouldDiscard` names verified work a revision would throw away DONE
    ▸ evidence: internal/plan/replan.go — Diff + ReplanDiff.AgainstDone
    note: plan must not import store, so Diff is pure and the caller supplies
    the verified set; that is what makes the refusal enforceable
    GATE: mid-run plan change never keeps a stale "done"              PASS

3.4 Templates                                                 DONE
    3.4.1 greenfield | bugfix | migration | audit | lint-sweep | next-usable-cvp DONE
    3.4.2 `template NAME [--out FILE]`, embedded in the binary        DONE
    3.4.3 examples stay green via the repo's own gate node             DONE
    ▸ evidence: internal/plan/templates/ embedded, cmd_template.go,
      Makefile `templates` target runs them through both linters
    GATE: 6 templates, each validated by the tool itself              PASS
```

## 4.0 CONTRACTS THAT CATCH SLOP — is "done" meaningful?

Gate: pasting one document into nine artifacts does not pass.

```
4.1 Kind-aware predicates                                     DONE
    4.1.1 SPEC: >=1 requirement, each with a WHEN/THEN scenario      DONE
    4.1.2 TEST: every SPEC requirement id referenced by >=1 test      DONE
    4.1.3 RESEARCH: >=2 distinct URLs + Decision + Alternatives       DONE
    4.1.4 SOTA: >=2 candidate headings on >=3 axes + explicit verdict DONE
    4.1.5 INTENT: acceptance criteria; UI: states + a11y; DOC: links resolve DONE
    ▸ evidence: internal/plan/requirements.go KindRequirements,
      internal/verify/kinds.go (checkSPEC/TEST/RESEARCH/SOTA/INTENT/UI/DOC),
      PlanKindCheck walks spec ancestors to resolve requirement ids
    GATE: a kind-specific placeholder fails its kind                  PASS

4.2 Coherence checks                                          DONE
    4.2.1 TEST<->SPEC id coverage across nodes                       DONE
    4.2.2 IMPL file_scope actually touched (diff-based)              DONE
    4.2.3 identical sha256 across nodes -> reported as a finding     DONE
    ▸ evidence: internal/verify/coverage_test.go, internal/plan/scope.go,
      internal/verify/antigaming.go CrossNodeDuplicates
    GATE: cross-node lies are caught                                  PASS

4.3 Anti-gaming                                               DONE
    4.3.1 placeholder markers (TODO/TBD/FIXME/lorem/placeholder) fail,
          except inside a fence or inline code where they are prose    DONE
    4.3.2 minimum distinct-line ratio catches repetition padding,
          with a 40-line floor so a short honest file is never punished DONE
    4.3.3 LLM review is annotation only, never the authority          DONE
    ▸ evidence: internal/verify/antigaming.go PlaceholderFindings, PaddingFindings;
      cmd_critique.go writes advice, never a verdict
    GATE: repetition-padding cannot satisfy a contract                PASS
```

## 5.0 TRACE AS A PRODUCT — can a human or Tracera read it?

```
5.1 Tracera submit                                            DONE
    5.1.1 `submit --url` POSTs; fails loud on a rejected payload    DONE
    5.1.2 emits the declaration record + content hash                DONE
    5.1.3 import comes back the other way                            DONE
    ▸ evidence: cmd_submit.go, cmd_import.go, internal/tracera
    GATE: a run is queryable in Tracera without hand-editing         PASS

5.2 Query surface                                             DONE
    5.2.1 `trace --node/--event/--since/--limit/--json`              DONE
    5.2.2 `explain NODE`: deps + last error + failed predicate + fix DONE
    5.2.3 `timeline` per run                                        DONE
    5.2.4 `query`: composable select over nodes — --where/--select/
          --order-by/--limit/--json                                  DONE
    ▸ evidence: cmd_view.go filterEvents/globMatch, cmd_explain.go,
      cmd_timeline.go, internal/query (Parse/Run/Validate/Render), cmd_query.go
    GATE: "why is this stuck" answers in one command                 PASS

5.3 OTel bridge                                               DONE
    5.3.1 one span per executed node, dag deps in attributes         DONE
    5.3.2 OTLP/JSON export, deterministic trace and span ids         DONE
    5.3.3 documented why the DAG lives in the relational tier        DONE
    ▸ evidence: internal/otel — Build/Write/WriteSpans; a parent link is only
      claimed when the dependency genuinely finished first, otherwise the node
      parents to the run root. Concurrency is not invented into causality.
    GATE: existing observability stacks can see runs                  PASS
```

## 6.0 AGILEPLUS INTEROP

```
6.1 Import path                                               DONE
    6.1.1 `import` reads a payload from a file or stdin              DONE
    6.1.2 reconstructs the plan; reports dropped items on stderr     DONE
    6.1.3 `export --format agileplus` emits an ImportBundle          DONE
    ▸ evidence: cmd_import.go + cmd_import_test.go, internal/export
    GATE: export output imports unchanged                            PASS

6.2 Round trip                                                DONE
    6.2.1 `import --from agileplus` reads the ImportBundle back           DONE
    6.2.2 wp sequence <-> node id map persisted (`agileplus.map.json`)    DONE
    6.2.3 conflicts reported, never auto-resolved                         DONE
    ▸ evidence: internal/agileplus — Parse/ToPlan/Conflicts/IDMap;
      cmd_import.go --from agileplus; the round-trip test asserts
      export -> parse -> plan -> export preserves slug, sequence, title,
      file_scope and deps
    note: an ImportBundle has no artifact-predicate field, so a re-imported
    artifact verifies EXISTENCE only. That loss is reported per work package
    rather than papered over with an invented predicate.
    GATE: import -> edit -> re-export preserves structure                PASS
```

## 7.0 MULTI-REPO INTENTS

```
7.1 Sub-plans                                                 DONE
    7.1.1 namespaced node ids across plan dirs                      DONE
    7.1.2 cross-plan dependency resolution                          DONE
    7.1.3 per-plan artifact roots                                   DONE
    7.1.4 cross-repo gating: repo B's node waits on repo A's        DONE
    ▸ evidence: internal/workspace/schedule.go (rewrites cross-repo deps),
      exec.go ("a node in repo R may start only when every..."), run.go
      externalBlockedReason, workspace.ArtifactsRoot override
    GATE: repo B's node can wait on repo A's node                    PASS

7.2 Workspace manifest                                        DONE
    7.2.1 `dagrun.workspace.yaml` listing repos + plans              DONE
    7.2.2 workspace rollup (`workspace.json`)                       DONE
    7.2.3 per-repo worker budgets, fair round-robin by least use     DONE
    ▸ evidence: internal/workspace/workspace.go (max_workers per repo,
      backward compatible when absent), budget.go
      (NewBudget/Acquire/Release/Runnable), schedule.go
    GATE: one command reports a multi-repo intent                    PASS
```

## 8.0 EXTENSIBILITY SURFACES — native use, no clever shell

```
8.1 MCP server                                                DONE
    8.1.1 `dagrun mcp` over stdio: 9 tools                          DONE
    8.1.2 stdout carries protocol frames only; logs to stderr        DONE
    8.1.3 local only, no auth                                       DONE
    ▸ evidence: cmd_mcp.go, internal/mcp; verified today: initialize and
      tools/list return 9 tools in one stdio session
    GATE: an MCP client drives a run without a shell                  PASS

8.2 Skill / slash wrappers                                    DONE
    8.2.1 /dagrun skill for jcode | kcode | codex | forge            DONE
    8.2.2 thin: one code path, the CLI                               DONE
    ▸ evidence: skills/dagrun/SKILL.md, cmd_skill.go (prints frontmatter + verbs),
      internal/skill
    note: the skill IS the surface; there is no second implementation to drift
    GATE: the same behaviour through every surface                    PASS

8.3 Hooks                                                     DONE
    8.3.1 pre-node, post-verify, on-fail shell hooks in the plan      DONE
    8.3.2 built-in git-commit ledger hook per verified node           DONE
    8.3.3 a failing hook never masks a verification result            DONE
    ▸ evidence: internal/hook/hook.go, internal/run/hooks.go,
      internal/plan/hooks.go, hook.DefaultGitCommitHook;
      internal/hook/hook_test.go covers phase filtering, dir, env, non-zero exit
    GATE: verified work can auto-commit without weakening verification PASS
```

## 9.0 OPERATIONAL HARDENING — never wedges

```
9.1 Housekeeping                                              DONE
    9.1.1 `gc`: prune logs/trace/worktrees by age, keep anything
          it is not certain about, with a reason                    DONE
    9.1.2 `recover [--force] [--node]`: report every running node
          and reclaim deliberately, keeping the attempt count       DONE
    9.1.3 state schema version + ordered migration; a newer state
          file is refused, never misread                            DONE
    ▸ evidence: cmd_house.go, cmd_recover.go, internal/store/schema.go
    note: recover does not reset attempts, so a crash loop cannot buy
    itself unlimited retries by being recovered over and over
    GATE: a year-old run dir is still usable                          PASS

9.2 Diagnostics                                               DONE
    9.2.1 `doctor`: expired leases, orphans, disk, stale worktrees    DONE
    9.2.2 orphan child detection (pid recorded per claim)             DONE
    9.2.3 `stats`                                                     DONE
    ▸ evidence: internal/house/house.go (orphan_child, SeverityError), cmd_stats.go
    GATE: one command says whether the run dir is healthy             PASS

9.3 Robustness                                                DONE
    9.3.1 fuzz the plan parser                                       DONE
    9.3.2 fuzz glob and must_match handling                          DONE
    9.3.3 disk-full and read-only-fs behaviour                       DONE
    ▸ evidence: internal/plan/fuzz_test.go, internal/verify/fuzz_test.go,
      Makefile `fuzz` target; store.writeErr classifies ENOSPC/EROFS/EACCES and
      keeps the cause reachable; house.checkFilesystem probes writability and
      escalates an imminent disk-full to an error
    GATE: no parser input panics or hangs                            PASS
    note: a run that cannot persist now says so on the first write, instead of
    failing every node for a reason it invented.
```

## 10.0 DECISION QUALITY — shrink the wrong-DAG risk

The known weakness versus Tracera: this tool trusts the first-pass DAG. These
features make that trust cheaper to earn.

```
10.1 Estimate calibration                                     DONE
    10.1.1 actual vs estimate recorded per node                      DONE
    10.1.2 drift report by kind; corrected defaults suggested         DONE
    ▸ evidence: internal/plan/calibrate.go + calibrate_test.go,
      NodeState.DurationMS, cmd_stats.go per-kind medians
    GATE: estimates converge after 3 runs                             PASS

10.2 CVP scoring                                              DONE
    10.2.1 explicit `cvp_gate:` honoured, else the last GATE         DONE
    10.2.2 `next --by-cvp` orders ready work toward the gate          DONE
    10.2.3 "what is blocking the CVP" chain output                   DONE
    10.2.4 marginal-progress scoring: reduction in remaining
           critical-path work per estimated minute, distance as
           the tiebreak                                            DONE
    ▸ evidence: internal/plan/cvp.go (MarginalScore), cmd_next.go
    note: marginal and distance both exist on purpose. Distance answers
    "how far", marginal answers "what is worth starting"; a node one step
    away that unblocks nothing is not the next thing to do
    GATE: "what next" answers in checkpoint terms                     PASS

10.3 Review loop                                              DONE
    10.3.1 `review` reads the trace and writes REVIEW.md              DONE
    10.3.2 the verdict is advice; nothing is auto-applied to the plan DONE
    ▸ evidence: cmd_report.go cmdReview + mergeTrace
    note: 10.3.1 is invoked, not auto-appended as a node. That is
    deliberate: a review node inside the DAG would be graded by the same
    contract that graded the work it is reviewing
    GATE: every run ends with an explicit judgement                   PASS
```

## 11.0 DYNAMIC DECOMPOSITION

The CRun lineage: a tool produces the work list, dagrun produces the nodes.

```
11.0 Dynamic decomposition                                    DONE
    11.1 discover: a verified artifact is the work set                DONE
    11.2 fan_out: one node per unit, ids become <parent>/<slug>       DONE
    11.3 fan_in: a single reduce that asserts the whole set is done   DONE
    11.4 expansion is idempotent per parent, so executors may race    DONE
    ▸ evidence: internal/plan/discover.go + discover_test.go,
      internal/run/expand.go, fanout_test.go, store.Expanded
    GATE: an empty work set is a successful run, not an error         PASS
```

## Dependency order (remaining work)

```
(none)
```

Nothing is left in the plan. What remains is external: two harness families the
tool cannot unblock from inside (see 1.1.4, 1.1.5).

## Next three

| # | item | why now |
|---|---|---|
| 1 | **1.1.4 kcode harness** | The fork the operator actually runs, and the only `BLOCKED` cell that is worth closing. It needs a credential in the fork's own store, which is outside dagrun — so it is a five-minute fix that converts a `PARTIAL` epic into a `DONE` one. Nothing else is waiting on it. |
| 2 | **1.1.5 helioslite harness** | The second fork, blocked on a pty plus an interactive prompt. Harder than kcode and worth less: helioslite is additive-only and legacy `forge` already passes. Mark it as the low priority it is rather than leaving it ambiguous. |
| 3 | **Nothing else** | Every other item in this document is `DONE` with evidence. The honest next move is to use the tool on real work and let the roadmap grow from what breaks, not from what can be imagined. |

## Explicit non-goals

No web UI. No scheduler daemon. No model routing by cost. No intent inference.
No cross-machine distribution of one run (single host, many processes).
