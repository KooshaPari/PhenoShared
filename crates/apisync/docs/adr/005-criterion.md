# ADR-005: Choice of criterion for Benchmarking

## Status

Accepted

## Context

Apisync requires reproducible, statistical benchmarking for its REST, GraphQL, and WebSocket adapters, as well as for domain-level serialization and deserialization paths. We need a benchmark harness that integrates with `cargo bench`, produces stable results across runs, and offers HTML reporting for CI artifacts.

Alternatives considered:
- **Standard `cargo bench` with `libtest`**: Built-in and zero-dependency, but it does not provide statistical analysis (warmup, outlier detection, confidence intervals) or HTML reports.
- **iai-callgrind**: Uses cachegrind/valgrind for instruction-count benchmarks, which is deterministic and excellent for micro-optimizations. However, it does not measure wall-clock time and requires a specific environment (valgrind on Linux), which complicates macOS and CI usage.
- **divan**: A newer, lightweight benchmark runner with low compile-time overhead. It is promising, but it is younger and lacks the mature ecosystem tooling (e.g., `cargo-criterion`, `bencher.dev` integration) that criterion has.
- **criterion-compare**: Not a runner, but a GitHub Action. It depends on criterion output format.

## Decision

Use **criterion 0.5** as the benchmark harness.

- Statistical rigor: automatic warmup, outlier detection, and confidence intervals.
- HTML reports generated per benchmark run, suitable for CI artifacts and local profiling.
- `cargo bench` integration via `harness = false` in `Cargo.toml` bench targets.
- Stable JSON output format enables downstream CI comparisons and trend tracking.

## Consequences

- **Positive**: Benchmarks are reproducible and comparable across commits. We can detect performance regressions in CI with `cargo-criterion` or custom scripts.
- **Positive**: HTML reports make it easy for reviewers to inspect latency distributions without running benchmarks locally.
- **Positive**: Well-documented API and broad ecosystem support lower the barrier for contributors to add new benchmark cases.
- **Negative**: Larger compile-time impact than `libtest` or `divan`. We mitigate this by keeping benchmark code in the `benches/` directory and only compiling it on explicit `cargo bench` invocations.
- **Negative**: Wall-clock benchmarks are sensitive to machine load. CI benchmarks must run on dedicated runners or use `iai-callgrind` as a secondary, deterministic metric in the future.
