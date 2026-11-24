---
source_file: ChatGPT-Reasoning Benchmarks.md
sha256: placeholder-reasoning-benchmarks
topics: [benchmarks, reasoning, eval, chain-of-thought]
related_okf:
  - benchmarks/pairwise-test-case-generation.md
  - benchmarks/model-inference-costs-2026.md
evidence_class: L
status: stub — N10 priority, needs full distillation
---

# Reasoning Benchmarks

**Source:** `ChatGPT-Reasoning Benchmarks.md` — class **L**.

## Overview

Eval suites for multi-step reasoning: GSM8K, MATH, MMLU-pro reasoning splits and custom chain-of-thought traces. Measures verified pass rate and step fidelity, not just final answer.

## Cost

Per-problem cost dominated by output tokens (CoT length 300-800 tokens). Pairwise sampling reduces 2000-problem sweeps to ~40 representative items. Local 3090 at $0.35/hr amortizes vs API 10x token premium.

## Safety

CoT traces may leak intermediate plans. Safety eval checks for deceptive reasoning and sycophancy. Gate via `config/risky_action_gate.yaml` before promotion to **P**.

**Evidence:** `local://sha256/placeholder-reasoning-benchmarks` (class **L**).
