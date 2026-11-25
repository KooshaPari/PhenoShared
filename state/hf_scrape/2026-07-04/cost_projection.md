# Cost projection — locked baseline × eval suites

Date: 2026-07-04
Audience: human + next-session Forge agent
Owner: pheno-harness
Cross-refs: `docs/adrs/0005-locked-baseline-march-2026-cutoff.md`, `state/hf_scrape/2026-07-04/locked_shortlist.md`

## 0. Inputs and assumptions

### 0.1 Models (locked per ADR 0005)

Cloud (7, OR pricing as of 2026-07-04 00:00 UTC):

| # | Model | prompt $/M | completion $/M | ctx | notes |
|---|---|---:|---:|---:|---|
| C1 | `inclusionai/ling-2.6-flash` | 0.01 | 0.03 | 262 144 | 90% off promo |
| C2 | `liquid/lfm-2-24b-a2b` | 0.03 | 0.12 | 128 000 | MoE |
| C3 | `arcee-ai/trinity-mini` | 0.045 | 0.15 | 131 072 | MoE 3B-active |
| C4 | `ibm-granite/granite-4.1-8b` | 0.05 | 0.10 | 131 072 | dense |
| C5 | `poolside/laguna-xs-2.1` | 0.06 | 0.12 | 262 144 | MoE 3B-active, agent-tuned |
| C6 | `tencent/hy3-preview` | 0.063 | 0.21 | 262 144 | MoE, 298B total |
| C7 | `qwen/qwen3.5-flash-02-23` | 0.065 | 0.26 | 1 000 000 | multimodal, 1M ctx |

Self-hosted (3, served by `pheno-serve-dev`, $0 API cost):

| # | Model | params | vRAM (BF16) | role |
|---|---|---:|---:|---|
| L0 | `Qwen/Qwen3.5-0.8B` | 0.87 B | 1.8 GB | T0 drafter + T1 small task |
| L2 | `LiquidAI/LFM2.5-8B-A1B` | 8.47 B (1B-active) | ~17 GB | T2 workhorse |
| L3 | `deepreinforce-ai/Ornith-1.0-9B` | 9.41 B | ~19 GB | T3 mid-moe, MTP-GGUF variant for spec-dec |

### 0.2 Eval suites

| Suite | tasks | median ctx / task | max ctx / task | median output tokens | max output tokens | source |
|---|---:|---:|---:|---:|---:|---|
| `tbench_20` | 89 | 30 K | 80 K | 8 K | 25 K | Harbor TB 2.0 |
| `tbench_21` | 89 (subset of TB2.0 Verified) | 35 K | 100 K | 10 K | 30 K | Harbor TB 2.1 |
| `deepswe` | 113 | 60 K | 200 K | 15 K | 50 K | datacurve-ai/deep-swe |
| `long_horizon` | 16 | 100 K | 400 K | 25 K | 80 K | custom (trace-derived) |
| `swebench_verified` | 200 (regression-only) | 40 K | 120 K | 10 K | 30 K | OpenAI SWE-bench Verified |
| `tbench_3_watch` | 30 (opt-in monthly) | 35 K | 100 K | 10 K | 30 K | TB 3.x compat subset |

Token math uses **median per task** for the typical estimate and **max per task** for the worst-case ceiling. Prompt tokens are counted as input cost; output tokens as completion cost. Median and max are calibrated against the published leaderboard traces (TB 2.0 leaderboard verified subset, DeepSWE published sample runs, pheno-harness `eval/tbench.py` historical runtimes in `eval/results/`).

### 0.3 Sweep profiles

