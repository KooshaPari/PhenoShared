# RISKS.md

> **Status:** Living document. Companion to `RESEARCH_AUDIT.md`, `EVAL_ARCHITECTURE.md`, `MODEL_MATRIX.md`, `IMPLEMENTATION_PLAN.md`.
> **Purpose:** Catalog the things that will silently break this program if we don't name them up front. Each risk has (a) what it is, (b) how it manifests, (c) how we detect it, (d) how we prevent or mitigate it.

---

## 1. Benchmark contamination

**What:** the model was trained on (or partially memorized) the exact task we are using to evaluate it. Result: inflated scores that don't generalize.

**How it manifests:**
- Terminal-Bench 2.0/2.1 tasks are public. Frontier models almost certainly saw them.
- SWE-bench Verified issues are public; many models were trained against them.
- DeepSWE tasks are public per datacurve-ai/deep-swe.
- The Artificial Analysis Coding Agent Index is a re-aggregation of the same public tasks — using it as a sole target inherits its contamination surface.

**Detection:**
- Hold any "frontier-class" eval result suspect unless (a) the model release date predates the task freeze date, or (b) the eval is gated by a held-out subset never released publicly.
- For our own trace-derived evalset: every spec is timestamped and source-traced. If a model release date is later than the trace capture date, treat as contamination candidate.

**Mitigation:**
- Maintain `training/eval_holdout.yaml` and the trace-derived holdout (T5 in `TRACE_EVALSET_PLAN.md`) as **strictly** held out. No code, no fine-tuning data, no prompt examples drawn from these tasks ever enter training.
- Cross-check with at least one non-public eval (our trace-derived evalset) before declaring a win.
- For DeepSWE: prefer v1.1+ tasks (separate verifier) and tasks with `synthetic: true` provenance.
- For TB 2.0 vs TB 2.1: if 2.1 scores are dramatically higher than 2.0 on the same model, **investigate before publishing** — 2.1 may have leaked into the training set.

---

## 2. Secret leakage

**What:** API keys, model weights, or trace content end up in places they shouldn't (committed to git, logged, exposed to a sub-agent with broader permissions).

**How it manifests:**
- `os.environ.get("OPENROUTER_API_KEY")` accidentally serialized into a JSON manifest.
- A trace-derived spec contains a real prompt that includes a key.
- A model checkpoint downloaded for local eval ends up in the repo by mistake.

**Detection:**
- Pre-commit hook: any file matching `*secret*`, `*.key`, `*.pem`, `*credentials*`, `*token*` is rejected.
- CI scan: ripgrep the diff for known prefix patterns of `sk-or-v1-…`, `sk-…`, `ghp_…`, `-----BEGIN … PRIVATE KEY-----`.
- Manifest validation: every `*.manifest.json` is loaded and any string matching key-prefix regexes is rejected at write time.

**Mitigation:**
- All secret reads go through `pheno-harness/pheno/secrets.py` (a small module that returns secrets from environment or a vault, never from disk and never logged).
- `eval/results/` and `bench/results/` are `.gitignore`-d except for the manifest files. Manifest files are redacted at write time.
- Trace-derived spec pipeline (`TRACE_EVALSET_PLAN.md` §6 Stage T3) explicitly filters traces that contain key patterns.

---

## 3. Disk pressure

**What:** the 2 TB NVMe is "mostly full" per the brief. Eval sandboxes, model weights, trace stores, and intermediate artifacts compete for space. A full disk mid-run produces silently-corrupted results.

**How it manifests:**
- Harbor / DeepSWE / SWE-bench sandboxes leave containers behind that grow.
- Trace `.graph.json` + `.trace.jsonl` files accumulate.
- Model weight downloads for the matrix sweep (multiple 70B-class weights at AWQ) easily hit hundreds of GB.

**Detection:**
- Pre-run check: `pheno-harness/perf/profiler.py` reports `disk_free_gb` at run start. If below `config/disk_budget.yaml:min_free_gb`, abort.
- Post-run GC: every run enforces `bench/results/` retention (30 days), trace archive (cold storage after 7 days), model weight cache eviction (LRU + size cap).

**Mitigation:**
- Single source of truth for disk budget: `config/disk_budget.yaml`. Limits per category (eval sandboxes, model cache, trace archive).
- Weight cache lives on a dedicated path (`state/model_cache/`) with a hard size cap.
- Harbor / DeepSWE sandboxes are torn down at run end (already a Harbor convention; enforce it in `pheno/harbor_util.py`).
- Long-context KV-cache spill goes to RAM (faster, frees disk) where vLLM / SGLang support it.

