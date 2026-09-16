# Evaluator lock and scoreability contract

This contract prevents a model/runtime speed result from becoming promotion
evidence when the task corpus, runner, agent, verifier, tool schema, or result
interpretation is mutable. It is metadata-only: it does not authorize corpus
acquisition, inference, or benchmark execution.

## Additive implementation checkpoint — 2026-07-14

The following offline contract layer has landed additively in the unreconciled
checkout:

- `pheno/evidence/trial_contracts.py` strictly validates and content-hashes
  `pheno.eval.trial.v2` records, verifies bounded on-disk artifact bundles,
  and separately reports scoreability reasons;
- `pheno/evidence/aggregate_contracts.py` builds, validates, recomputes, and
  content-hashes `pheno.eval.aggregate.v2` records, with separate
  `pheno.eval.run-provenance.v1` input;
- `pheno/evidence/performance_blocks.py` validates and recomputes
  `pheno.eval.performance-block.v1` summaries from at least three immutable,
  independently scheduled paired run blocks;
- `pheno/evidence/telemetry.py` validates and recomputes bounded heterogeneous
  time series, process-attributable physical-memory peaks, coverage, thermal
  and lifecycle state, energy, and collection-overhead evidence;
- `pheno/evidence/replay_stability.py` validates and recomputes bounded
  greedy or sampled replay blocks, separating harness validity, semantic
  outcomes, tool-call correctness, recovery, loops, and risky-action bypasses;
- `pheno/evidence/atif.py` adds Pheno's closed-artifact integrity overlay for
  ATIF v1.7;
- `scripts/eval_contract.py` exposes strict offline JSON commands
  `validate-atif`, `validate-trial`, `validate-aggregate`, and
  `validate-performance-block`, plus `validate-replay-stability` and
  `validate-telemetry`; and
- `scripts/audit_eval_locks.py` performs a bounded, link-free, alias-free,
  duplicate-key-safe YAML audit of every candidate suite lock. Structural
  validity and scoreability are reported separately; `--require-scoreable`
  exits nonzero while any immutable identity or holdout gate remains open.

The accompanying trial, aggregate, ATIF, performance, replay, and telemetry
fixtures are offline/synthetic
contract tests. They are not Harbor or Pier runs, measured model results, or
scoreable benchmark evidence. These files remain untracked and post-date the
original verified preservation packet; they require a fresh delta capture
before no-loss reconciliation. Their presence does not authorize execution or
make the dirty checkout an evidence-producing environment.

## Current candidate pins

### Terminal-Bench 2.1

