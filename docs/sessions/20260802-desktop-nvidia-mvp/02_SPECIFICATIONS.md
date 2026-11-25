# Specifications

## Acceptance criteria

1. Exact Qwen3.5 model revision, quantized artifact, and SHA-256 are recorded.
2. Physical GPU indices and runtime-visible mappings are recorded separately.
3. Each live run includes timestamps, workload, dry-run state, timeout, and
   concurrency metadata.
4. Repeated helper and primary responses are deterministic with no fallback.
5. A real harness evaluation writes a `pheno.perf.v1` result.
6. Promotion remains blocked until every declared gate is true.
7. macOS inference and unrelated user processes remain untouched.
