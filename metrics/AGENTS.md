# AGENTS.md — metrics

## Project Overview

- **Name**: metrics (Metrics Collection & Analytics Platform)
- **Description**: High-performance metrics collection and analytics platform with real-time aggregation and visualization
- **Location**: `/Users/<REDACTED>/CodeProjects/Phenotype/repos/metrics`
- **Language Stack**: Rust (Edition 2024), ClickHouse, Grafana
- **Published**: Private (Phenotype org)

## Quick Start Commands

```bash
# Clone and setup
git clone https://github.com/KooshaPari/metrics.git
cd metrics

# Install Rust toolchain
rustup update nightly
rustup default nightly

# Build
cargo build --release

# Run tests
cargo test
cargo nextest run

# Start server
cargo run --bin metrics -- server
```

## Architecture

### Metrics Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Ingestion Layer                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│  │   Application     │  │   System          │  │   Custom          │         │
│  │   (StatsD)        │  │   (Prometheus)    │  │   (OTLP)          │         │
│  │   (HTTP)          │  │                   │  │                   │         │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘         │
└───────────┼────────────────────┼────────────────────┼────────────────┘
            │                    │                    │
            ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      metrics Core (Rust)                                 │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Metrics Engine                                │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐            │   │
│  │  │   Parser     │  │   Router     │  │   Enrich     │            │   │
│  │  │   (Decode)   │  │   (Route)    │  │   (Add Meta) │            │   │
│  │  └────────────┘  └────────────┘  └────────────┘            │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐            │   │
│  │  │   Aggregate  │  │   Sample     │  │   Compress   │            │   │
│  │  │   (Rollups)  │  │   (Reduce)   │  │   (Encode)   │            │   │
│  │  └────────────┘  └────────────┘  └────────────┘            │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Storage Layer                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│  │   ClickHouse      │  │   Redis           │  │   Parquet         │         │
│  │   (Hot)           │  │   (Cache)           │  │   (Cold)          │         │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘         │
└─────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Query & Visualization Layer                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│  │   SQL API         │  │   Grafana         │  │   Alerts          │         │
│  │   (REST)          │  │   (Dashboards)    │  │   (Thresholds)    │         │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘         │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Metrics Data Flow                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Raw ──▶ Parse ──▶ Enrich ──▶ Aggregate ──▶ Store ──▶ Query        │
│                                                                      │
│  100K/s   Decode   Add tags   1min/5min     Hot     SQL/Grafana     │
│  metrics  JSON     service    rollups       7d      queries          │
│           Protobuf host       counters      Cold                   │
│                               gauges        1y                     │
│                               histograms                           │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Quality Standards

### Rust Code Quality

- **Formatter**: `rustfmt` (nightly)
- **Linter**: `clippy -- -D warnings`
- **Tests**: `cargo nextest run` with coverage >80%

### Performance Standards

- 1M+ metrics/second ingestion
- Sub-100ms query latency
- 99.99% uptime target
- Automatic retention policies

### Test Requirements

```bash
# Unit tests
cargo test

# Load tests
cargo test --test load

# Integration tests
cargo test --test integration
```

## Git Workflow

### Branch Naming

Format: `<type>/<component>/<description>`

Types: `feat`, `fix`, `docs`, `refactor`, `perf`

Examples:
- `feat/ingestion/add-otlp-support`
- `perf/query/optimize-clickhouse`
- `fix/storage/handle-backpressure`

## CLI Commands

```bash
# Start server
cargo run --bin metrics -- server

# Query metrics
cargo run --bin metrics -- query 'SELECT * FROM metrics WHERE time > now() - 1h'

# List sources
cargo run --bin metrics -- sources list

# Check health
cargo run --bin metrics -- health
```

## Environment Variables

```bash
# Server
METRICS_PORT=8080
METRICS_INGESTION_PORT=8125

# ClickHouse
CLICKHOUSE_URL=http://localhost:8123
CLICKHOUSE_DATABASE=metrics

# Retention
HOT_RETENTION_DAYS=7
COLD_RETENTION_DAYS=365
```

---

Last Updated: 2026-04-05
Version: 1.0.0
