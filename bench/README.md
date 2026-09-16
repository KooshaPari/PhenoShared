"""Bench — benchmark-harness skeleton for pheno-harness.

This package provides the *skeleton* layer for the 10-suite benchmark harness
specified in `docs/superpowers/specs/2026-07-16-benchmark-harness.md`. The
suites agent fills in concrete suite implementations, and the runner agent
fills in concrete matrix execution logic. Both consume this skeleton.

## Architecture

```
bench/
├── __init__.py       # version
├── __main__.py       # `python -m bench` entry point
├── cli.py            # Argparse CLI + --self-test
├── types.py          # RunSpec/SuiteSpec/TaskResult/SuiteResult/RunReport
├── spec.py           # parse the spec markdown into machine-readable facts
├── metric.py         # Metric dataclass + SPEC_Q4_METRICS + percentile/ci helpers
├── trajectory.py     # ATIF v1.7 + CTRF readers → unified RunRecord
├── registry.py       # @suite/@task/@metric + __init_subclass__ auto-discovery
└── README.md         # (this file)
```

Modules depend on each other in one direction: `cli` → `registry`, `spec`,
`metric`, `trajectory`, `types`. `registry` depends on `metric` and `types`.
`trajectory` and `metric` are leaves.

### Type system

* `RunSpec` — frozen, immutable description of one benchmark invocation.
* `SuiteSpec` — static definition of a registered suite (subset, source URL).
* `TaskResult` — outcome of one task.
* `SuiteResult` — full per-(suite, model) result, JSON-roundtrippable.
* `RunReport` — top-level cross-suite report.

### Registries

* `Suite` subclasses auto-register via `__init_subclass__`.
* `@task(...)` and `@metric(...)` are decorators that register handlers.
* `reset_registry()`, `reset_task_registry()`, and `reset_metric_registry()`
  exist for tests.

### Trajectory handling

`bench.trajectory` reads either ATIF v1.7 (IBM Agent Trajectory Interchange
Format) or CTRF (Common Test Report Format) JSON, normalizes them to a single
`RunRecord` dataclass, and supports streaming via JSONL.

### Metric catalog

`SPEC_Q4_METRICS` lists every metric from spec §4. The framework supports
`Metric` instances that include name, value, source, units, higher-is-better,
and sample-size — all round-trippable through `MetricSet.coerce(...)`.

## How to add a new suite

1. Create a new module under `bench/suites/<suite_name>.py`.
2. Subclass `bench.registry.Suite`, set class attributes (`name`, `source_url`,
   `format`, `subset`, `rationale`, `default_judge_mode`).
3. Implement `run(self, run_spec: bench.types.RunSpec) -> bench.types.SuiteResult`.
4. Import the module somewhere on the import path (e.g., `bench/suites/__init__.py`).
   The subclass auto-registers on import.

```python
# bench/suites/ifeval.py
from bench.registry import Suite
from bench.types import RunSpec, SuiteResult

class IfEval(Suite):
    name = "ifeval"
    source_url = "github.com/google-research/google-research/tree/master/instruction_following"
    format = "deterministic verifier"
    subset = "n=100 of ~500"
    rationale = "format stability, no judge"
    default_judge_mode = "deterministic"

    def run(self, run_spec: RunSpec) -> SuiteResult:
        ...
```

## How to add a new metric

There are two patterns:

**Pattern A — collected at suite time**:

```python
from bench.metric import Metric

metrics.append(Metric(
    name="tool_call_success_rate",
    value=0.97,
    source="pheno.eval.agent_loop",
    units="ratio",
    higher_is_better=True,
    sample_size=n,
))
```

**Pattern B — registered globally**:

```python
from bench.registry import metric

@metric(name="local_tokens_per_sec", units="tok/s", source="pheno.eval.perplexity")
def tokens_per_sec() -> float:
    return compute_tps()
```

Use `MetricSet.coerce(...)` if you have a raw dict (e.g., from JSON) and want
type-safe coercion.
