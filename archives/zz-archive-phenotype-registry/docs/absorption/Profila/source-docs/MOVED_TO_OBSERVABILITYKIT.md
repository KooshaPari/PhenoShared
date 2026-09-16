# Moved to ObservabilityKit

**2026-06-20** — Profila's profiling and observability functionality has been superseded by [ObservabilityKit](https://github.com/KooshaPari/ObservabilityKit).

## Script Mapping

Profila provided a set of Bash and Python scripts for system profiling, code analysis, and performance monitoring. These capabilities are now available in ObservabilityKit's multi-language SDK workspace:

| Profila Script | ObservabilityKit Equivalent | Notes |
|---|---|---|
| `profiler.sh` (root launcher) | `python/performance_kit/scripts/profiler.py` | Unified profiler; ObservabilityKit's covers app-level profiling (startup, memory, imports, tool execution) |
| `bin/profiler.sh` (system profiling) | `rust/phenotype-health-runtime/` | System-level health/runtime probes in Rust |
| `bin/all_metrics.sh` | `python/performance_kit/scripts/profiler.py` + `rust/phenotype-metrics/` | Metrics collection (memory, CPU, files, network, disk) |
| `bin/system_metrics.py` | `python/performance_kit/scripts/profiler.py` | psutil-based metrics collection |
| `bin/full_system_audit.sh` | `rust/phenotype-health-runtime/` | Comprehensive system audit / health probes |
| `bin/disk_profiler.sh` | `rust/phenotype-observability-client/` (disk I/O via OTEL) | Disk I/O profiling |
| `bin/network_profiler.sh` | `rust/phenotype-observability-client/` (network metrics via OTEL) | Network profiling |
| `bin/complexity_analyzer.py` | `python/performance_kit/scripts/analyze_complexity.py` | Code complexity analysis (Ast-based → Radon-based) |
| `bin/generate_charts.py` | `python/performance_kit/scripts/benchmark.py` (chart section) | Chart generation from profile data |
| `bin/continuous_profiler.py` | `python/performance_kit/scripts/profiler.py` + `scripts/duration_tracker.py` | Continuous monitoring and duration tracking |
| `bin/profiler_setup.sh` | `Taskfile.yml` + `Cargo.toml` (declarative deps) | Profiling tool installation |
| `bin/build_for_profiling.sh` | `Taskfile.yml` (build tasks) | Build with profiling symbols |

## ObservabilityKit Advantages

- **Multi-language SDKs**: Rust, Python, Go, TypeScript (Profila was Bash + Python)
- **OpenTelemetry-native**: OTLP-compatible traces, metrics, logs (Profila was `/proc`/`ps`/`lsof` filesystem scraping)
- **Structured logging**: `tracing`-based with correlation IDs and redaction
- **Distributed tracing**: Parent/child span linking across service boundaries
- **Kubernetes probes**: `/healthz` and `/readyz` endpoints via `phenotype-health-runtime`
- **Cardinality controls**: Protect Prometheus from high-cardinality dimensions
- **Cross-language parity**: Same conceptual surface across all supported languages

## Archive

Profila repository is archived at [KooshaPari/Profila](https://github.com/KooshaPari/Profila). For new observability work, use [ObservabilityKit](https://github.com/KooshaPari/ObservabilityKit).
