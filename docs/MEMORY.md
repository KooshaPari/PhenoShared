# Memory Profiling and Management

## Overview
Efficient memory usage is critical for long-running evaluation harnesses and large-scale data processing. This document outlines the tools and approaches used to monitor and optimize memory performance in pheno-harness.

## Profiling Tools
- **Python `tracemalloc`**: Integrated into the core evaluation loop to track memory allocations by source line. Snapshots are taken at regular intervals to identify growth patterns.
- **Memory Profiler**: Used for line-by-line profiling of hot paths to identify memory-intensive operations.
- **Docker/Container Metrics**: Monitoring RSS and heap usage in containerized environments via cgroups.

## Tracemalloc Integration
- **Snapshotting**: Automatic snapshots are generated every 100 evaluations to capture the delta in memory usage.
- **Comparison**: `tracemalloc.compare()` is used to highlight the top memory consumers between snapshots.
- **Analysis**: The `TracebackFilter` is configured to exclude standard library calls and focus on project-specific code (`pheno`, `bench`, `verifier`).

## Optimization Strategies
1. **Streaming Processing**: Use generators and iterators to process large datasets (like `datasets/`) without loading them entirely into memory.
2. **Object Pooling**: Reuse expensive objects (e.g., database connections, large model weights) via a centralized pool.
3. **Memory-Mapped Files**: For very large state files, utilize `mmap` to provide efficient random access without full loading.
4. **Garbage Collection Tuning**: Explicitly trigger `gc.collect()` after large batch operations to reclaim memory promptly.

## Monitoring and Alerts
- **Thresholds**: Set memory usage alerts at 70% and 90% of container limits.
- **Leak Detection**: Periodic "memory leak" tests are run in CI to ensure long-running processes maintain stable memory profiles.
