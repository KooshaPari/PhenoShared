# DESIGN.md

> **Status:** canonical design intent. Pointers to `docs/specs/` and `docs/adrs/` are authoritative.

## Pheno-Harness — Design Intent

PhenoLM is built around three orthogonal axes that are **never collapsed
into a single score** during development:

1. **Semantic quality.** Did the model solve the task correctly, robustly,
   safely, recoverably? See `docs/specs/001-eval-architecture.md` §5.1.
2. **Harness quality.** Did the tool loop, context assembly, planner,
   trace recorder help or hurt? See `docs/specs/001-eval-architecture.md` §5.2.
3. **Serving performance.** Did the engine / router deliver tokens fast
   and stably at the configured concurrency? See
   `docs/specs/001-eval-architecture.md` §5.3.

A single composite exists only for ranking — never for diagnosis.

## Layered Architecture

The stack is six layers (top → bottom):

```
┌─────────────────────────────────────────────────────────────┐
│  forge-dev (coding-agent CLI)                              │
│      │ default path                                         │
│      ▼                                                     │
│  omniroute-dev (outer router, OpenAI-compat, provider blend)│
│      │                                                     │
│      ▼                                                     │
│  PhenoLM (policy + eval + trace + garden loop) — this repo  │
│      │                                                     │
│      ▼                                                     │
│  pheno-serve-dev (inner inference router, engine lifecycle) │
│      │                                                     │
│      ▼                                                     │
│  engines: SGLang | vLLM | TensorRT-LLM | llama.cpp | MLX    │
│      │                                                     │
│      ▼                                                     │
│  bifrost / other substrate (below pheno-serve-dev, optional)│
└─────────────────────────────────────────────────────────────┘
```

Full contract: `docs/ARCHITECTURE_LAYERS.md`. Direct calls between
non-adjacent layers are allowed only when an eval cell is explicitly
measuring that lower layer, and the call must log the bypass.

## Bidirectional Intent-Graph Migration

PhenoLM today is a chat-loop harness. The next-era design is a typed
DAG (intent graph) where:

- **Strong planners** produce typed task DAGs.
- **Deterministic tools** (`ripgrep`, `ast-grep`, `pytest`, `cargo`,
  `tsc`, …) execute leaf nodes with no LLM cost.
- **Weak / local workers** handle cheap leaves (formatting, docstring
  polish, simple renames).
- **The strong model re-enters** only on ambiguity, design choices,
  `post`-predicate failure, or explicit review / merge steps.
- **A scheduler** parallelizes independent branches and reports queue
  depth to the perf suite.
- **A trace recorder** captures every model call, tool call, file diff,
  test result, metric, and final outcome, emit a `.graph.json` per run.

Migration is staged A → E (no behavior change in Stage A; full planner
+ multi-agent + strong re-entry by Stage E). See
`docs/specs/001-eval-architecture.md` §4 and
`docs/specs/004-implementation-plan.md` §9.

## Garden Loop

Promotions are gated and observable. Two consecutive green windows are
required; one lucky TB2 / DeepSWE result is not enough. A candidate that
improves pass rate while increasing unsafe actions, cost per success,
unreplayable runs, or crash rate is demoted. Full policy:
`docs/GARDEN_LOOP.md`.

## Local-First Workhorse Strategy

The current local evaluation set is deliberately limited to Qwen3.5 0.8B,
LFM 2.5 8B-A1B, and Ornith 1.0 9B. SGLang is the primary serving path on the
RTX 3090 Ti; vLLM is a cross-engine comparison path; TensorRT-LLM is a
compile-once candidate only after an evidence-backed winner exists. Cloud
evaluation is disabled by default and may be enabled only when the projected
full TB2.0 cost is at most $1 per model.

The 24 GB GPU uses quantized artifacts only (q2 through q8, plus eligible
NVFP4-type artifacts); BF16 is not an evaluation artifact. One SGLang slot is
resident at a time, and any engine start must use a pre-existing local model
directory, never a network model identifier.

Full plan and bootstrap commands: `docs/adrs/0003-local-serving-bootstrap.md`,
`docs/adrs/0007-current-local-serving-contract.md`,
`docs/specs/003-model-engine-matrix.md`.

## Eval Reproducibility Contract

Every eval run writes a manifest with: `commit_sha`, `model_id`,
`provider`, `route_kind`, `engine`, `quantization`, `hardware`,
`env`, `seeds`, `held_out_from_training`, `holdout_hash`, `artifacts`.

A run without this manifest is rejected by the scoreboard. The
manifest schema is in `docs/specs/001-eval-architecture.md` §6.

## Risks

Contamination, secret leakage, disk pressure, invalid comparisons,
overfitting, flaky envs, throughput mismeasurement, multi-agent
attribution, OpenRouter stability, self-improvement gaming, sub-agent
drift, latent-MAS bifurcation, pheno-specs submodule state, M1 Pro
under-spec trap, reproducibility gaps, dependency drift, compliance,
long-context drift. All 20 are catalogued in
`docs/adrs/0002-risks-register.md` with detection + mitigation.

## Out of Scope (this round)

- Latent-MAS encoding. Parked.
- Public leaderboard. Internal only.
- User-facing benchmark UI.
- Codex-fork migration. Gated on user sign-off.
- New training recipes beyond garden-loop promotions.
- Anything outside the four axes above.

## Non-goals

- Cloud-only routing. We are local-first.
- Single composite scoring during diagnosis.
- Silent engine version bumps.
- Auto-promotion without two consecutive green gates.
- Trace-derived evalset that contaminates training.
- Bench results that can't be reproduced from the manifest.
