# Product Requirements Document — helix-logging

## Overview

`helix-logging` is a Rust structured logging library for the Phenotype/Helix ecosystem. It provides unified structured logging with correlation IDs, JSON output, async support, and multiple output backends. It replaces the deprecated `phenotype-logger` crate and is the canonical logging solution for all Rust services in the Helix ecosystem.

## Problem Statement

Rust services in the Helix ecosystem previously used `phenotype-logger`, which lacked structured JSON output, correlation ID propagation, and async-friendly logging. `helix-logging` provides these capabilities in a single, well-tested library.

## Goals

- Structured JSON log output for machine consumption.
- Human-readable console output for development.
- Correlation ID propagation via thread-local or async context storage.
- Multiple log levels: Trace, Debug, Info, Warn, Error.
- Async-safe logging (no blocking I/O in hot paths).
- Compatible with the `log` crate facade for ecosystem interop.
- Publish to crates.io (or GitHub Packages for private use).

## Non-Goals

- Not a distributed tracing library (that is `helix-tracing`).
- Does not manage log rotation or archival.
- Does not provide UI or dashboards.

## Epics & User Stories

### E1 — Initialisation
- E1.1: `Logger::init(config: LoggerConfig)` initialises global logging for a service.
- E1.2: `LoggerConfig` specifies minimum level, output format (JSON/text), and include_timestamps flag.

### E2 — Correlation IDs
- E2.1: `Logger::with_correlation_id(id: &str, f: impl FnOnce())` runs `f` with the correlation ID in scope.
- E2.2: All log messages emitted inside the scope include the `correlation_id` field.

### E3 — Structured Fields
- E3.1: Log macros accept optional key-value pairs: `info\!("msg", key = "value", count = 42)`.
- E3.2: JSON output includes all key-value pairs as top-level fields alongside `level`, `timestamp`, `message`.

### E4 — Output Backends
- E4.1: Console backend (stdout/stderr) for development.
- E4.2: JSON backend for production/log aggregators.

### E5 — Compatibility
- E5.1: `helix-logging` implements `log::Log` so any code using `log::info\!()` etc. is captured.

### E6 — Testing
- E6.1: `cargo test` passes with zero failures.
- E6.2: Tests verify JSON output contains expected fields.

## Acceptance Criteria

- `cargo build` and `cargo test` succeed.
- `cargo clippy -- -D warnings` exits 0.
- JSON output format is documented.
