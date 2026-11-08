# phenotype-sentinel

Rust resilience library providing rate limiting (token bucket, leaky bucket), circuit breaking, and bulkhead isolation for services.

## Stack
- Language: Rust
- Key deps: Cargo, tokio (async), atomic operations

## Structure
- `src/`: Rust library
  - `rate_limiter.rs`: Token bucket and leaky bucket implementations
  - `circuit_breaker.rs`: Failure threshold-based circuit breaker
  - `bulkhead.rs`: Partition-based isolation

## Key Patterns
- All primitives are async-safe and thread-safe
- Configurable policies (thresholds, window sizes, partition counts)
- Fail-fast behavior: errors returned immediately when limits exceeded

## Adding New Functionality
- New resilience primitives: add modules in `src/`
- Implement the relevant trait and export from `lib.rs`
- Run `cargo test` to verify
