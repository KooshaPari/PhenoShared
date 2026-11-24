---
source_file: ChatGPT-Model improvements under $500.md
sha256: 7cb2b0065d42ac484ade5fb87b3157cb8b3b4722122bcefe122ca31ce3a85348
topics: [hardware, inference, cost, budget, model-improvements]
related_okf:
  - hardware/rtx-3090-throughput.md
  - inference/kimi-deepseek-moe-cost.md
  - inference/efficiency-evolutions-post-moe.md
evidence_class: L
status: stub — N10 priority, needs full distillation
---

# Model Improvements Under $500

**Source:** `ChatGPT-Model improvements under $500.md` (13.1 KB, 2026-07-04) — class **L**.

$500 is not a model-training budget but a **harness + data + eval** budget. The corpus argues the highest ROI under $500 is not finetuning but **better eval harnesses, smarter routing, and cheaper inference** — exactly the levers Forward DAG N06–N09 (Portage rep-6, TB2.1) and N19 (model routing) target.

## Key insights (stub)

- **Eval-first:** $0–$100 on `harbor-TB2` native adapter + `pheno_eval_batch.py` (N21) yields more signal than $500 on LoRA — scoreable results beat unmeasured finetunes.
- **Routing cheaper than retraining:** `local/qwen35-08b` via :21080 at $0/hr vs API at $2–$5/1M tokens — N19 ladder saves 60% tokens before any model change.
- **Quant + speculative:** 8B Qwen at Q4/Q5 (via `quantization_plan.yaml`) + `agent-aware-speculative-decoding` (JetSpec/DDTree) improves `tg64` without new weights.
- **Hardware:** 3090 Ti rental $0.50/hr vs A100 $2/hr — 3090 is 4× cheaper for 8B MoE staging (see `hardware/rtx-3090-throughput.md`).

## Next (N10)

- Extract full `[L]` claims with `local://sha256/7cb2b0065d42...` citations.
- Verify against `config/budget_targets.yaml` and `benchmark_registry` before **[P]**.
- Link to `plans/2026-07-24-forward-dag-v2/INDEX.md` N19/N20 cost controls.

**Evidence:** `local://sha256/7cb2b0065d42ac484ade5fb87b3157cb8b3b4722122bcefe122ca31ce3a85348` (class **L**).
