# helix-logging

Rust structured logging helpers with correlation IDs, JSON output, and async support. Provides a consistent logging interface across Phenotype services.

## Stack
- Language: Rust
- Key deps: Cargo, tracing, serde_json
- Status: Archived (see ARCHIVED.md)

## Structure
- `src/`: Rust library
  - Correlation ID generation and propagation
  - JSON log formatter
  - Async-safe log emitters

## Key Patterns
- Correlation IDs attached to all log entries for request tracing
- JSON output suitable for structured log aggregators (Loki, ELK, Datadog)
- Zero-allocation hot path for common log operations
- Wraps the `tracing` ecosystem

## Adding New Functionality
- This repo is archived; prefer successor indicated in ARCHIVED.md
- If extending: add new log field types in `src/`
- Run `cargo test` to verify
