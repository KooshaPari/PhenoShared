# Performance Optimization Notes

## Overview
This document describes the performance benchmarking methodology and optimization strategies for the pheno-harness project.

## Benchmarking Methodology
- **Framework**: Use `pytest-benchmark` for standardizing micro-benchmarks and `criterion` (via Rust wrappers) for hot-path components.
- **Environments**: Benchmarks are run on dedicated CI runners with isolated CPU cores to minimize jitter.
- **Metrics**:
    - **Latency**: p50, p95, p99 execution times.
    - **Throughput**: Requests per second for I/O bound operations.
    - **Resource Utilization**: CPU and Memory usage during peak load.

## Profiling Tools
- **Python**: `cProfile`, `py-spy` (for low-overhead sampling), and `memray` for allocation tracking.
- **Rust**: `flamegraph` and `cargo bench` for cycle-accurate profiling.

## Optimization Strategies
1. **Caching**: Implement LRU caching for expensive, deterministic computations (e.g., schema validation).
2. **Lazy Loading**: Defer import of heavy modules (like ML kernels) until they are actually required.
3. **Parallelism**: Use `concurrent.futures` for I/O-bound tasks and `multiprocessing` for CPU-bound data transformations.
4. **Zero-Copy**: Minimize data copying between Rust and Python bindings using `PyO3` and memory views.

## Continuous Improvement
- **Regression Tracking**: Track benchmark results in `perf/bench_results.json` and alert on >5% regressions.
- **Budget**: Maintain a "Performance Budget" for cold-start times and critical path latency.
