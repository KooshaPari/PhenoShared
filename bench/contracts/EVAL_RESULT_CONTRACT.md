# pheno-harness → oMLX Result Interchange Contract

> Author: feynman (Chat 3)
> Status: **proposed v0.1** — not yet accepted by Chat 6 producer or Argis consumer
> Scope: cross-repo JSON schema for V4+ real-model runs.
> This document is **specification only**. It does not modify any harness or oMLX source.
> Backed by: `pheno-harness` repo at HEAD `5dbe919`, branch `main`, dirty = untracked only.

## Purpose

`stock_vs_ours.py` emits a per-cell Python report. Argis's oMLX eval-harness consumer
needs a stable, versioned, hash-pinned JSON contract that proves a real run happened.
This file pins:

1. The minimal JSON schema every artifact must satisfy.
2. Producer-side acceptance cases Chat 6 must meet before handoff.
3. Consumer-side acceptance cases Argis's oMLX eval-harness must meet before ingest.
4. The fields Chat 6's existing `SuiteResult` / `TaskResult` types do **not** already
   provide, and which the contract adds as required additions.

## Truth policy applied

Per the cross-chat alignment document (truth and evidence policy):

- Every cell in the report must be labeled **live verified** at the named HEAD,
  **historical**, or **inferred**. No label is "passed by default".
- Source/scaffold readiness is not production readiness. The 10-suite matrix is the
  comparison-runner layer, separate from the 4-suite Rust eval-harness and the
  23-suite registry. They are not interchangeable evidence.
- Substitutes (Qwen2.5 NIAH, cached Qwen3.5, syntax-valid Python) are explicitly
  labeled in `provenance.substitute` and are not real-model end-to-end proof.

## Versioning

| Version | Status | Notes |
|---|---|---|
| `0.1`   | proposed | this document — first proposal from feynman |
| `0.2`   | future   | incorporate Chat 6 producer review |
| `1.0`   | future   | accept only after Argis consumer implementation passes acceptance case C2 |

Producer must emit `"contract_version": "0.1"` in every artifact. Consumer must
reject unknown major versions.

### Cell pass metrics (v0.2, PR1)

Per-cell `gen_ok`, `verified_pass_at_1`, and dual-write `pass_at_1` are defined in
`bench/contracts/CELL_PASS_METRICS.md`. For `evidence_label == "reported"`,
consumers prefer `gen_ok` and treat legacy `pass_at_1` as a `gen_ok` alias.

### Cell assignment + transcript (v0.3)

Per-cell `task_title`, `task_description`, `acceptance`/`rubric`, full
`prompt`/`reply`, and SpanKind `progress_trace`/`chat_trace` are defined in
`bench/contracts/CELL_ASSIGNMENT.md`. Producers dual-write nested `assignment`
and transcript aliases for cockpit Canvas task pages.

## Top-level schema (required)

