# Performance Suite Contract

Status: implemented baseline; real-engine validation remains pending local weights.

Use `scripts/run_perf_suite.py` against an already-running local OpenAI-compatible
endpoint. `--synthetic` validates scheduling and reporting without a model call.
`--no-gpu-sampling` isolates request timing from `nvidia-smi` overhead.

Measurement semantics:

- TTFT is request submission to the first nonempty streamed content chunk.
- ITL is the interval between nonempty SSE chunks, explicitly a chunk proxy.
- Server usage is preferred for token counts; fallback counts are approximate.
- Concurrency is actual simultaneous in-flight requests.
- Failed requests remain in results; warmups are reported and excluded.
- `probe_overhead_ms` reports synchronous resource-sampler cost separately.

Each JSON report contains reproducible endpoint/model metadata, warmups,
per-level p50/p95 latency, aggregate throughput, individual failures, resource
summaries, and measurement caveats. Cloud routes remain disabled by policy.
