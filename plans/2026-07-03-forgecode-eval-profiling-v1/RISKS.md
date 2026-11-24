# RISKS.md

Date: 2026-07-03
Companion to: `RESEARCH_AUDIT.md`, `EVAL_ARCHITECTURE.md`,
`MODEL_MATRIX.md`, `TRACE_EVALSET_PLAN.md`, `IMPLEMENTATION_PLAN.md`.

Risks are scoped, owned, and gated. They are not "things to worry
about" — each has a detection signal and an automatic action.

---

## R1 — Benchmark contamination

**Risk.** Long-horizon custom tasks or trace-derived role evals pick up
content from TB2.0 / TB2.1 / TB3.0 / DeepSWE / SWE-bench, polluting
the leaderboard for those suites.

**Detection signal.** `eval/suites/long_horizon/<task>/contamination_check.py`
must report zero overlap on a corpus fingerprint
(minhash + n-gram) between the authored task and any external benchmark
in our known set.

**Owner.** PR-4 author.

**Action on detection.** The offending task moves to a
`evalset/private/` namespace, never appears in the public leaderboard,
and is marked `contaminated=true` in the ledger. No silent fix.

---

## R2 — Disk pressure (2 TB NVMe at ~95% full)

**Risk.** Traces, model weights, harbor containers, and bench results
fill the disk and brick the host mid-run.

**Detection signal.** `eval/perf/profiler.py` samples `shutil.disk_usage`
every 1 Hz; threshold `free_gb < 25 GB` (`config/context_caps.yaml`
proposes this default).

**Owner.** PR-1 (profiler) + every long-running script.

**Action on detection.**
1. `eval/results/` and `bench/results/` are age-pruned (default 14 d,
   configurable; never prune the most recent ledger day).
2. Cold archive (`%_archive%`) for trace JSONL once a row is in the
   ledger.
3. Script aborts if `free_gb < 10 GB` after prune.
4. `verifier/risky_action.py` denies any action that would `rm` outside
   the whitelisted paths.

**Why this is a real risk here, not generic.** The 2 TB NVMe is full;
this is the *binding* environmental constraint of the project.

---

## R3 — Brief-vs-reality mismatches (working-name drift)

**Risk.** The brief repeatedly references `forge-dev`, `forgecode`,
`codex-fork`, `pheno-specs` as if they were committed paths. Several
do not exist locally (see `RESEARCH_AUDIT.md` §1).

**Detection signal.** The first command in any CI job should print a
"path-resolved" table that this `RESEARCH_AUDIT.md` also mirrors. Any
mismatch is logged.

**Owner.** This audit; the eventual `forge/AGENTS.md` should mirror it.

**Action on detection.** Plan adapts (it does). Anything that depends
on a missing path is gated until the path is real (`.git submodule
init` for `agileplus-specs`, etc.).

---

## R4 — Secret leakage

**Risk.** `OPENROUTER_API_KEY` or other secrets enter a recorder JSONL,
a benchmark payload, or a public bundle.

**Detection signal.**
- Pre-commit grep blocks `sk-or-…` patterns.
- `eval/traces/recorder.py` runs a redact pass before any persist.
- `scripts/gardener.py` scrubs ledger JSONL when promoting.

**Owner.** Garden + redactor; CI enforces.

**Action on detection.** If a secret is found in a ledger row, the row
is encrypted at rest (libsodium secret-box) with a per-host key, and
the JSON is removed from any bundle going to PR data.

---

## R5 — Invalid comparisons across engines / runners