---

## 4. Invalid comparisons

**What:** we compare two systems that aren't actually comparable — different task subsets, different budgets, different verification, different harness versions. The "win" is an artifact.

**How it manifests:**
- TB 2.0 score on a 32-task subset vs. TB 2.1 score on the full 89-task set.
- Local 4B AWQ vs. cloud 100B MoE without correcting for cost.
- Ling-2.6-flash with 90 % promo pricing vs. local model with $0.
- A matrix sweep with `--max-tokens 4096` vs. another sweep with `--max-tokens 16384`.

**Detection:**
- Every scoreboard row carries the full reproducibility manifest (`EVAL_ARCHITECTURE.md` §6). The scoreboard refuses to render rows with mismatched keys (subset, budget, env).
- Composite score `40/30/30` is the only number ever published; raw numbers are always alongside.

**Mitigation:**
- Cross-suite comparisons require the same model id, the same route kind, the same budget.
- Cross-hardware comparisons require a separate row in the scoreboard (no folding).
- Cost comparisons always include `$` and `tokens` together. Never one without the other.
- Whenever a pricing promo is active (e.g. Ling 90 % off), tag it in the manifest. Re-run when promo expires.

---

## 5. Overfitting to a single benchmark

**What:** we tune the harness / planner / prompt so hard against TB 2.0 that TB 2.1, DeepSWE, and the trace-derived suite all regress.

**How it manifests:**
- Per-task prompt templates that game the TB 2.0 task structure.
- Planner DAG templates that fit TB 2.0 task shapes but generalize poorly.
- Eval-holdout leakage via the trace-derived evalset (we trained on similar tasks).

**Detection:**
- Every PR runs **all four** suite families: TB 2.0, TB 2.1, SWE-bench Verified subset, trace-derived role suite. A PR that improves one family and regresses another is auto-flagged.
- The self-improvement loop's regression gate (§1 of `IMPLEMENTATION_PLAN.md` Stage 4) is the second line of defense.

**Mitigation:**
- Pillar weights in `config/eval_pillars.yaml` are tuned across all four suite families, not against any single one.
- "Pillar score" is the only optimization target; per-suite score is diagnostic, not objective.

---

## 6. Flaky environments

**What:** Harbor / DeepSWE / SWE-bench sandboxes are non-deterministic in subtle ways — network availability, container start order, clock skew. A single run can vary ±5 % across identical re-runs.

**How it manifests:**
- A model that scored 0.81 yesterday scores 0.78 today on the same task.
- A container failed to start because the registry was rate-limited.
- A test ran but the verifier's wall-clock expired before results were read.

**Detection:**
- Every run is `n_attempts=1` by policy (already in `eval/tbench.py`). To detect flake, every scoreboard row is paired with a "flake score" computed from the rolling 5-run variance on a fixed 16-task subset.
- `config/disk_budget.yaml` and the manifest's `env:` block make container start order reproducible.

**Mitigation:**
- For TB 2.0/2.1, use the verified subset only. Avoid "all tasks" mode for daily runs.
- For DeepSWE, prefer `--env modal` over `--env docker` when possible (better isolation).
- Container registry pinning: every docker image SHA is recorded in the manifest, not just the tag.

---

## 7. Misleading throughput metrics

**What:** we report "tokens/sec" without specifying whether it's aggregate, per-request, with prefix cache, with spec-dec, with chunked prefill. Or we compare a batch-1 run to a batch-32 run and call one faster.

**How it manifests:**
- vLLM with chunked prefill + EAGLE-2 reports 200 tok/s aggregate on a single 4-prompt batch. Ling-2.6-flash on OpenRouter reports 80 tok/s on the same workload. The 200-vs-80 comparison is apples-to-oranges.
- A "TTFT p95 < 100 ms" claim is actually TTFT for an empty cache vs. a warm cache — different numbers.

**Detection:**
- The perf suite's manifest records `batch_size`, `prefix_cache_state`, `spec_dec_mode`, `chunked_prefill_mode`, `concurrency`. Two rows with different values can never be plotted on the same axis.
- The scoreboard's per-row filters expose these fields; default filter is "same batch_size, same cache state, same spec_dec mode".

**Mitigation:**
- Always publish `tokens/sec/request` and `aggregate tokens/sec` together.
- Always publish `TTFT p50 / p95 / p99` with cache state annotated.
- Probe overhead is reported separately (see `EVAL_ARCHITECTURE.md` §3 and `IMPLEMENTATION_PLAN.md` Stage 3).
- "Fast" claims always name the configuration.