```jsonc
{
  "contract_version": "0.1",                          // REQUIRED: semver string
  "artifact_kind": "EvaluationReport",                // REQUIRED: fixed enum, see below
  "schema_hash": "<sha256 of canonicalized schema>",  // REQUIRED: lets consumer detect drift

  "producer": {
    "repo": "pheno-harness",
    "head": "5dbe919...",                             // REQUIRED: exact git rev
    "branch": "main",
    "dirty_paths": ["bench/comparison/stock_vs_ours.py"], // REQUIRED: untracked or modified
    "host": {                                         // OPTIONAL but recommended
      "os": "macos",
      "chip": "M1 Pro",
      "mlx_server_url": "http://127.0.0.1:8765/v1"
    }
  },

  "run": {
    "run_id": "<uuid4>",                              // REQUIRED
    "started_at": "2026-07-19T20:00:00Z",              // REQUIRED: ISO-8601 UTC
    "stopped_at": "2026-07-19T20:35:00Z",              // REQUIRED
    "variant": "stock",                               // REQUIRED: "stock" | "ours"
    "model": "Qwen/Qwen3.5-0.8B",                     // REQUIRED: matches served name
    "model_revision": "<huggingface commit sha>",     // REQUIRED when available
    "judge_mode": "deterministic",                    // REQUIRED: enum
    "energy_source": "none",                          // REQUIRED: enum
    "executed_by": "fe8762e-river-3",                  // REQUIRED: agent identity
    "command": "python -m bench.comparison.stock_vs_ours --variant stock --n 25", // REQUIRED
    "evidence_label": "live verified"                 // REQUIRED: enum
  },

  "matrix": {                                         // REQUIRED
    "suites": ["mmlu-pro","gpqa-diamond","aime",
               "arc-agi-2","livecodebench","aider-polyglot",
               "swe-bench","swe-bench-pro","bfcl","terminal-bench"],
    "tasks_per_suite": 25,
    "variants": ["stock", "ours"],
    "total_cells": 500
  },

  "suites": [                                         // REQUIRED: one entry per suite+variant
    {
      "suite": "mmlu-pro",
      "n": 25,
      "passed": 25,
      "wrong": 0,
      "errored": 0,
      "pass_at_1": 1.000,                             // REQUIRED: 4 decimal places
      "partial_credit_mean": null,                    // OPTIONAL: null if N/A
      "wall_clock_s": 17.1,
      "tokens_in": 4823,
      "tokens_out": 1204,
      "evidence_label": "live verified",              // REQUIRED per suite
      "provenance": {                                 // REQUIRED
        "dataset_revision": "<pinned hash or hf commit>",
        "synthetic": false,
        "substitute": null
      },
      "task_results": [                               // REQUIRED
        {
          "task_id": "mmlu-pro-001",
          "status": "ok",                             // enum: ok | wrong | error | skipped
          "prompt_hash": "<sha256>",
          "completion_hash": "<sha256>",
          "expected_hash": "<sha256>",
          "wall_clock_s": 0.68,
          "tokens_in": 193,
          "tokens_out": 47,
          "first_token_latency_s": 0.041,
          "tool_calls": [],
          "cached": false,
          "error": null,
          "evidence_label": "live verified"
        }
      ]
    }
  ],

  "totals": {                                         // REQUIRED
    "pass_at_1": 1.000,                               // weighted across all 10 suites
    "passed": 500,
    "wrong": 0,
    "errored": 0,
    "wall_clock_s": 1026.7,
    "tokens_in": 48230,
    "tokens_out": 12040,
    "energy_total": null
  },

  "comparator": {                                     // REQUIRED when both variants present
    "delta_pass_at_1": 0.000,                         // ours - stock, 4 decimal places
    "winner": "tie",                                  // stock | ours | tie
    "p_value": null                                   // null until n is large enough
  },

  "hash_chain": {                                     // REQUIRED
    "top_level_sha256": "<sha256 of canonicalized body minus hash_chain>",
    "task_ids_sorted_sha256": "<sha256 of sorted task_id list>"
  }
}
```

## Enums

- `artifact_kind`: only `"EvaluationReport"` is accepted in v0.1.
- `evidence_label`: `"live verified" | "historical" | "reported" | "inferred" | "unknown"`.
- `variant`: `"stock" | "ours"`.
- `judge_mode`: `"deterministic" | "llm"`.
- `energy_source`: `"none" | "m1_pmu" | "nvidia_smi"`.
- `task status`: `"ok" | "wrong" | "error" | "skipped"`.
- `comparator.winner`: `"stock" | "ours" | "tie"`.
- `provenance.substitute`: `null` for real runs; one of `"qwen2.5-substitute"`, `"cached-only"`,
  `"syntax-only"`, `"synthetic"` when the run is not a real-model end-to-end proof.

## Mapping to existing pheno-harness types

`pheno-harness` already defines `SuiteResult` and `TaskResult` in `bench/types.py`. The
contract reuses those field names so Chat 6 can emit artifacts without an extra translation
layer. Fields the contract **adds** beyond `SuiteResult`:

- `producer.*`, `run.*` (except `run_id`), `matrix.*`, `totals.evidence_label`,
  `comparator.*`, `hash_chain.*`, `provenance.*`, `prompt_hash`, `completion_hash`,
  `expected_hash`, `task_id` invariant for stable sort, `schema_hash`,
  `evidence_label` per-task and per-suite.

