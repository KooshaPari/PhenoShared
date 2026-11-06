---
title: Getting Started
---

# Getting Started

Quillr ships HTTP primitives as two language-specific packages. Pick the one that matches your stack.

## TypeScript — `@kooshapari/quillts`

A type-safe HTTP client with interceptors, retries, and built-in mocking utilities.

### Features

- **Type-safe** — full TypeScript inference for requests and responses.
- **Interceptors** — transform requests and responses in a composable pipeline.
- **Retry** — automatic retry with backoff.
- **Mocking** — built-in test utilities for HTTP testing.

### Installation

```bash
npm install @kooshapari/quillts
```

### Usage

```typescript
import { createClient } from '@kooshapari/quillts';

const api = createClient({
  baseUrl: 'https://api.example.com',
  headers: { Authorization: 'Bearer token' },
});

const user = await api.get<User>('/users/123');
await api.post('/users', { name: 'Alice' });
```

## Rust — `httpora-core`

Ergonomic HTTP middleware — rate limiting, retries, circuit breakers, and CORS — for Tower-based services.

### Features

- **Rate Limiting** — token bucket and fixed-window rate limiters.
- **Retry Logic** — exponential backoff with jitter.
- **Circuit Breaker** — three-state (closed / open / half-open) failure detection.
- **CORS Helpers** — cross-origin resource sharing utilities.
- **Request / Response Builders** — ergonomic HTTP message construction.

### Installation

```toml
[dependencies]
httpora-core = { git = "https://github.com/KooshaPari/Quillr" }
```

### Quick start

```rust
use httpora_core::{RateLimiter, RetryLayer, CircuitBreaker};
use std::time::Duration;

// Token bucket rate limiter
let limiter = RateLimiter::token_bucket(100, 10.0);

// Retry with exponential backoff
let retry = RetryLayer::new(3, Duration::from_millis(100));

// Circuit breaker
let cb = CircuitBreaker::new(0.5, Duration::from_secs(30));
```

## Development

### TypeScript

```bash
# Build
npm run build

# Test
npm test

# Lint
npm run lint
```

### Rust

```bash
# Build
cargo build -p httpora-core

# Test
cargo test -p httpora-core

# Lint
cargo clippy -p httpora-core -- -D warnings
```

## Next steps

- Browse the source: [`src/`](https://github.com/KooshaPari/Quillr/tree/main/src) and [`crates/httpora-core/`](https://github.com/KooshaPari/Quillr/tree/main/crates/httpora-core).
- Open an issue or pull request on [GitHub](https://github.com/KooshaPari/Quillr).
