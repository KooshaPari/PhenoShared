# sentinel

Rate limiting, circuit breaking, and bulkhead isolation for Rust services.

## Features

- **Token Bucket**: Token bucket rate limiting
- **Leaky Bucket**: Leaky bucket algorithm
- **Circuit Breaker**: Failure threshold based
- **Bulkhead**: Isolate by partition

## Installation

```toml
[dependencies]
sentinel = { git = "https://github.com/KooshaPari/sentinel" }
```

## Usage

```rust
use sentinel::{RateLimiter, CircuitBreaker};

let limiter = RateLimiter::token_bucket(100, 10);
if limiter.try_acquire() {
    // proceed
}

let circuit = CircuitBreaker::new(5, Duration::from_secs(60));
match circuit.call(|| risky_operation()) {
    Ok(val) => println!("Success: {:?}", val),
    Err(e) => println!("Circuit open: {:?}", e),
}
```

## Architecture

```
src/
├── ratelimit/    # Token bucket, leaky bucket
├── circuit/      # Circuit breaker
└── bulkhead/    # Partition isolation
```

## License

MIT