Producer implementation note for Chat 6: emit `SuiteResult.to_dict()` first, then wrap
in the contract envelope and attach the contract-only fields. **No changes to
`bench/types.py` are required by this contract** — Chat 6 can choose to add them or
populate at emit time only.

## Producer-side acceptance cases

Chat 6 must satisfy **all** of the following before the artifact is considered ready
for handoff to Argis:

| ID | Acceptance case | Pass criterion |
|---|---|---|
| **P1** | Exact HEAD recorded | `producer.head` equals `git rev-parse HEAD` of the producer worktree |
| **P2** | Dirty paths declared | Every untracked or modified file in `git status --porcelain` appears in `producer.dirty_paths` |
| **P3** | Real run evidence label | At least one suite carries `evidence_label = "live verified"` AND that suite's `provenance.substitute == null` AND `provenance.synthetic == false` |
| **P4** | Pinned dataset revision | Every suite that has a real dataset carries `provenance.dataset_revision` |
| **P5** | Stable task_id ordering | `task_results` is sorted by `task_id` lexicographically; `hash_chain.task_ids_sorted_sha256` matches `sha256("\n".join(sorted(task_ids)))` |
| **P6** | Schema hash matches | `schema_hash` equals `sha256` of the canonicalized schema body in this document |
| **P7** | pass@1 = passed/n | For every suite, `pass_at_1 == round(passed/n, 4)`; consumer verifies |
| **P8** | No silent error hiding | `errored > 0` suites must include at least one `task_results[].status == "error"` with a non-null `error` string |
| **P9** | Variant isolation | Stock and ours are emitted as **separate artifacts** with their own `run.variant`; the comparator is computed at consumer time, not faked at producer time |
| **P10** | No stub data | Every numeric value in `totals` and `suites` is backed by a real measurement in the run log; nothing is "rounded to 1.000 by default" |

## Consumer-side acceptance cases

Argis's oMLX eval-harness consumer must satisfy **all** of the following before
ingesting an artifact:

| ID | Acceptance case | Pass criterion |
|---|---|---|
| **C1** | Reject unknown major version | `contract_version` must parse as `0.x`; reject otherwise |
| **C2** | Verify schema hash | Recompute `sha256` of the embedded canonicalized schema and compare to `schema_hash`; mismatch = reject |
| **C3** | Verify top-level hash | Recompute `sha256` of canonicalized body with `hash_chain` stripped and compare; mismatch = reject |
| **C4** | Verify task identity | Every `task_results[].task_id` is unique within its suite AND matches `bench/spec.py` registry for the named suite |
| **C5** | Pass@1 cross-check | Independently compute `passed / n` and compare to `pass_at_1`; mismatch = reject |
| **C6** | Evidence gate | Only artifacts whose `totals.evidence_label == "live verified"` AND `provenance.synthetic == false` AND `provenance.substitute == null` advance the oMLX FR-5 promotion gate; all others are recorded but do not count |
| **C7** | Comparator transparency | When both stock and ours are present, `comparator.delta_pass_at_1 == ours.pass_at_1 - stock.pass_at_1` (4dp); reject otherwise |

## Worked example (acceptance scenarios)

```text
Scenario A — V4 real run succeeds end-to-end
  producer publishes EvaluationReport(contract_version="0.1", head=NEW_HASH,
                                     evidence_label="live verified",
                                     provenance.synthetic=false,
                                     provenance.substitute=null)
  → consumer C1..C5 PASS, C6 advances promotion, C7 computes comparator.

Scenario B — V4 ran on cached Qwen3.5 only (no live MLX server hit)
  producer must label evidence_label="reported" OR
                     provenance.substitute="cached-only"
  → consumer C6 records but does NOT advance promotion. Salmon blocked until
    a real-MLX-server artifact lands.

Scenario C — V4 ran with synthetic tasks (no real dataset)
  producer must label provenance.synthetic=true
  → consumer C6 records but does NOT advance promotion. Same outcome as B.

Scenario D — V4 file is syntax-valid but never executed
  → no EvaluationReport exists; nothing to ingest. feynman's prior "V4 file
    syntax-valid" claim is explicitly withdrawn. It is not acceptance case evidence.
```

