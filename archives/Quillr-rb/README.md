> **Work state:** RELEASE-CANDIDATE · **Progress:** `████████░░ 80%`
> The org-shared HTTP toolkit spanning **Rust + TypeScript** — rate limiting, retries, circuit breakers, interceptors, and mocking. TypeScript client published as `@kooshapari/quillts`. Rust middleware published as `httpora-core` crate. · updated 2026-06-26

# Quillr

Multi-language HTTP toolkit for the Phenotype ecosystem. Quillr provides composable HTTP primitives — rate limiting, retries, circuit breakers, interceptors, and mocking — as first-class citizens in both **TypeScript** and **Rust**.

[![AI slop inside](https://sladge.net/badge.svg)](https://sladge.net) [![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/KooshaPari/Quillr/total)](https://github.com/KooshaPari/Quillr/releases)

## State

Progress: `[████████░░] 80%` — TypeScript client scaffold + Rust `httpora-core` middleware landed; CI green, release-candidate README polish in flight.

**What Quillr does:** Quillr is the Phenotype org's shared HTTP toolkit spanning **Rust and TypeScript** — composable rate limiting, retries, circuit breakers, interceptors, and mocking as first-class citizens. The TypeScript package (`@kooshapari/quillts`) is a type-safe HTTP client with interceptors and built-in test utilities; the Rust crate (`httpora-core`) provides Tower-compatible middleware for production services.

## Quick Try

Spin up a live environment to test the TypeScript client instantly:

[![Open in StackBlitz](https://developer.stackblitz.com/img/open_in_stackblitz.svg)](https://stackblitz.com/edit/github-kooshapari-quillr?embed=1&file=src/index.ts)

## Rust Quick Start

Add `httpora-core` to your Rust project:

```bash
cargo add httpora-core
```

Minimal usage example:

```rust
use httpora_core::{RateLimiter, RetryLayer, CircuitBreaker};
use std::time::Duration;

#[tokio::main]
async fn main() {
    let limiter = RateLimiter::token_bucket(100, 10.0);
    let retry = RetryLayer::new(3, Duration::from_millis(100));
    let cb = CircuitBreaker::new(0.5, Duration::from_secs(30));
    
    println!("Quillr Rust middleware ready!");
}
```

## Usage / Quickstart

```bash
git clone https://github.com/KooshaPari/Quillr.git && cd Quillr
npm install
npm run build && npm test

# Rust middleware crate
cd crates/httpora-core
cargo build --release && cargo test
```

Install the published TypeScript client in your app:

```bash
npm install @kooshapari/quillts
```

```typescript
import { createClient } from '@kooshapari/quillts';

const api = createClient({
  baseUrl: 'https://api.example.com',
  headers: { Authorization: 'Bearer token' },
});

const user = await api.get<User>('/users/123');
```

## Packages

| Package | Language | Description | Path |
|---------|----------|-------------|------|
| `@kooshapari/quillts` | TypeScript | Type-safe HTTP client with interceptors, retries, and mocking | `src/` |
| `httpora-core` | Rust | Tower-compatible middleware — rate limiter, retry, circuit breaker | `crates/httpora-core/` |

## TypeScript Client (`@kooshapari/quillts`)

Type-safe HTTP client for TypeScript with interceptors and retries.

### Features

- **Type-safe**: Full TypeScript inference
- **Interceptors**: Transform requests/responses
- **Retry**: Automatic retry with backoff
- **Mocking**: Built-in test utilities

### Installation

```bash
npm install @kooshapari/quillts
```

### Usage

```typescript
import { createClient } from '@kooshapari/quillts';

const api = createClient({
  baseUrl: 'https://api.example.com',
  headers: { 'Authorization': 'Bearer token' },
});

const user = await api.get<User>('/users/123');
await api.post('/users', { name: 'Alice' });
```

## Rust Crate (`httpora-core`)

Ergonomic HTTP middleware — rate limiting, retries, circuit breakers — for Tower-based services.

### Features

- **Rate Limiting**: Token bucket and fixed-window rate limiters
- **Retry Logic**: Exponential backoff with jitter
- **Circuit Breaker**: Three-state (closed/open/half-open) failure detection
- **CORS Helpers**: Cross-origin resource sharing utilities
- **Request/Response Builders**: Ergonomic HTTP message construction

### Installation

```toml
[dependencies]
httpora-core = { git = "https://github.com/KooshaPari/Quillr" }
```

### Quick Start

```rust
use httpora_core::{RateLimiter, RetryLayer, CircuitBreaker};
use std::time::Duration;

// Create a token bucket rate limiter
let limiter = RateLimiter::token_bucket(100, 10.0);

// Configure retry with exponential backoff
let retry = RetryLayer::new(3, Duration::from_millis(100));

// Create a circuit breaker
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

## License

MIT

/// @trace QUILL-001
 