---

## 8. Multi-agent attribution

**What:** in a multi-agent run, who deserves credit / blame for the outcome? If the planner picks the wrong DAG and the sub-agent recovers, is that a planner fail or a sub-agent win?

**How it manifests:**
- An aggregated "team pass rate" masks which role is actually weak.
- A promotion candidate clears the bar because the planner carries a weak sub-agent.

**Detection:**
- Per-role scoreboards (`TRACE_EVALSET_PLAN.md` §7) make this explicit.
- The intent-graph recorder (Stage 2 of `IMPLEMENTATION_PLAN.md`) attributes every outcome to the node that produced it.

**Mitigation:**
- Per-role score is the unit of promotion, not the team score.
- Cross-role correlation is logged but not optimized. (Optimizing for it is how you game the metric.)
- A planner that "carries" a sub-agent should be flagged by the role correlation metric, not rewarded.

---

## 9. OpenRouter API stability

**What:** OpenRouter is a routing layer over many providers. A model id can map to a different upstream provider between calls. A 90 % promo can expire mid-benchmark. A provider can rate-limit or deprecate a model.

**How it manifests:**
- Ling-2.6-flash runs return slightly different outputs on different days because the upstream provider rotated.
- A cost cap is hit mid-run because pricing changed.
- The model id resolves but the response is now from a different (worse) provider.

**Detection:**
- Every manifest records `provider_route` and `provider_response_id` if exposed by OpenRouter. Cross-check vs. expected.
- Cost ceiling checks (`eval/budget.py`) every N requests, not just at run end.

**Mitigation:**
- Pin a model id + provider combination at the start of every benchmark campaign.
- Re-verify pricing on every model-binding PR.
- Have a local fallback (Mixtral 8x7B / DeepSeek-V2-Lite) ready for the most common model ids.
- Treat `inclusionai/ling-2.6-flash` as `ling-2.6-flash + OpenRouter` explicitly in the binding — never just the slug.

---

## 10. Self-improvement loop gaming

**What:** the loop optimizes its own gates and learns to game them.

**How it manifests:**
- The verifier learns to mark borderline cases as pass because that improves the rolling score.
- The gate thresholds drift upward because "no regression detected" is misinterpreted as "improvement".
- The DPO data filter starts excluding hard cases to keep the holdout pass rate high.

**Detection:**
- Holdout gate is **fixed** at run time, not derived from rolling stats. See `config/eval_pillars.yaml:holdout_thresholds`.
- The garden tick logs a snapshot of the gates + thresholds daily; any drift is alarmed.
- A synthetic failing run injected weekly must always trip the regression gate.

**Mitigation:**
- All thresholds live in YAML, not in code. PRs to change them require a justification comment.
- Loop has no write access to its own thresholds.
- The "two consecutive green windows" rule is enforced by the clock, not by the loop itself.
- Every promotion candidate is reviewed by a human (or a meta-model with a hard risk budget) before merge.

---

## 11. Sub-agent drift

**What:** when the main thread delegates work to subagents, the subagents may take action the main thread didn't intend (mutate files, change config, run expensive operations).

**How it manifests:**
- A subagent dispatched to "audit perf suite" decides to actually install vLLM, fills the disk.
- A subagent dispatched to "build spec pipeline" writes to a path the main thread reserved for something else.

**Detection:**
- Subagent hand-off contract (`IMPLEMENTATION_PLAN.md` §13) returns file paths only, not write side effects.
- All subagent-returned file paths are validated against the `pheno-harness/` tree before being trusted.

**Mitigation:**
- Subagents are dispatched with explicit scope statements. Scope violations are returned as errors, not silently accepted.
- Subagents never run `pip install`, `git push`, or destructive shell commands without explicit main-thread approval.
- The main thread owns the reproducibility manifest; subagents contribute artifacts.

---

## 12. Codex fork unknown surface (Stage 10)

**What:** when Stage 10 starts, the codex fork's internal architecture is not fully mapped. The Stages 1–9 transfer may miss surfaces we don't know about.

**How it manifests:**
- The eval harness integration points in the codex fork differ from pheno-harness.
- The intent-graph recorder (Stage 2) integrates differently because codex's chat loop has different boundaries.

**Detection:**
- Before Stage 10 starts, a **separate** audit of the codex fork is required (`audit/CODEX_AUDIT.md`, modeled on `RESEARCH_AUDIT.md`).
- All assumptions from Stages 1–9 must be re-verified against the codex fork.

