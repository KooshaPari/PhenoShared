# pheno-harness API Reference

## `bench.types`
`EnergySource` — enum: `NONE`, `M1_PMU`, `NVIDIA_SMI`, `POWERMETRICS`.
`RunSpec` — `suite`, `n`, `seed`, `model`, `judge_model`, `energy_source`.
`SuiteSpec` — `name`, `cls`, `domain`, `paper_metrics`.

## `bench.adapters`
`ModelAdapter` — protocol: `generate(messages, **kw) -> ModelResponse`, `agenerate(...)`.
`build_adapter(spec: str) -> ModelAdapter` — factory; aliases: `HttpOpenAI`, `HttpAnthropic`, `MLXModelAdapter`, `MockModel`, `HttpGemini`.

```python
adapter = build_adapter("http_openai")
resp = adapter.generate([{"role": "user", "content": "Hello"}])
```

## `bench.executor`
`RunConfig` — `spec`, `workers`, `per_task_timeout_s`, `cache_path`, `adapter_factory`.
`Executor(config).run() -> SuiteResult` — main run-loop.
`iter_task_descriptors(spec) -> list[TaskDescriptor]` — normalize tasks.

```python
result = await Executor(RunConfig(spec=RunSpec(suite="humaneval", n=10))).run()
```

## `bench.energy`
`detect_source(prefer=None) -> EnergySource` — auto-detect host energy source.
`measure(source, gpu_index=0)` — context manager yielding `EnergyTotal` (joules, peak_watts, mean_watts).

```python
with energy.measure(EnergySource.NVIDIA_SMI) as total:
    run_benchmark()
print(total.joules)
```

## `bench.seeds`
`sample(suite, seed, *, count=None, pool=None, n) -> Subset` — deterministic task sampling.
`shuffled_pool(pool, suite, seed) -> list` — deterministic shuffle.
