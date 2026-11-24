# Implementation strategy

- Keep the lane declarative and fail-closed.
- Treat physical GPU indices, CUDA visibility, and runtime logical indices as
  different namespaces.
- Use one worker per GPU; forbid tensor parallelism and implicit migration.
- Use `run_perf_suite.py` for real OpenAI-compatible performance evidence.
- Keep Harbor/TBench out of this lane until explicit authorization and a route
  to the desktop endpoint exist.
- Preserve all unrelated dirty files and use Airlock after every edit batch.
