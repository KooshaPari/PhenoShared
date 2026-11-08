> **Pinned references (Phenotype-org)**
> - MSRV: see rust-toolchain.toml
> - cargo-deny config: see deny.toml
> - cargo-audit: rustsec/audit-check@v2 weekly
> - Branch protection: 1 reviewer required, no force-push
> - Authority: phenotype-org-governance/SUPERSEDED.md

# Metron

**Status:** maintenance

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/KooshaPari/Metron/actions/workflows/ci.yml/badge.svg)](https://github.com/KooshaPari/Metron/actions/workflows/ci.yml)
[![Rust](https://img.shields.io/badge/rust-1.75%2B-orange.svg)](https://www.rust-lang.org)

Production-grade metrics collection and observability framework for Phenotype services. Provides Prometheus-compatible metrics with zero-overhead collection, multiple exporters, built-in cardinality protection, and seamless async integration.

## Overview

**Metron** is the observability backbone for all Phenotype services, enabling comprehensive metrics collection without sacrificing performance. It implements the full Prometheus data model while adding Phenotype-specific features: zero-overhead metrics (created only when enabled), automatic cardinality guards against label explosion, multiple exporters (Prometheus, StatsD, JSON), and non-blocking async metric updates.

**Core Mission**: Make observability effortless by providing a high-performance, Prometheus-compatible metrics library that protects against common pitfalls while integrating seamlessly into Phenotype services.

## Technology Stack

- **Language**: Rust (edition 2021)
- **Prometheus**: Full data model support (counters, gauges, histograms, summaries)
- **Async Runtime**: Tokio-native async metric updates, non-blocking exporters
- **Exporters**: Prometheus text format, StatsD/Statsd, JSON, custom sinks
- **Architecture**: Hexagonal ports-and-adapters, testable domain layer
- **Safety**: Cardinality limits, label validation, overflow protection

## Key Features

- **Prometheus Compatible**: Full data model (Counter, Gauge, Histogram, Summary, Untyped)
- **Zero-Overhead Collection**: Metrics only allocated/updated when enabled
- **Multiple Exporters**: Prometheus scrape endpoint, StatsD push, JSON export, custom adapters
- **Cardinality Safety**: Automatic label cardinality limits prevent memory exhaustion
- **Async Non-blocking**: Tokio-native metric updates that never block request threads
- **Custom Labels**: Dynamic label addition with validation and automatic enforcement
- **Rich Histograms**: Configurable buckets, automatic percentile calculation
- **In-Memory Registry**: Optional in-memory aggregation for testing and debugging

## Quick Start

```bash
# Clone and explore
git clone <repo-url>
cd Metron

# Review governance and architecture
cat CLAUDE.md          # Project governance
cat AGENTS.md          # Agent operating contract

# Build
cargo build --workspace

# Run tests
cargo test --workspace

# Run benchmarks
cargo bench --workspace

# Example: collect metrics and export
cargo run --example prometheus_export
```

## Project Structure

```
Metron/
├── src/
│   ├── domain/
│   │   ├── metric.rs           # Core metric entity
│   │   ├── counter.rs          # Counter value object
│   │   ├── gauge.rs            # Gauge value object
│   │   ├── histogram.rs        # Histogram with buckets
│   │   ├── summary.rs          # Summary percentiles
│   │   └── meter.rs            # Meter port/trait
│   ├── application/
│   │   ├── registry.rs         # MetricRegistry use case
│   │   ├── exporter.rs         # MetricExporter use case
│   │   └── cardinality.rs      # Label cardinality management
│   ├── adapters/
│   │   ├── prometheus.rs       # Prometheus text exporter
│   │   ├── statsd.rs           # StatsD push exporter
│   │   ├── json.rs             # JSON export adapter
│   │   ├── in_memory.rs        # In-memory registry
│   │   └── custom.rs           # Custom sink adapters
│   ├── errors.rs               # Error types
│   └── lib.rs
├── examples/
│   ├── prometheus_export.rs    # Prometheus scrape endpoint example
│   ├── statsd_push.rs          # StatsD push example
│   └── custom_exporter.rs      # Custom adapter example
├── benches/
│   ├── metric_update_perf.rs
│   ├── cardinality_check.rs
│   └── export_performance.rs
├── docs/
│   ├── ARCHITECTURE.md         # Hexagonal design explanation
│   ├── EXPORTERS.md            # Exporter implementation guide
│   ├── CARDINALITY.md          # Cardinality management strategy
│   └── INTEGRATION.md          # Integration with Phenotype services
├── tests/
│   ├── integration/
│   │   ├── prometheus_export_test.rs
│   │   └── cardinality_limits_test.rs
│   └── fixtures/
└── Cargo.toml
```

## Hexagonal Architecture

```
Domain Layer (core business logic)
├── Metric (aggregate root)
├── Counter, Gauge, Histogram, Summary (value objects)
└── Meter trait (output port)
         ↓
Application Layer (use cases)
├── MetricRegistry (orchestrates collection)
├── MetricExporter (handles output)
└── CardinalityManager (enforces limits)
         ↓
Adapter Layer (IO)
├── PrometheusExporter (text format adapter)
├── StatsDExporter (UDP push adapter)
├── JSONExporter (JSON serialization adapter)
└── InMemoryRegistry (test adapter)
```

## Quick Integration Guide

```rust
// In your Phenotype service
use metron::{Registry, Counter, Histogram};
use std::sync::Arc;

// Create registry
let registry = Arc::new(Registry::new());

// Create metrics
let request_counter = registry.counter("http_requests_total", "Total HTTP requests");
let request_duration = registry.histogram("http_request_duration_seconds", "Request duration in seconds");

// Use in request handler
let start = std::time::Instant::now();
request_counter.inc();
// ... process request ...
request_duration.observe(start.elapsed().as_secs_f64());

// Export metrics (Prometheus scrape endpoint)
let metrics_text = registry.prometheus_text();
```

## Related Phenotype Projects

- **Tracera**: Distributed tracing and observability (integrates Metron metrics)
- **PhenoObservability**: Observability platform (primary metrics consumer)
- **phenotype-ops-mcp**: Ops MCP server (metrics export endpoints)
- **AgilePlus**: Work tracking (Metron tracks workflow execution metrics)
- **cloud**: Multi-tenant platform (Metron provides per-tenant metrics isolation)

## License

MIT OR Apache-2.0

## License

MIT — see [LICENSE](./LICENSE).
