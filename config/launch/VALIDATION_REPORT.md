# Launch Configuration Validation Report

**Generated:** 2026-07-23  
**Configs scanned:** 10  
**Status:** All YAML valid ✅

---

## Summary Table

| Config | Model ID | Backend | Context Length | Standalone | Suites | Est. Cells |
|--------|----------|---------|----------------|------------|--------|------------|
| `dense12.yaml` | tier1_5.dense12 | llama | — | yes | 0 | — |
| `draft_06b.yaml` | sub1b.draft_06b | — | — | **no** (draft) | 0 | — |
| `granite8.yaml` | tier1.granite8 | llama | — | yes | 0 | — |
| `lfm25_8b_a1b.yaml` | local.lfm25_8b_a1b | llama | — | yes | 0 | — |
| `moe30.yaml` | tier2.moe30 | llama | — | yes | 0 | — |
| `ornith_8b.yaml` | local.ornith_8b | llama | — | yes | 0 | — |
| `qwen35_08b.yaml` | local.qwen35_08b | llama | — | yes | 0 | — |
| `qwen4b.yaml` | tier0.qwen4b | llama | — | yes | 0 | — |
| `zaya8.yaml` | tier1.zaya8 | llama | — | yes | 0 | — |
| `qwen4b_bench.yaml` | Qwen/Qwen3.5-4B-Coder | **mlx** | **32768** | yes | **13** | ~**5,270+** |

---

## Per-Config Details

### 1. `dense12.yaml`
- **Model:** `tier1_5.dense12`
- **Description:** 12B dense distilled executor — on-demand
- **Args:** llama-server template (`{binary}`, `{path}`, `{port}`, `{kv_ctx}`, `-ngl 99`, `{ik_flags}`)
- **Suites:** None (server launch config only)

### 2. `draft_06b.yaml`
- **Model:** `sub1b.draft_06b`
- **Description:** Draft model attached to tier0.qwen4b via `-md` (not standalone server)
- **Standalone:** false
- **Suites:** None

### 3. `granite8.yaml`
- **Model:** `tier1.granite8`
- **Description:** Granite 4.1 8B — on-demand tool/schema lane
- **Args:** Standard llama-server template
- **Suites:** None

### 4. `lfm25_8b_a1b.yaml`
- **Model:** `local.lfm25_8b_a1b`
- **Description:** LiquidAI LFM 2.5 8B-A1B — on-demand local workhorse
- **Args:** Standard llama-server template
- **Suites:** None

### 5. `moe30.yaml`
- **Model:** `tier2.moe30`
- **Description:** Qwen3 30B A3B MoE — ik_llama expert offload (on-demand fallback)
- **Args:** Extended MoE flags: `-fa`, `-fmoe`, `-rtr`, `-ctk q8_0`, `-ctv q8_0`
- **Suites:** None

### 6. `ornith_8b.yaml`
- **Model:** `local.ornith_8b`
- **Description:** Ornith 8B alias — on-demand local coding-agent comparison
- **Args:** Standard llama-server template
- **Suites:** None

### 7. `qwen35_08b.yaml`
- **Model:** `local.qwen35_08b`
- **Description:** Qwen3.5 0.8B — always-on local drafter / tiny worker
- **Args:** Standard llama-server template
- **Suites:** None

### 8. `qwen4b.yaml`
- **Model:** `tier0.qwen4b`
- **Description:** Qwen4B always-on + optional 0.6B draft
- **Args:** Standard llama-server template
- **Draft args:** `-md {draft_path} --draft-max 16`
- **Suites:** None

### 9. `zaya8.yaml`
- **Model:** `tier1.zaya8`
- **Description:** ZAYA1 8B — on-demand debug/judge-lite lane
- **Args:** Standard llama-server template
- **Suites:** None

### 10. `qwen4b_bench.yaml` ⭐
- **Model ID:** `Qwen/Qwen3.5-4B-Coder`
- **Alias:** `local/qwen35-4b`
- **Backend:** `mlx`
- **Context length:** 32768
- **Quant:** q4
- **Estimated VRAM:** 3 GB
- **Energy source:** powermetrics (100ms sampling)
- **Judge mode:** deterministic
- **Run params:** n=5, seed=42

#### Suites (13 entries)

| # | Suite | Subset | Est. Cells (n=5) |
|---|-------|--------|-------------------|
| 1 | terminal-bench | 6 tasks (headless-terminal, log-summary-date-ranges, fix-code-vulnerability, build-cython-ext, sqlite-db-truncate, query-optimize) | 30 |
| 2 | deepswe | 16 | 80 |
| 3 | swe-bench-verified | regression-anchor | ~250* |
| 4 | mmlu-pro | 100 | 500 |
| 5 | gpqa-diamond | full | ~400* |
| 6 | hle | full | ~200* |
| 7 | arc-agi-2 | full | ~200* |
| 8 | perplexity | full | ~200* |
| 9 | custom-pheno-trace | smoke | ~25* |
| 10 | mt-bench | full | ~40* |
| 11 | ifeval | full | ~500* |
| 12 | bfcl-v4 | full | ~200* |
| 13 | kernelbench | L1 | ~50* |
| | | **Estimated total** | **~5,270+** |

*\* Estimated — exact subset sizes depend on dataset availability at runtime.*

---

## Tier Distribution

| Tier | Models |
|------|--------|
| tier0 | qwen4b |
| tier1 | granite8, zaya8 |
| tier1_5 | dense12 |
| tier2 | moe30 |
| local | lfm25_8b_a1b, ornith_8b, qwen35_08b |
| sub1b | draft_06b |

---

## Notes

- 9 of 10 configs are **llama-server launch templates** (args-based, no embedded suites).
- 1 config (`qwen4b_bench.yaml`) is a **bench run config** with full task matrix, energy/judge settings, and run parameters.
- `draft_06b.yaml` is the only non-standalone config (`standalone: false`).
- `moe30.yaml` is the only config with MoE-specific flags (`-fmoe`, `-rtr`, quant cache types).
- `qwen4b.yaml` is the only config with draft model support (`draft_args`).
- All YAML files parse cleanly; no syntax errors detected.