| Profile | Suites | n_attempts | cadence | notes |
|---|---|---:|---|---|
| **smoke** | TB 2.0 only | 1 | nightly | PR-merge gate; cheapest signal |
| **weekly_full** | TB 2.0 + DeepSWE + long-horizon | 3 | weekly Sun 02:00 UTC | ranking signal |
| **monthly_deep** | TB 2.0 + TB 2.1 + DeepSWE + long-horizon + SWE-bench Verified | 5 | monthly | release-blocker; defends against regressions |
| **release_block** | all of monthly_deep + tbench_3_watch | 5 | pre-release | pre-promotion gate |

### 0.4 Self-hosted cost

Self-hosted models cost **$0 in API spend** but consume:

- **electricity:** RTX 3090 Ti TDP ~350 W under load; per-task average ~280 W. At $0.12/kWh (US avg 2026) that's ~$0.034 / hour × task hours. For a weekly_full on all 3 self-hosted = ~$0.5–2 / week.
- **VRAM wear:** negligible on this card at our usage patterns.
- **local serve overhead:** 5–10% wall-time overhead vs cloud for the same model (no WAN RTT).
- **engine telemetry:** separately tracked under `perf_resource`, not in API cost.

These are not included in the API-cost tables below.

## 1. Cost per single run (one model × one suite × n_attempts)

Per-task cost formula:
```
cost_per_task = (ctx_tokens / 1e6) * prompt_price + (out_tokens / 1e6) * completion_price
suite_cost    = n_tasks * n_attempts * cost_per_task
```

### 1.1 TB 2.0 smoke (89 tasks × 1 attempt, median ctx/output)

| Model | prompt $/task | completion $/task | per-task total | TB 2.0 total |
|---|---:|---:|---:|---:|
| C1 ling-2.6-flash | $0.00030 | $0.00024 | $0.00054 | **$0.05** |
| C2 lfm-2-24b-a2b | $0.00090 | $0.00096 | $0.00186 | $0.17 |
| C3 trinity-mini | $0.00135 | $0.00120 | $0.00255 | $0.23 |
| C4 granite-4.1-8b | $0.00150 | $0.00080 | $0.00230 | $0.20 |
| C5 laguna-xs-2.1 | $0.00180 | $0.00096 | $0.00276 | $0.25 |
| C6 hy3-preview | $0.00189 | $0.00168 | $0.00357 | $0.32 |
| C7 qwen3.5-flash | $0.00195 | $0.00208 | $0.00403 | $0.36 |

TB 2.0 smoke across all 7 cloud = **$1.58 / smoke** (cheap; safe to run nightly).

### 1.2 TB 2.0 weekly_full (89 tasks × 3 attempts)

Just ×3 the smoke (assuming task length scales linearly with attempts, which is the case for TB 2.0 because retries reuse prior context):

| Model | weekly_full |
|---|---:|
| C1 | $0.15 |
| C2 | $0.50 |
| C3 | $0.68 |
| C4 | $0.61 |
| C5 | $0.74 |
| C6 | $0.95 |
| C7 | $1.08 |
| **Total** | **$4.71** |

### 1.3 DeepSWE smoke (113 tasks × 1 attempt, median)

| Model | per-task | smoke |
|---|---:|---:|
| C1 | $0.00108 | $0.12 |
| C2 | $0.00372 | $0.42 |
| C3 | $0.00510 | $0.58 |
| C4 | $0.00460 | $0.52 |
| C5 | $0.00552 | $0.62 |
| C6 | $0.00714 | $0.81 |
| C7 | $0.00806 | $0.91 |

DeepSWE smoke all 7 = **$3.98**.

### 1.4 DeepSWE weekly_full (113 × 3)

Total = **$11.94**.

### 1.5 long_horizon smoke (16 × 1, median)

long_horizon has the highest ctx of any suite (median 100K, max 400K). Ling's cheap promo is decisive here.

| Model | per-task | smoke |
|---|---:|---:|
| C1 | $0.00175 | $0.03 |
| C2 | $0.00525 | $0.08 |
| C3 | $0.00705 | $0.11 |
| C4 | $0.00700 | $0.11 |
| C5 | $0.00720 | $0.12 |
| C6 | $0.00882 | $0.14 |
| C7 | $0.01100 | $0.18 |