- Release: [Terminal-Bench 2.1](https://www.tbench.ai/news/terminal-bench-2-1)
- Dataset: [harbor-framework/terminal-bench-2-1](https://github.com/harbor-framework/terminal-bench-2-1)
- Candidate repository revision on 2026-07-14:
  `36d417f56c293b8271b306a0e4c566f58e98c153`
- Size: 89 tasks.
- Official prose conflicts: the release article says 28 tasks were repaired;
  the current repository README says 26 were modified. The task manifest and
  diff at the pinned commit are authoritative.
- Current invocation uses dataset
  `terminal-bench/terminal-bench-2-1`; leaderboard evidence requires at least
  five independent trials per task.
- Method and submission-integrity references:
  [Terminal-Bench paper](https://arxiv.org/html/2601.11868) and the
  [leaderboard integrity update](https://www.tbench.ai/news/leaderboard-integrity-update).

### DeepSWE v1.1

- Dataset: [datacurve-ai/deep-swe](https://github.com/datacurve-ai/deep-swe)
- Protocol: [arXiv:2607.07946v1](https://arxiv.org/html/2607.07946v1)
- Candidate dataset revision:
  `6db64a40f3318d8659238ff34a8cc4b491c49205`
- 113 tasks across TypeScript, Go, Python, JavaScript, and Rust.
- Pier `0.3.0` wheel SHA-256:
  `a8b43377774bc45fa20520d6c1aad9e244f2c6bdcd04155dddabd753fe443251`.
- Paper-fixed mini-swe-agent revision:
  `adfe20233d456104c38c3129161b54f0fd39f2c7`.
- The separate verifier environment is mandatory. Preserve hashes for
  `reward.json`, `ctrf.json`, `test-stdout.txt`, `run.log`, and `reports/`.
- Final evidence uses roughly four independent rollouts per task,
  macro-average per-task pass fractions for pass@1, and solved-at-least-once
  pass@4.

## Three independent artifacts

1. `pheno.eval.suite-lock.v1` freezes the repository, exact task IDs and
   subset, runner/package, agent prompt/config/tools, verifier images, and
   held-out-data manifest.
2. `pheno.eval.trial.v2` freezes one model/runtime/device/treatment cell and
   records verifier-backed milestones, tools, monotonic timing, tokens, cache,
   resources, thermals, cost, and hashed trajectories/artifacts.
3. `pheno.eval.aggregate.v2` names every contributing trial hash and reports
   attempted/scored/excluded counts, pass@1/pass@4/pass-all-k, task-cluster
   bootstrap intervals, accepted verified steps, latency, cache, tool,
   fairness, thermal, and cost completeness.

### Run provenance, memory, and cost

`pheno.eval.run-provenance.v1` is a separate run-level companion, not a value
copied into and summed across concurrent trials. One run contributes one
monotonic makespan, one time-aligned peak of attributable physical memory, and
one cost ledger. The locked memory scope is
`time_aligned_peak_attributable_physical_bytes`; unified memory is counted
once, and the derived memory denominator uses SI GB. Shared-server makespan,
memory, or cost must never be multiplied by the number of requests.

Each cost component is `complete`, `not_applicable`, or `unknown`, and a
complete total must reconcile to a uniquely hashed ledger. Incomplete cost
keeps AVS/$ and the combined dollar metric null and makes the cost gate
`not_evaluable`; it does not invent a zero-dollar run or invalidate otherwise
valid core-quality reporting.

### ATIF authority and the Pheno overlay

Use [ATIF v1.7](https://www.harborframework.com/docs/agents/trajectory-format)
as the canonical agent trajectory. Harbor's official `Trajectory` model and
`TrajectoryValidator` remain authoritative for field types, timestamps,
multimodal content, and source-specific rules. They must run first. The local
overlay then proves file-wide trajectory-ID uniqueness, closed embedded-child
resolution, exactly-once subagent references, and a step-local bijection
between tool calls and observation results. Pheno's intent graph
cross-references ATIF; it does not replace either validation layer.

Accordingly, the offline CLI's `validate-atif` command reports
`validation_scope=pheno_atif_integrity_overlay`. A successful overlay result
alone is not official Harbor validation and is not sufficient for
scoreability. In contrast, `validate-trial --artifact-root DIR` byte-hashes
every declared artifact, runs the installed Harbor validator and then the
Pheno overlay, validates the intent-graph DAG and run identity, and requires
verifier output. Without `--artifact-root`, the CLI always reports
`artifact_bundle_verified=false` and `scoreable=false`.

### Heterogeneous telemetry bundle

`pheno.eval.telemetry-bundle.v1` is the offline normalization boundary between
future native collectors and evaluator aggregates. It binds every series to
the run provenance, suite lock, cell, model, runtime, launch configuration,
load profile, fleet topology, collector/config, device-capability manifest,
hardware identity, and host software identity. WSL CUDA records additionally
require a guest identity; native macOS, Android, and iOS records forbid one.
The GTX 1080 Ti profile can only appear as a helper role.

The bundle contains exactly one series for every defined metric: GPU, system,
and battery power; cumulative energy; GPU, process-attributable, unified, and
available-system memory; temperature; throttle state; normalized OS thermal
and lifecycle state; and GPU utilization. Every series is explicitly
`measured`, `missing`, or `not_applicable`. Only profile-defined impossible
metrics may use `not_applicable`; it cannot hide a missing required sensor.
Missing data carries a source-provenance hash and bounded reason rather than a
zero value.

Memory follows the aggregate's
`time_aligned_peak_attributable_physical_bytes` scope. RTX 3090 Ti and optional
1080 Ti records require process-scoped host RAM and process-scoped GPU VRAM on
the same sample grid, then sum their disjoint physical bytes per aligned slot.
M1 records align process and unified-memory streams but use their per-slot
maximum so shared physical pages are counted once. Phones use app/UID process
memory. Multi-stream slots also enforce a clock-resolution-aware skew bound
(at most 50 ms and normally at most one-tenth of the interval). The promotable
peak is null unless the aligned grid has at least 95%
coverage; the component rows, process-attribution identity, alignment, and
derived peak receive a separate memory-provenance hash.

All samples use one profile-appropriate monotonic clock and unique interval
slots. Coverage is recomputed as observed slots divided by the bounded expected
grid. Timestamps outside their slot, duplicate/out-of-order slots, non-finite
values, decreasing cumulative energy, and oversized grids fail validation.
Process/app/process-tree scopes must agree exactly with the hashed attribution
set. Device- or system-scoped energy is not evaluable without a declared
exclusive device lease.

Instrumentation overhead is never `not_applicable`. A usable bundle needs at
least three independently scheduled baseline/instrumented calibration pairs;
their geometric-mean slowdown is recomputed and must be at most 5%. Required
series need at least 95% coverage. Unknown thermal/lifecycle observations or
missing required measurements produce `not_evaluable`; excessive overhead,
throttling, prohibited thermal state, or leaving the required active/foreground
lifecycle produces `fail`. All summaries, quality reasons, the telemetry ID,
and final bundle hash are deterministic recomputations from bounded rows.

This artifact proves byte integrity and internal reconciliation, not collector,
device, owner, process, or lease authenticity. It cannot authorize a probe or
run. The aggregate must eventually validate the complete bundle and bind its
hash; merely copying a telemetry hash into run provenance is insufficient.

### Replay and tool-stability block

`pheno.eval.replay-stability.v1` is a standalone, content-addressed contract
for repeated executions of the same immutable replay tasks. Every row binds
the suite lock, replay manifest, assertion manifest, cell, task, attempt, and
underlying `pheno.eval.trial.v2` hash. Rows must use trial run mode `replay`.
Greedy blocks require at least three seed-zero attempts per task; sampled
blocks require at least five attempts with unique seeds per task. Attempt
ordinals must be contiguous, and rows from different identities or modes
cannot be pooled.

Harness validity and semantic success are separate. From the immutable rows,
the contract recomputes normalized-output and tool-trace modal agreement,
semantic consistency, schema-valid and semantically correct calls,
valid-but-wrong calls, duplicates, repairs, fallbacks, loops, injected-failure
recovery, and risky-action bypasses. Promotion requires at least 99.5% harness
validity and tool-schema validity; at most 1% valid-but-wrong, duplicate, and
loop rates; at least 95% injected-failure recovery; and zero risky-action
bypasses. Greedy mode additionally requires at least 99% normalized-output,
tool-trace, and semantic consistency. Sampled output variance is reported but
the greedy-equivalence gates are explicitly not applicable.

Only `local_measured` rows can pass. Dry-run or synthetic rows, absent tool
calls, or absent injected-failure evidence remain `not_evaluable`; fixtures do
not become execution evidence. The record and each replicate have
deterministic content hashes, strict fields, bounded row counts, and secret
rejection. This contract is not yet resolved by aggregate ingestion and no
runner currently emits it; those integrations remain post-reconciliation
work.

### Deterministic aggregation

- Pass@1 is the macro-average of each task's scored pass fraction.
- Pass@4 is the fraction of tasks solved at least once among scoreable attempt
  ordinals 0–3; pass-all-k reports complete-case reliability and explicit
  coverage.
- Confidence intervals use exactly 10,000 deterministic percentile resamples,
  cluster on task, retain all attempts for a sampled task, and use a recorded
  SHA-256-derived seed plus Hyndman–Fan type-7 quantiles.
- Paired treatment/baseline inference admits only matching task IDs, attempt
  ordinals, seeds, and arm-independent pair keys. If either side is excluded,
  that pair contributes to neither quality arm.
- Task resampling cannot create independent run-level performance replicates;
  a single concurrent schedule therefore cannot establish an AVS speedup
  confidence interval.
- Performance promotion requires a validated performance-block summary. It
  uses exactly 10,000 deterministic percentile resamples of paired block-level
  log AVS/s speedups; the lower 95% speedup bound must be at least 1.0. Without
  this separate artifact the gate remains `not_evaluable`.
- Latency summaries use named queue, TTFT, task-wall, and verifier intervals.
  True decode throughput is `(completion_tokens - 1) / (last_token -
  first_token)` only when token endpoints exist; SSE chunk gaps never become
  ITL. Long-turn retention uses a hashed assertion manifest and ordered
  checkpoints at turns 1, 5, 10, 25, and 50.

These rules make the implementation deterministic; they do not turn fixture
values into measurements. The quality definitions follow the pinned
[DeepSWE protocol](https://arxiv.org/html/2607.07946v1), while Terminal-Bench
submission integrity remains governed by its official policy linked above.

### Strict offline CLI boundary

`scripts/eval_contract.py` accepts one bounded regular UTF-8 JSON file. It
rejects duplicate keys, non-finite numbers, symbolic links, non-regular files,
and inputs above the default 16 MiB limit. Output is deterministic JSON:

- `validate-trial` validates, hashes, and reports record scoreability reasons.
  It requires `--artifact-root DIR` before it can report `scoreable=true`; a
  structurally valid diagnostic or synthetic trial may exit successfully while
  reporting `scoreable=false`;
- `validate-aggregate` performs validation and hashing only; it does not build
  an aggregate from trials;
- `validate-telemetry` validates bounded time-series rows, recomputes coverage,
  calibration overhead, memory alignment, summaries, quality state, and the
  content hash; it never collects telemetry; and
- `validate-replay-stability` validates and hashes an already-built replay
  block and reports its promotion gate; it never executes a replay; and
- `validate-atif` runs only the Pheno overlay described above.

The CLI has no network, download, inference, server, evaluator, or subprocess
execution path. Input/contract failures exit nonzero separately from sanitized
unexpected failures.

## Outcome semantics

- The persisted vocabulary is `passed`, `model_failure`, and
  `infrastructure_exclusion`.
- Verifier failure, timeout, context exhaustion, OOM, and unsafe model/agent
  behavior are `model_failure`. They stay in the scored failure denominator;
  OOM is not reclassified as an infrastructure exclusion.
- Harness crashes and provider, verifier-infrastructure, network, or evaluator
  infrastructure errors are `infrastructure_exclusion` and must be counted by
  reason. This is distinct from a verifier correctly rejecting a model result,
  which is `model_failure`.
- A task seed is not a subset identity. Freeze and hash the exact task IDs.
- Exact tool/argument accuracy is valid only on gold-labeled tool fixtures.
  Open-ended terminal/SWE trajectories report schema validity, safety,
  duplicates, semantic postconditions, and verifier outcome instead.
- SSE chunk gaps are not token ITL unless token-level timestamps exist.

An accepted verified step is a frozen verifier-backed milestone whose
predicate changes false to true and remains true through the terminal
regression verifier. It is not a token, turn, or tool call. A fully passed task
without subtask verifiers contributes exactly one step.

## Hard promotion gates

Before efficiency comparison:

- evidence class is locally measured execution, not dry-run, synthetic,
  vendor, or anecdotal;
- every dataset/model/artifact/runtime/harness/parser/template/tool/config and
  evaluator revision is immutable and hashed;
- ATIF validates, tool calls and observations correlate completely, verifier
  artifacts hash correctly, secrets are absent, held-out tasks were not used
  for training, and risky-action bypasses equal zero;
- infrastructure exclusions are at most 2%, with no more than a one-point
  paired-arm exclusion difference;
- production candidates have zero OOM, deadlock, unexplained restart, orphan
  tool-call, and cross-request cache-contamination events;
- comparisons use paired task IDs, attempt ordinals, and seeds;
- paired lower 95% confidence bound for pass@1 delta is at least -2 points;
  tool semantic correctness is within -0.5 point of baseline; schema-valid
  calls are at least 99.5%; valid-but-wrong and duplicate/loop rates are at
  most 1%; injected-failure recovery and long-turn retention are at least 95%;
- instrumentation coverage is at least 95%; concurrency error rate is at most
  1%; Jain fairness is at least 0.95; starvation is zero; 30-minute throughput
  retention is at least 90%; and no device thermal policy is violated.

Long-turn drift and concurrency are required core gates. A missing fixture may
be reported as `not_applicable`, but it cannot produce core promotion.

Only after these gates compare the AVS goodput, AVS/s/peak-active-GB, and AVS/$
Pareto frontier. The combined AVS/(s·GB·$) value is reporting only.

## Current local gaps

- The candidate TB2.1 and DeepSWE suite locks still lack final task/subset,
  held-out, runner, prompt, tool-definition, verifier, and artifact hashes and
  therefore remain explicitly non-scoreable. The offline lock audit validates
  both files but reports zero of two scoreable, so this is now a machine gate
  rather than a prose-only warning.
- The standalone `validate-atif` command remains overlay-only. Runner
  integration must either use `validate-trial --artifact-root` or explicitly
  run canonical Harbor validation before the overlay; no existing runner does
  that ingestion yet.
- The bounded artifact resolver now independently hashes regular files, rejects
  root links and path escapes, validates ATIF and the intent graph, requires
  verifier output, and scans UTF-8 artifacts for credential patterns. Binary
  outputs are byte-hashed and bounded but remain format-agnostic; suite-specific
  adapters must still interpret verifier semantics.
- Run-provenance, attributable-memory, cost-ledger, concurrency, thermal, and
  time-series telemetry contracts are exercised only by offline fixtures. No
  instrumented SGLang, vLLM, TensorRT-LLM, oMLX, Cactus, Harbor, or Pier run has
  populated them. Aggregate ingestion does not yet resolve and validate the
  telemetry bundle behind `telemetry_sha256`.
- Replay/tool-stability recomputation is also fixture-only. No runner emits a
  `pheno.eval.replay-stability.v1` block, and aggregate promotion does not yet
  resolve or bind one.
- The independent paired-run-block contract is implemented and synthetic-test
  covered, but no measured run has populated it. Task-cluster resampling alone
  still cannot make the performance-promotion gate evaluable.
- `eval/tbench_v21.py` still labels availability unverified and invokes
  `terminal-bench@2.1`; `config/harbor_tbench_agent.yaml` still declares 2.0.
- `config/harbor.yaml`, `config/harbor_tbench_routes.yaml`, and
  `config/local_eval_manifest.yaml` also retain executable Terminal-Bench 2.0
  defaults. Treat all four legacy paths as disabled/historical until the 2.1
  lock is scoreable; none may silently populate the new aggregate contract.
- The dropped `granite-4.0-h-micro` cloud row remains in three legacy matrices,
  and older specs still describe eight rather than seven locked cloud
  baselines. Reconcile those identities before regenerating a route matrix.
- `config/eval_pillars.yaml` still calls a weighted composite its primary
  acceptance result. That legacy score is reporting-only and can never bypass
  mandatory quality, safety, drift, concurrency, or performance-block gates.
- Legacy local manifests bind MLX and Linux/WSL engines to a Windows 3090 Ti
  hardware cell. Split OS, device, runtime, and owner-specific cells before
  generating any executable matrix.
- `eval/deepswe.py` checks that `pier --version` runs but does not enforce the
  semantic minimum or package hash.
- Existing TB2.1 and DeepSWE JSON files, plus the new contract fixtures, are
  dry-run or synthetic artifacts—not measured results.
- `perf/streaming.py` measures SSE chunks rather than token ITL; existing
  throughput fields need corrected timing before promotion use.
- `perf/resources.py` still lacks temperature, throttle, energy integration,
  phone thermal/lifecycle state, and server-process attribution. The additive
  telemetry contract defines their normalized destination but does not modify
  or legitimize that active collector.
- Output length, similar token counts, placeholder speed scores, and historical
  weighted composites are not accepted-step, cache-hit, or promotion evidence.

Do not repair the actively modified runners in the diverged checkout. The new
validators, overlay, CLI, candidate suite locks, and fixtures are additive and
remain untracked. Preserve and reconcile the repository before integrating
them with existing runners; only then may separately authorized benchmark
execution produce candidate evidence.
