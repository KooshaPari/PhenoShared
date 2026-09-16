# DEPRECATED

**This repository is archived and no longer maintained.**

**Date:** 2026-06-20

## Reason

Profila's profiling and observability functionality has been superseded by [ObservabilityKit](https://github.com/KooshaPari/ObservabilityKit) — a multi-language SDK workspace providing OpenTelemetry-native traces, metrics, structured logging, and health probes across Rust, Python, Go, and TypeScript.

See [`MOVED_TO_OBSERVABILITYKIT.md`](./MOVED_TO_OBSERVABILITYKIT.md) for the full script mapping.

## What to Use Instead

| Capability | Replacement |
|---|---|
| System profiling & metrics | [ObservabilityKit](https://github.com/KooshaPari/ObservabilityKit) — `phenotype-metrics`, `phenotype-health-runtime`, `phenotype-observability-client` |
| Code complexity analysis | ObservabilityKit `python/performance_kit/scripts/analyze_complexity.py` |
| Continuous monitoring | ObservabilityKit `python/performance_kit/scripts/profiler.py` |
| Performance benchmarking | ObservabilityKit `python/performance_kit/scripts/benchmark.py` |
| Network/disk profiling | ObservabilityKit Rust SDKs via OTEL-compatible instrumentation |

## Status

- GitHub: **Archived** (read-only)
- Local: Kept for historical reference at `/Users/kooshapari/CodeProjects/Phenotype/repos/Profila/`