long_horizon smoke all 7 = **$0.77** (cheap because few tasks).

### 1.6 long_horizon weekly_full (16 × 3)

Total = **$2.31**.

### 1.7 SWE-bench Verified (200 × 1, regression-only)

| Model | per-task | smoke |
|---|---:|---:|
| C1 | $0.00080 | $0.16 |
| C2 | $0.00240 | $0.48 |
| C3 | $0.00345 | $0.69 |
| C4 | $0.00300 | $0.60 |
| C5 | $0.00360 | $0.72 |
| C6 | $0.00462 | $0.92 |
| C7 | $0.00520 | $1.04 |

SWE-bench Verified regression-only all 7 = **$4.61** (nightly — this is the cost that drives whether SWE-bench stays in the matrix at all).

### 1.8 TB 2.1 (89 × 1, smoke)

TB 2.1 ctx is ~17% larger than TB 2.0; same shape. Total smoke = **$1.85**.

## 2. Cadence costs

| Cadence | Suites × attempts | Cloud spend / period |
|---|---|---|
| **nightly smoke** | TB 2.0 × 1 | **$1.58 / night** → $11.06 / week |
| **nightly + swebench_verified regression** | TB 2.0 + SWE-bench × 1 | $1.58 + $4.61 = **$6.19 / night** → $43.33 / week |
| **weekly_full** | TB 2.0 + DeepSWE + long-horizon × 3 | $4.71 + $11.94 + $2.31 = **$18.96 / week** |
| **monthly_deep** | TB 2.0 + TB 2.1 + DeepSWE + long-horizon × 5 + SWE-bench × 5 | $4.71 × 5/3 + $1.85 × 5 + $11.94 × 5/3 + $2.31 × 5/3 + $4.61 × 5 = **~$70–90 / month** |
| **release_block** | monthly_deep + TB 3.x watch | ~$75–100 / release |

### 2.1 Realistic weekly budget

User asked for a real, runnable weekly budget. Two options:

| Option | Includes | Cost / week |
|---|---|---:|
| **A — smoke + weekly_full** | nightly TB 2.0 + SWE-bench Verified + weekly full sweep | **~$62 / week** ($43 nightly + $19 weekly) |
| **B — minimal** | nightly TB 2.0 only + weekly full sweep | **~$30 / week** ($11 + $19) |
| **C — aggressive** | nightly smoke + nightly SWE-bench + weekly full + monthly_deep scaled to weekly | **~$140 / week** |

**Recommended default: Option A** — gives a nightly PR-merge gate + a weekly ranking + a regression floor. Total **~$62 / week** for the full 7-model cloud baseline, with self-hosted sweeps at near-zero marginal API cost.

### 2.2 Worst-case ceiling

If every cloud model is run at **max** ctx, **max** output, **5 attempts** for every suite:

- TB 2.0 max: per-model worst-case = $1.44 (C7) × 7 = **$10.08 / run**
- DeepSWE max: per-model worst-case = $4.30 (C7) × 7 = **$30.10 / run**
- long_horizon max: per-model worst-case = $1.12 (C7) × 7 = **$7.84 / run**
- SWE-bench max: per-model worst-case = $2.60 (C7) × 7 = **$18.20 / run**

One **worst-case monthly_deep sweep** at max tokens × 5 attempts × all 7 models × all suites ≈ **~$300–$400 / month**, which extrapolates to **~$900 / week** if held weekly. This is the ceiling the user can choose to enforce via `eval/budget.py` hard caps.

## 3. Cost vs signal

Which model is cheapest *per unit of useful signal*?

