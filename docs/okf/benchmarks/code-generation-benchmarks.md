---
source_file: ChatGPT-Code Generation Benchmarks.md
sha256: placeholder-code-generation-benchmarks
topics: [benchmarks, codegen, humaneval, mbpp, swe-bench]
related_okf:
  - benchmarks/pairwise-test-case-generation.md
  - agents/feature-graph-system-design.md
evidence_class: L
status: stub — N10 priority, needs full distillation
---

# Code Generation Benchmarks

**Source:** `ChatGPT-Code Generation Benchmarks.md` — class **L**.

## Overview

HumanEval, MBPP, and SWE-Bench style eval for code synthesis and repo-level patch generation. Tracks pass@k, edit distance, and verifier-gated correctness.

## Cost

Codegen eval burns tokens on sampling (k=10) and execution sandboxes. Pairwise reduces 89-task×3-model sweeps to ~40 trials. Local 3090 handles <8B code models; larger via API routing.

## Safety

Untrusted generated code runs in sandbox only; no host exec. Benchmark includes injection and supply-chain checks. Promotion to **P** requires isolated container verification.

**Evidence:** `local://sha256/placeholder-code-generation-benchmarks` (class **L**).
