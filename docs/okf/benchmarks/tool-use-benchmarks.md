---
source_file: ChatGPT-Tool Use Benchmarks.md
sha256: placeholder-tool-use-benchmarks
topics: [benchmarks, tool-use, function-calling, agents]
related_okf:
  - benchmarks/agent-flow-optimization.md
  - agents/coding-agents-intent-graphs.md
evidence_class: L
status: stub — N10 priority, needs full distillation
---

# Tool Use Benchmarks

**Source:** `ChatGPT-Tool Use Benchmarks.md` — class **L**.

## Overview

Function-calling accuracy, multi-tool chaining, and Tau-Bench style trajectory eval. Covers parallel calls, argument schema adherence, and recovery from tool errors.

## Cost

Tool-use traces bloat tokens 2-3x vs QA; benchmark measures $/successful_trajectory and latency to first tool call (TTFTc). Local cache of tool schemas cuts prompt overhead 15%.

## Safety

Tool eval must sandbox filesystem/network and gate risky actions (`rm`, `git push`, `curl|bash`) via `config/risky_action_gate.yaml`. Verify isolation before **P** promotion.

**Evidence:** `local://sha256/placeholder-tool-use-benchmarks` (class **L**).
