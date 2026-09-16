# V5 Cell Pass Metrics (contract v0.2)

> Status: **PR1** — honest generation vs verified pass separation
> Scope: per-cell fields in `stock_vs_ours.py` output and `task_results[]`
> `additionalProperties` after `convert_to_contract.py`

## Problem

`pass_at_1` was used as a 0/1 generation-success flag (`result["ok"]`). That is
not verified pass@1. Consumers must not treat suite-level `pass_at_1` as Harbor
or verifier proof.

## Cell fields (v0.2)

| Field | Type | Meaning |
|-------|------|---------|
| `gen_ok` | `0.0 \| 1.0` | Generation succeeded (model returned output) |
| `pass_at_1` | `0.0 \| 1.0` | **Deprecated alias** of `gen_ok` for one release |
| `verified_pass_at_1` | `0.0–1.0` | Harbor reward or verifier score; `0.0` when absent |
| `evidence_label` | enum | `"reported"` when only `gen_ok`; `"verified"` when Harbor reward present |

Producers dual-write `pass_at_1 = gen_ok` with an inline comment that it is not
verified pass@1. PR2 will stop relying on `pass_at_1` at the cell layer.

## Producer rules

1. MLX ablation / direct-generate path: `verified_pass_at_1 = 0.0`,
   `evidence_label = "reported"`.
2. Harbor reward path: set `verified_pass_at_1` from the reward,
   `evidence_label = "verified"`.
3. Always emit `gen_ok` and the `pass_at_1` alias together.

## Consumer rules (`verify_contract.py`, `convert_to_contract.py`)

1. Prefer `gen_ok` when present on cells or in `additionalProperties`.
2. For `evidence_label == "reported"`, treat legacy `pass_at_1` as `gen_ok` when
   `gen_ok` is missing (backward compatibility).
3. Do not require `verified_pass_at_1 > 0` for reported-evidence artifacts.
4. Suite aggregation: `gen_ok_mean = round(sum(gen_ok) / n, 4)` when cells carry
   `gen_ok`; `pass_at_1` at suite level may still reflect `passed / n` for v0.1
   EvaluationReport compatibility.

## Helper

`bench/contracts/cell_metrics.py` exports `cell_pass_fields()` for producers and
`task_gen_ok()` / `suite_gen_ok_mean()` / `effective_pass_at_1()` for consumers.
