---
source_file: ChatGPT-Incorporation as Agent.md
sha256: ff316e9945f0d69f8389225fb7102eca765759b2b2c1da009ee70d7a233f68c3
topics: [agents, human-in-loop, mas, routing, orchestration, human-agent]
related_okf:
  - agents/coding-agents-intent-graphs.md
  - agents/feature-graph-system-design.md
evidence_class: L
status: stub — N10 priority, needs full distillation
---

# Incorporation as Agent

**Source:** `ChatGPT-Incorporation as Agent.md` (6 KB, 2026-06-14) — class **L**.

Incorporating the human founder as a **HumanAgent** node in the MAS org — not a manager bottleneck, but a scarce, high-value specialist with explicit routing rules separating required judgment from optional "stay sharp" work.

## Key insights (stub — full distillation pending N10)

- **Two routing lanes:** required-human (irreversible / product-direction / architecture veto / thesis-changing decisions) vs optional-human (isolated coding, review, debug kata, triage) — latter is interruptible, non-blocking, replaceable with agent fallback and defaults.
- **Bounded capacity config:** `max_required_interrupts_per_day`, `max_optional_tasks_per_day`, `preferred_task_length_minutes [15,45]`, avoid rote CRUD/formatting, prefer design judgment and hard debugging.
- **Human Task Router scoring:** `human_value_score = ambiguity + taste + irreversible_weight + learning/fun - automation_confidence - interruption/blocking_cost`; gates to `required_human_review | optional_human_task | agent_only`.
- **Claimable quests board:** system generates non-blocking quests (e.g., fix WebSocket reconnect test, review routing policy) that the human can accept/skip/delegate; required escalations carry `agent_recommendation`, `default_if_no_response`, deadline, reversibility, and affected FRs.
- **Agents must earn interruptions:** prove docs/ADR search, option generation, recommendation, default action, and quantified risk before escalating — no open-ended "what should we do?".

## Next (N10)

- Extract full `[L]`-tagged claims with `local://sha256/ff316e9945f0d6...` citations.
- Cross-link to `docs/okf/agents/coding-agents-intent-graphs.md`, `routing/latentmas-vs-textmas.md`, and `plans/2026-07-24-forward-dag-v2/INDEX.md` (Forward DAG human-in-loop).
- Verify against MAS/HITL primary sources before promoting to **P** and to `docs/specs/`.

**Evidence:** `local://sha256/ff316e9945f0d69f8389225fb7102eca765759b2b2c1da009ee70d7a233f68c3` (class **L**).