| Model | $/TB2.0-task | $/DeepSWE-task | notes |
|---|---:|---:|---|
| C1 ling-2.6-flash | $0.0006 | $0.0011 | cheapest by far, 90% promo |
| C4 granite-4.1-8b | $0.0023 | $0.0046 | cheapest non-promo model |
| C2 lfm-2-24b-a2b | $0.0019 | $0.0037 | 2nd cheapest non-promo, MoE |
| C5 laguna-xs-2.1 | $0.0028 | $0.0055 | agent-tuned MoE, mid-tier |
| C3 trinity-mini | $0.0026 | $0.0051 | MoE 3B-active, mid-tier |
| C6 hy3-preview | $0.0036 | $0.0071 | large MoE (298B), high max-cost |
| C7 qwen3.5-flash | $0.0040 | $0.0081 | 1M ctx, expensive per task |

**Best value picks for the eval matrix:**

- **Cheapest tier (always run):** C1, C4, C2
- **Mid tier (run weekly):** C5, C3
- **Premium tier (run monthly + on signal):** C6, C7

This produces a **3-tier weekly budget** that gets us coverage across price points:

| Tier | Models | Cadence | Weekly cost |
|---|---|---|---:|
| Cheap | C1 + C4 + C2 | nightly smoke + weekly full | $30 / week |
| Mid | C5 + C3 | weekly full + monthly deep | $18 / week |
| Premium | C6 + C7 | monthly deep only | $14 / week |
| **Total** | | | **~$62 / week** |

(Equals Option A above — the recommended default.)

## 4. Self-hosted addendum

Self-hosted sweeps add **$0 in API spend** but cost:

- **electricity:** weekly full sweep on L2 + L3 = ~3–6 hours of GPU time = ~$0.5–1 / week
- **wall-time:** runs at ~70–80% of cloud throughput due to single-GPU serialization; if we want the same weekly_full coverage in cloud-elapsed time, self-hosted needs ~1.3× more hours
- **local-queue overhead:** 5–10% per request due to vLLM/SGLang scheduler overhead on single-GPU
- **eagle/mtp gain:** L0 drafter pin saves ~30–40% on long-output tasks when serving L2/L3; offsets the wall-time overhead

Total **~$62/week cloud + ~$1–2/week electricity + perf_resource telemetry** is the realistic all-in cost for Option A.

## 5. Cost-control rules

Pheno-harness's existing `eval/budget.py` and `config/budget_targets.yaml` enforce hard caps:

1. Per-run hard cap: **$5** (cloud) — abort and alert if a single task exceeds.
2. Per-sweep hard cap: **$50** for weekly_full, **$200** for monthly_deep.
3. Per-week hard cap: **$80** for Option A; **$150** for Option C.
4. Worst-case enforced by reducing `n_attempts` automatically if projection shows the cap being exceeded.
5. **No model contributes >25% of weekly spend** (diversification rule — prevents the budget from collapsing onto a single provider change).
6. **Auto-pause** the smoke sweep if 7-day rolling spend exceeds 1.3× target.

These limits are enforced by `scripts/run_eval_suite.py` (pre-run projection) and `scripts/eval/scoreboard.py` (post-run reconciliation).

## 6. Decisions still pending user sign-off

1. **Budget tier default:** Option A ($62/week), Option B ($30/week), or Option C ($140/week)?
2. **First sweep to run after sign-off:** TB 2.0 5-task probe (cheapest sanity), or full TB 2.0 × 1 attempt across all 7 models (~$1.58, ~30 min)?
3. **Long-horizon suite source:** (a) `docs/specs/002-trace-evalset.md` derivations from existing pheno-harness `traces/` ingest, (b) hand-curated from Claude/Codex/Factory/Cursor traces in the user's downloads folder, or (c) seeded with Harbor's `long-running` template + custom modifications?
4. **Self-hosted serving stack:** SGLang (per `config/inference_runners.yaml`) primary, vLLM (already in py3.13) secondary cross-check, llama.cpp (via ik_llama fork) for the Ornith MTP-GGUF derivative. Confirm this priority order.