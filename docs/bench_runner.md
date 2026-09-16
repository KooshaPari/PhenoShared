# bench/runner — Execution engine for pheno-harness

This document describes the runner layer that orchestrates the
skeleton (suites + metrics) against model adapters, collects
measurements, and aggregates them into a `RunReport`.

## Layout

Primary modules live flat under `bench/` (cache, executor, energy, …).
`bench/runner/` is a **back-compat package path** used by tests and older docs:
most modules re-export from `bench.*`; `model_adapter` and `executor` keep the
`complete()`-era APIs for the runner test suite.

```
bench/
├── cli.py                 CLI: `python -m bench` / `bench`
├── adapters.py            generate()-era adapters (MockModel, Http*, MLX)
├── types.py               RunSpec / SuiteResult / RunReport / EnergySource
├── runner/                back-compat + complete()-era model_adapter/executor
│   ├── model_adapter.py
│   └── executor.py
├── cache.py, energy.py, perf.py, …
└── suites/                suite implementations
```

## CLI quick-start

```bash
# 3-task deterministic smoke run against the in-process stub model
python -m bench.run --suite deep-swe --n 3 --seed 42 \
    --model mlx-stub --output /tmp/bench-smoke --no-judge

# End-to-end run; requires API keys in env
ANTHROPIC_API_KEY=sk-... python -m bench.run --suite deep-swe \
    --n 50 --seed 7 --model claude-sonnet-5-20250514 \
    --judge-model claude-opus-5 --workers 8 \
    --output runs/2026-07-16 --stability-metric
```

The script-mode shortcut is registered in `pyproject.toml`:

```bash
bench-run --help
```

## RunReport schema (top-level)

```jsonc
{
  "schema": "bench.runner.RunReport/0.1",
  "created_at": "2026-07-16T10:13:42Z",
  "model": "claude-sonnet-5-20250514",
  "judge_model": "claude-opus-5",
  "totals": {
    "tasks": 50,
    "passed": 31,
    "failed": 19,
    "wall_clock_s": 412.83,
    "joules": 9821.4,
    "joules_per_passed_task": 316.8,
    "tokens_in": 1442211,
    "tokens_out": 902118,
    "pass_rate": 0.62
  },
  "suites": [
    {
      "name": "deep-swe",
      "n": 50,
      "tasks": [
        {
          "task_id": "deep-swe-0001",
          "status": "PASS",
          "score": 1.0,
          "judge_verdict": "pass",
          "judge_reason": "All acceptance criteria met.",
          "wall_clock_s": 8.42,
          "tokens_in": 18421,
          "tokens_out": 2110,
          "tokens_per_s": 250.6,
          "joules": 192.1,
          "peak_rss_mb": 312.8,
          "intent_drift": 0.024
        }
      ]
    }
  ]
}
```

`report.md` renders the totals as a single summary block plus a
per-suite pass-rate table; for multi-suite runs, the table rows
index by `suite` and columns list each Q4 metric.

## Adding a new model adapter

1. Subclass `bench.runner.model_adapter.ModelAdapter`.
2. Implement `name`, `complete(prompt, *, temperature, max_tokens) ->
   Completion`, and (optionally) `stream(prompt, *, temperature,
   max_tokens) -> Iterator[str]`.
3. Register your adapter string prefix in `_DISPATCH` inside
   `model_adapter.py`:

```python
_DISPATCH = {
    "claude":       lambda s: AnthropicAdapter(model_id=s, ...),
    "gpt-":         lambda s: OpenAIAdapter(model_id=s, ...),
    "http":         lambda s: VLLMAdapter(base_url=s, ...),
    "mlx":          _resolve_mlx,        # MLX (real) or stub
    "my-factory":   lambda s: MyAdapter(...),    # <-- add here
}
```

4. Add a unit test under
   `tests/test_bench_runner.py::TestBuildAdapter` that asserts
   `--model my-factory-xyz` routes to your adapter.
5. Run `pytest tests/test_bench_runner.py -v` — every test must pass
   with no real network calls.

### Adapter contract

```python
class ModelAdapter(Protocol):
    name: str

    def complete(
        self,
        prompt: str,
        *,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> Completion: ...

    def stream(
        self,
        prompt: str,
        *,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> Iterator[str]: ...
```

`Completion` carries `text`, `prompt_tokens`, `completion_tokens`,
`finish_reason`, `model_id`, and `raw` (vendor SDK response, optional).
Adapters may raise `bench.runner.model_adapter.ModelAdapterError`;
the executor wraps each invocation with a per-task timeout.

## Cache behaviour

- Key: `(suite, task_id, model, prompt_hash, temperature)` where
  `prompt_hash = sha1(prompt).hexdigest()[:16]`.
- Storage: SQLite at `$XDG_CACHE_HOME/bench/cache.sqlite` (overridable
  via `--cache /path/to/cache.sqlite`). Default TTL is 7 days.
- Bypass with `--no-cache`.
- Cache hits short-circuit `complete()` and reuse the prior
  `Completion`, including prompt/completion token counts.

## Stability metrics

`--stability-metric` runs `bench.runner.stability.compute_semantic_drift`
after task execution. It embeds the user-intent string for each turn
(via `sentence-transformers/all-MiniLM-L6-v2` when available, else the
deterministic `hash_embed` fallback) and reports:

- `intent_drift` — 1 − mean pairwise cosine over all turns.
- `dead_ends` — number of repeated identical turns.
- `mean_repeat_cosine` — average cosine similarity between adjacent
  intent embeddings.

If `sentence-transformers` is not installed, a deterministic,
hash-based embedder is used (no model download required); results are
flagged `approx=true` on the produced metric.

## Environment variables

| Var | Purpose |
| --- | --- |
| `ANTHROPIC_API_KEY` | API key for `AnthropicAdapter`. |
| `OPENAI_API_KEY`    | API key for `OpenAIAdapter`.   |
| `BENCH_DISABLE_METAL_PROBE=1` | Skip `import torch` (Metal probe) — useful in CI where torch is broken. |
| `XDG_CACHE_HOME` | Cache DB location (`$XDG_CACHE_HOME/bench/cache.sqlite`). |
| `PYTHONHASHSEED` | If set, overrides `random.Random` seed for sub-sampling (NOT recommended — keep `--seed`). |

## Running the test suite

```bash
# Minimal: 73 tests pass in ~15-30s
BENCH_DISABLE_METAL_PROBE=1 pytest tests/test_bench_runner.py -v

# If your environment has heavy pytest plugins auto-loaded
# (e.g., schemathesis, xdist, respx, langsmith, tach) and they
# cause `pytest --collect-only` to hang for >30s, disable them:
pytest tests/test_bench_runner.py -v \
    -p no:schemathesis -p no:respx -p no:langsmith \
    -p no:tach -p no:xdist
```

The second invocation is what the `scripts/run_bench_smoke.sh`
script uses, since the host machine has the full `phenotype-org`
plugin set installed globally.

## Limitations & non-goals

- No streaming judge (judge runs synchronously in `judge_runner.py`).
- `--per-task-timeout` defaults to 600s. Long-running DeepSWE
  tasks may need `--per-task-timeout 1800`.
- Energy on linux without `nvidia-smi` returns 0 joules (no Intel RAPL
  probe yet).
- vLLM adapter speaks the OpenAI HTTP schema; it does not yet respect
  `tool_choice` or `response_format`.
