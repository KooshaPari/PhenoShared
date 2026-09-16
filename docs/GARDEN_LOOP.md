# PhenoLM Garden Loop

The garden loop is the managed self-improvement system for PhenoLM. It turns
agent traces and benchmark runs into candidates, but it does not let candidates
change routing, prompts, local models, or training policy unless gates pass.

## Loop Stages

1. Observe
   - Collect traces, perf counters, benchmark results, cost, and safety events.
   - No behavior changes are made in this stage.

2. Score
   - Convert observations into task, role, route, and serving-engine metrics.
   - Store rows in the append-only ledger.

3. Propose
   - Produce candidates: route weight changes, prompt policy edits, local model
     promotions, DPO/LoRA candidates, or serving-engine config changes.
   - Every candidate includes a rollback plan.

4. Gate
   - Run holdout, regression, safety, budget, reproducibility, and serving
     stability gates from `config/garden_loop.yaml`.

5. Promote or demote
   - Promote only after two consecutive green windows.
   - Demote immediately on required-gate failure, missing manifest, or secret
     leak.

## Required Separation

The garden loop must keep these signals separate:

- Model quality: did the model solve the task?
- Agent harness quality: did the tool loop, context assembly, and planner help?
- Serving performance: did the engine/router deliver tokens fast and stably?
- Economic quality: did cost per accepted verified step improve?

Combining those too early hides the actual bottleneck.

## Current Implementation

The observation-only spine is implemented in `harness/self_improvement/` and
`scripts/run_self_improvement_tick.py --dry-run`:

- `signals.py` aggregates numeric observations by role/lane.
- `gates.py` evaluates holdout, regression, safety, budget, reproducibility,
  and serving stability, failing closed on missing required signals.
- `retention.py` previews 30-day archival eligibility without modifying the
  append-only ledger.
- `promotion.py` requires two consecutive green windows and explicit human
  approval, and returns a non-mutating decision.

`scripts/gardener.py --observe --dry-run` remains the low-level ledger-row
writer. No automatic promotion, config mutation, weight change, or training
action is permitted by the garden tick.

## Promotion Policy

A candidate can promote only if all required gates in `config/garden_loop.yaml`
are green in two consecutive windows. One lucky TB2/DeepSWE result is not
enough. A candidate that improves pass rate while increasing unsafe actions,
cost per success, unreplayable runs, or crash rate is demoted.