**Risk.** Because cells differ in `model_id`, `quant`, `runner`,
`serving-opt`, and `solver` (e.g. llama-server doesn't support EAGLE),
direct two-cell comparisons will lie. E.g. comparing "vLLM Qwen12B" to
"ik_llama Qwen4B" and concluding "vLLM is faster" when in fact the
model size shrank by 3×.

**Detection signal.** Every cell carries the envelope from
`EVAL_ARCHITECTURE.md` §2; comparisons are *only* within cells whose
attributes differ by at most **one** dimension at a time. Markdown
and dashboard enforce this.

**Owner.** `bench/results/model_matrix/*` aggregator.

**Action on detection.** Any aggregator that can't show its comparison
audit log refuses to print a "winner" rank. Lying-with-rank is a
flag-shippable offense here.

---

## R6 — Throughput-mismeasurement

**Risk.** Tokens/sec reported during a benchmark can be inflated by
queue depth, batch coalescing, or warm KV cache. Wall-clock isn't a
proxy for cost.

**Detection signal.**
- `eval/perf/ctx_cache_probe.py` reports hit rate by prefix-shape.
- `eval/perf/harness_overhead.py` tags slices as **model / harness /
  IO** and reports each separately.
- `ctx_cache_hit_rate` must be reported alongside any tokens/sec.
- "harness overhead" must be reported alongside any TTFT.
- A bare "tokens/sec" claim with no router context is rejected by the
  leadership dashboard.

**Owner.** PR-1 + PR-8.

**Action on detection.** Numbers without provenance are not published.

---

## R7 — Overfitting / benchmark gaming

**Risk.** Self-improvement loop optimizes a single reward against a
fixed eval set. Without multi-signal and gates, the model learns the
test, not the skill.

**Detection signal.**
- Multi-signal reward (see `IMPLEMENTATION_PLAN.md` §7).
- `replay_equiv` gate.
- `heldout` rotation defined in `training/eval_holdout.yaml`; promoted
  scores are always computed on the held-out split, never on the training
  split.

**Owner.** Garden + verifier.

**Action on detection.** Demotion automatic when held-out scores
diverge from training scores > ε.

---

## R8 — Flaky environments

**Risk.** Harbor containers, Pier sandboxes, llama-server warm-up,
network jitter, OpenRouter rate limits all produce variance that
masks model quality.

**Detection signal.**
- `n_attempts=1` default and `n_attempts=3` mode plus reporter.
- `bench/results/*` runs include `--reps` so variance bars are reported.
- `eval/ledger/` includes a run-by-run variance overlay.

**Owner.** All PRs.

**Action on detection.** Cells whose `σ(pass@1) > 0.05` are flagged as
"noisy" and excluded from any leaderboard claim.

---

## R9 — Multi-agent attribution

**Risk.** In multi-agent runs, which agent produced the win? Without
per-role scoring, "manager helped" is unfalsifiable.

**Detection signal.**
- Per-role eval pipeline (`TRACE_EVALSET_PLAN.md`).
- `acceptance_delta` separated per role.
- Pheno's `lanes.yaml` already routes by role; ledger records the
  lane.

**Owner.** PR-6 + Garden.

**Action on detection.** "Manager helped" claims require paired
per-role leaderboard rows.

---

## R10 — Chat-loop demotion blind spot

**Risk.** PR-10 (intent-graph refactor) could regress under the radar
if acceptance is multi-signal but the gate set is too easy.

**Detection signal.** G1..G7 in `IMPLEMENTATION_PLAN.md` §6.

**Owner.** Whoever lands PR-10.

**Action on detection.** Automatic demotion + reason in authorship
ledger.

---

## R11 — VRAM instability (overswap, OOMs)

**Risk.** Aggressive swap driven by `moe_deploy_policy.yaml` could
OOM or thrash.

**Detection signal.** `vram_peak`, `gpu_util`, `oom_event_count`.

**Owner.** `pheno/model_manager.py` + Garden.

**Action on detection.** Swap frequency drops automatically if OOM
events > 0 in any 24 h window.

---

## R12 — Latent-vs-text multi-agent blind spot

**Risk.** Picking LatentMAS or TextMAS without measuring each on the
real per-role suite means we adopt a cheaper or cleaner-looking system
that is actually worse.

**Detection signal.** Both modes have first-class configs and a paired
diff in the per-role leaderboard (per `EVAL_ARCHITECTURE.md` §3.2 +
`Trace_EVALSET_PLAN` §3.3).

**Owner.** PR-7.

**Action on detection.** Mode is rolled forward only if its paired diff
is positive on `acceptance_delta` AND within budget on `cost_per_success`.

---

## R13 — Prompt canonicalization (deterministic cache) risk

**Risk.** User-level deterministic cache (`ChatGPT-User-level
Deterministic Cache`) helps repeat runs but can poison comparison when
one model runs warm and another runs cold.

**Detection signal.** `cache_warm` and `cache_cold` cells both
required for any cacheable cell.

**Owner.** PR-1 + PR-5.

**Action on detection.** Comparisons cross cache states are explicitly
disallowed in the aggregator.

---

## R14 — Provider lock-in (OpenRouter)

**Risk.** Pinning everything to OpenRouter ling-2.6-flash creates a
single-point-of-failure for the program.

**Detection signal.** `provider_retry_rate`, `provider_5xx_rate`,
`provider_429_rate` (defined in `EVAL_ARCHITECTURE.md` §3.3).

**Owner.** CI runs.

**Action on detection.** Provider health spike > 5% over 24 h → eval
runs defer + alert (no leaderboard updates from broken-provider rows).

---

## R15 — Audit-trail drift

**Risk.** Garden demotes but the demotion isn't visible; or a model
swap ships without an authorship row.

**Detection signal.** Authorship-audit job in CI (PR-9).

**Owner.** Garden.

**Action on detection.** Any change without an authorship row is
auto-reverted by CI.

---

## R16 — Long-horizon prompt leakage of TLDRs

**Risk.** Long runs post LLM responses into other context sources
(TB-style public write-ups, blog posts) — and over time, future
benchmark revisions leak into training data.

**Detection signal.** Prompt-set fingerprint must change every N runs;
`prompts/fingerprint.txt` is rotated.

**Owner.** Garden.

**Action on detection.** Rotation is automatic; if the fingerprint
fails to rotate for >7 d, CI alerts.

---

## R17 — Engine feature drift

**Risk.** vLLM / SGLang / TRT-LLM add/remove/different-prefix-key
features month-to-month.

**Detection signal.** Per-engine smoke (`PR-5` sub-PRs) must pass per
release; release is pinned in `config/inference_runners.yaml`.

**Owner.** Engine adapters.

**Action on detection.** Smoke failure blocks any cell using that
runner until bumped.

---

## R18 — Sub-1B BitNet drift

**Risk.** BitNet / ternary weights have unstable kernels on consumer
GPUs; spec-dec parity can fail silently.

**Detection signal.** `bench/kv_bakeoff.py` regular bakeoff; spec-dec
acceptance per task.

**Owner.** PR-5e.

**Action on detection.** If parity < baseline, BitNet demoted from the
draft role until parity is restored.

---

## R19 — Test verification false green

**Risk.** Verifier passes a patch that shouldn't pass (test isn't
actually exercising the fix, or env differs from claim).

**Detection signal.** Per-role verifier health: `verifier_flip_rate`
(yes↔no between two runs). Replay-equiv gate (G3) catches class.

**Owner.** Verifier + Garden.

**Action on detection.** Held-out verifier refresh; flip-rate > ε
demotes the verifier.

---

## R20 — Scope creep into codex fork

**Risk.** Stage 2 (codex fork) is opened before stage 1 lands; partial
work splits attention.

**Detection signal.** Branch protection: `core/intent-graph-v1` and
`eval/garden-v1` merge gates.

**Owner.** This doc + `IMPLEMENTATION_PLAN.md` §5 ladder.

**Action on detection.** Stage 2 doc (`IMPLEMENTATION_PLAN-stage2.md`)
is not written until stage 1 is green.

---

## Notes for the user

- The **two biggest risks** for this host are R2 (disk) and R5 (invalid
  cross-engine comparisons). The plan elevates both to first-class
  detection with hard actions, not best-effort logs.
- The garden model in `EVAL_ARCHITECTURE.md` §5 / `IMPLEMENTATION_PLAN.md` §7
  directly addresses the user's "1st blind attempt with a much smaller
  prompt (just told them to RLVRAF)" — the new approach is multi-signal,
  gated, and audited.
