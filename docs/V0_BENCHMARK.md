# V0 measured benchmark foundation

Day-6 introduces a strict, offline-first measured benchmark lane for the
PhenoCompose dogfood program. Artifacts separate **observations** (raw
measurements), **derived metrics** (computed from observations),
**simulations** (explicitly non-measured), and **hypotheses** (claims to test).

## Evidence classes

| Layer | Schema | `evidence_class` | Promotable as measured? |
| --- | --- | --- | --- |
| Observations | `pheno.bench.v0.observation.v1` | `local_measured` or `blocked` | Only `local_measured` |
| Derived | `pheno.bench.v0.derived.v1` | `derived` | No (requires source observations) |
| Simulations | `pheno.bench.v0.simulation.v1` | `simulated` | **Never** |
| Hypotheses | `pheno.bench.v0.hypothesis.v1` | n/a | n/a |

Missing model weights or disabled live mode produce **`blocked`** observations.
Blocked rows are persisted with a `block_reason` and **never** back-filled from
simulation output.

## GPU UUID keying

NVIDIA telemetry is keyed by canonical GPU UUID (for example
`GPU-8d337a84-43de-158d-7526-7175288a6064` from
`config/phenocompose_dogfood_v0.yaml`). Each observation's `gpu_telemetry` object
must contain exactly one entry per declared `gpu_uuids` element with fields:

- `utilization_percent`
- `memory_used_mib`
- `memory_total_mib`
- `power_watts`
- `temperature_c`

Nulls are allowed when telemetry was not collected (offline stub or blocked).

## Required provenance digests

Every artifact carries the same provenance object:

- `config_sha256`
- `model_sha256`
- `fixture_sha256`
- `environment_sha256`
- `phenocompose_run_sha256`
- `nvms_provenance_sha256`

These bind PhenoCompose persisted-run state and NanoVMS action provenance to
benchmark rows without embedding host paths or secrets.

## PhenoCompose / NVMS binding

1. PhenoCompose `plan` / `apply` / `run-action` produces a persisted run whose
   content hash becomes `phenocompose_run_sha256`.
2. NanoVMS `action --request -` returns provider, GPU reservation, and cleanup
   evidence whose digest becomes `nvms_provenance_sha256`.
3. The declared GPU UUID in the composition manifest must match observation
   telemetry keys and NVMS reservation records.

See `docs/PHENOCOMPOSE_DOGFOOD.md` for the delegated boundary sequence.

## First slice (Day-6 gate)

`bench/v0/plugin.py` registers five cases:

| Case | Offline behavior | Live (`PHENO_V0_LIVE=1`) + model assets |
| --- | --- | --- |
| `transport_baseline` | Measured stub (pass) | Same stub |
| `qwen_08b_warm_gh` | Blocked | Streaming warm generation via `perf.streaming` |
| `qwen_08b_cold_gh` | Blocked | Streaming cold generation |
| `concurrency_sweep` | Blocked | Placeholder sweep via `perf.sweep` |
| `prefix_affinity_ab` | Blocked | Placeholder A/B via `perf.heterogeneous` |

Model assets are detected from `PHENO_V0_MODEL_PATH` (directory containing
`config.json` or tokenizer files). Live OpenAI-compatible endpoint defaults to
`http://127.0.0.1:8080` and can be overridden with `PHENO_V0_API_BASE`.

Provider interfaces in `bench/v0/providers/` wrap existing `perf/` modules so
benchmark code does not fork streaming, sweep, heterogeneous, or resource
sampling logic.

## Schemas and validation

JSON Schema drafts live under `bench/v0/schema/`. Python validators in
`bench/v0/contracts.py` enforce content-addressed IDs and reject unknown fields.
Run focused tests:

```powershell
python -m pytest tests/test_v0_benchmark.py -q --basetemp=.pytest_cache
```

A schema-valid reference artifact is checked in at
`bench/v0/fixtures/first_slice_day6.json`.

## Running the slice

```powershell
python -c "import json; from bench.v0.plugin import run_v0_first_slice; print(json.dumps(run_v0_first_slice(), indent=2))"
```

Opt-in live measurements:

```powershell
$env:PHENO_V0_LIVE = "1"
$env:PHENO_V0_MODEL_PATH = "C:\path\to\qwen35-08b"
$env:PHENO_V0_API_BASE = "http://127.0.0.1:8080/v1"
python -c "import json; from bench.v0.plugin import run_v0_first_slice; print(json.dumps(run_v0_first_slice(), indent=2))"
```

No Docker invocation is required for the Day-6 gate; offline blocked slices are
valid gate output when GPU/model assets are unavailable.
