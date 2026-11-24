---
source_file: ChatGPT-Long Context Eval.md
sha256: placeholder-long-context-eval
topics: [benchmarks, long-context, retrieval, needle]
related_okf:
  - benchmarks/pairwise-test-case-generation.md
  - inference/vram-scaling-factors.md
evidence_class: L
status: stub — N10 priority, needs full distillation
---

# Long Context Eval

**Source:** `ChatGPT-Long Context Eval.md` — class **L**.

## Overview

Needle-in-haystack, RULER, and InfiniteBench patterns for 32K-128K windows. Tests retrieval, aggregation, and multi-hop recall under KV-cache pressure and RoPE scaling.

## Cost

Context length drives KV memory linearly; 128K costs 4x 32K in VRAM and TPOT. Benchmark bins by length (4K/32K/128K) and reports $/verified_pass. Pairwise reduces length×model×task combos 90%.

## Safety

Long contexts amplify prompt injection and data exfiltration. Eval includes isolated tool-call checks and context sandboxing. Verify vs primary long-context suites before **P**.

**Evidence:** `local://sha256/placeholder-long-context-eval` (class **L**).