## What this contract does NOT cover

- **FR-7 dashboard schema**: owned by Salmon + (Hawking if external chat exists).
  This contract only covers evaluation results, not UI panels.
- **Mojo/CUDA/Swift-Metal tier performance metrics**: those are runtime benchmarks,
  not eval harness results. They live in their own layer.
- **hwLedger preservation metadata**: owned by Hopper; separate contract.
- **OmniRoute Bifrost or ADR-032 observability metrics**: owned by Chat 2 / resolver.
- **Portage/Harbor adapter JSON**: owned by Rutherford; separate contract.
- **helios-cli invocation traces**: owned by Turing; separate contract.

## Handoff protocol

1. **feynman → Chat 6**: this document is the proposal. Chat 6 reviews and either
   accepts, proposes amendments, or rejects. Feynman does **not** edit
   `pheno-harness` source after handoff.
2. **Chat 6 → feynman**: when Chat 6 publishes the first immutable V4 artifact,
   feynman performs acceptance cases P1–P10 **without** rerunning the harness.
   Returns a one-page sign-off listing which cases passed, which failed, and
   whether the artifact may proceed to Argis.
3. **feynman → Argis**: Argis implements C1–C7 against this document. Feynman
   reviews the consumer implementation for parity but does not author it.
4. **Argis → Salmon**: Salmon only accepts promotion evidence that has passed C6.

## Downgraded readiness claims (feynman, explicit)

| Prior claim | Status now |
|---|---|
| "production-ready" | **withdrawn** — source/scaffold readiness ≠ production readiness |
| "Mojo, CUDA, Swift/Metal validated" | **withdrawn** — scaffolds are unbuilt, ABI parity not demonstrated |
| "V4 complete" | **withdrawn** — syntax-valid Python is not a completed 500-cell run |
| "Rust/C/Go/Nim/Zig source compiles" | **historical** — verified once at `d8ac9ed`, not rerun at current heads |
| "turbo_quant_encode 4.5 ms / 222 MB/s on M1 Pro" | **reported** — observed in earlier session, not live-verified in this session |
| "NIAH on Qwen2.5-0.5B @ 32K: 21 MB compacted" | **reported** — Qwen2.5 is a substitute, regression test only |
| "Qwen3.5-0.8B-OptiQ-4bit downloaded" | **reported** — model on disk but not proof of oMLX weight loading or decode |

## File-level evidence for handoff

`pheno-harness` worktree state at handoff (untracked, not committed):

```
?? bench/comparison/load_test.py
?? bench/comparison/report.py
?? bench/comparison/semantic_analysis.py
?? bench/comparison/stock_vs_ours.py        (1247 lines, 10 suites, 6 dispatcher branches)
?? bench/dashboard/
?? bench/results/stock-vs-ours/
?? bench/results/stock_vs_ours_qwen0.8.md
```

`stock_vs_ours.py` structure:

| Symbol | Role |
|---|---|
| `SUITES` (line ~390) | 10-suite canonical list matching Qwen3.5 / M3 / Opus 4.x / GPT 5.x published eval tables |
| `_arc_agi_2_pool`, `_mmlu_pro_pool`, `_gpqa_diamond_pool`, `_terminal_bench_pool`, `_swe_bench_pool`, `_swe_bench_pro_pool`, `_aime_pool`, `_livecodebench_pool`, `_aider_polyglot_pool`, `_bfcl_pool` | 10 pool functions (one per suite) |
| `pick_25_tasks` | dispatcher — now references `swe-bench` / `swe-bench-pro` keys; the stale `deep-swe` branch was removed in this session |
| `run_one_cell` | prompt-construction + LLM call + scoring — 6 prompt-suffix branches cover the 10 suites |

Note: the 10-suite dispatcher in `stock_vs_ours.py` is **prepared** but the V4
500-cell real run is **not yet executed**. Chat 6 owns the execution and the
emission of immutable artifacts under this contract.