**Mitigation:**
- Stage 10 is **gated on user approval** (see `IMPLEMENTATION_PLAN.md` §10).
- The codex fork's first eval is a smoke (16-task TB 2.0) — not a full sweep.
- Stages 1–9 are re-played against the codex fork one at a time; no batch transfer.

---

## 13. Latent-MAS / text-MAS bifurcation

**What:** the corpus (`ChatGPT-LatentMAS vs TextMAS comparison (1).md`) flags a real architectural decision that could destabilize the program if revisited mid-implementation.

**How it manifests:**
- Half the team assumes text-MAS (JSON messages, inspectable); half assumes latent-MAS (hidden-state, cheaper). Trace schema diverges.

**Detection:**
- Trace schema is text-only in this round. Any latent encoding is parked.

**Mitigation:**
- Decision is deferred (`EVAL_ARCHITECTURE.md` §9). Do not commit to latent-MAS in this round.
- Any proposal to add latent encoding requires a fresh audit doc.

---

## 14. Pheno-specs submodule ambiguity

**What:** `pheno-harness` references a submodule called `agileplus-specs/` (per AGENTS.md); the brief references `pheno-specs/`. Local dir state was unclear on the day of audit.

**Detection:**
- Confirm submodule state at the start of every PR that touches the spec submodule path.

**Mitigation:**
- Decision logged in `RESEARCH_AUDIT.md` §6 unknown #1. Resolve before any spec submodule mutation.

---

## 15. M1 Pro under-spec trap

**What:** the M1 Pro 16 GB can run small models, but it cannot run the same eval suite as the 3090 Ti. Treating it as a peer hardware target will produce misleading throughput numbers.

**Detection:**
- M1 Pro runs are tagged `hardware_profile: m1_pro_16gb` and excluded from desktop comparisons by default.

**Mitigation:**
- M1 Pro runs the **fallback worker** (T0 + spec-dec) and the **monitoring** role only.
- No TB 2.0 / DeepSWE runs on M1 Pro. Reject such requests at the runner level.

---

## 16. Reproducibility gaps

**What:** a benchmark run is published without the full manifest. Months later, no one can reproduce the number.

**Detection:**
- The scoreboard refuses any row without a complete manifest. The manifest schema is in `EVAL_ARCHITECTURE.md` §6.

**Mitigation:**
- Manifest is written at run start, not run end. A run that fails before the manifest is written is **not a run** — it's a draft and is excluded.
- Manifests include `commit_sha`, `model_id`, `provider`, `route_kind`, `engine`, `quantization`, `hardware`, `env`, `seeds`, `held_out_from_training`, `holdout_hash`, `artifacts`.
- Manifests are git-tracked. Result JSONs are gitignored.

---

## 17. Tool / dependency drift

**What:** vLLM / SGLang / TensorRT-LLM move fast. A version bump can change behavior, default flags, or quantization support.

**Detection:**
- Pinned versions in `requirements.txt` (or equivalent).
- CI installs from lock files, not from unpinned `>=`.

**Mitigation:**
- Lock files are updated in a separate PR with its own benchmark sweep. No silent bumps.
- Engine upgrades are gated on a re-run of the matrix sweep (Stage 7).

---

## 18. Compliance / acceptable use

**What:** some models on OpenRouter / forge have use restrictions. Eval prompts that exercise restricted behavior (e.g. vulnerability reproduction) may violate provider ToS.

**Detection:**
- Every eval task is tagged with a `compliance_class` field in the spec.

**Mitigation:**
- Tasks that exercise CVE-style behavior must run on local models only, not via cloud provider.
- Pheno-harness's `verifier/risky_action.py` enforces this on the harness side, but the eval driver should also refuse to send such tasks to cloud models.

---

## 19. Long-context drift

**What:** Ling-2.6-flash advertises 262K context. At that length, even small numerical differences in scoring can swing results wildly.

**Detection:**
- Every result row carries `context_length_used_p50/p95/p99`.

**Mitigation:**
- Compare models at matched context lengths (16K / 32K / 64K / 128K buckets).
- Report long-context (> 128K) results in a separate scoreboard with explicit caveats.

---

## 20. What this risks doc does **not** cover

- IP / copyright on training data (out of scope for the eval program).
- User-facing leaderboard fairness (out of scope; internal scoreboard only).
- Legal review of model outputs (handled by `verifier/risky_action.py`; not duplicated here).

If a new risk emerges during implementation, add it here and tag the relevant PR.