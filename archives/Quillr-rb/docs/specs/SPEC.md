# Quillr Specification

> Multi-language HTTP toolkit — TypeScript client (`@kooshapari/quillts`) and Rust middleware (`httpora-core`)

**Version**: 0.1.0 | **Status**: Draft | **Last Updated**: 2026-06-24

## Overview

Quillr provides composable HTTP primitives — rate limiting, retries, circuit breakers, interceptors, and mocking — as first-class citizens in both TypeScript and Rust.

| Package | Language | Path |
|---------|----------|------|
| `@kooshapari/quillts` | TypeScript | `src/` |
| `httpora-core` | Rust | `crates/httpora-core/` |

---

## Functional Requirements

### TypeScript Client (`@kooshapari/quillts`)

#### FR-1: Client Creation

The library MUST export a `createClient` factory that accepts a `ClientConfig` object with `baseUrl`, `headers`, and `timeout` options and returns a `QuillClient` instance.

- **Acceptance Criterion**: `createClient({ baseUrl: 'https://api.example.com', headers: { Authorization: 'Bearer x' }, timeout: 5000 })` returns an object with typed `get`, `post`, `put`, `delete` methods.
- **Traceability**: `src/index.ts` (export); `src/client.ts` (`createClient`, `QuillClient`)

#### FR-2: Typed HTTP Methods

The client MUST support `get<T>`, `post<T>`, `put<T>`, and `delete<T>` methods that accept a path string and an optional generic type parameter for the response body.

- **Acceptance Criterion**: `api.get<User>('/users/123')` infers the return type as `Promise<User>`.
- **Traceability**: `src/client.ts` (`QuillClient.get`, `.post`, `.put`, `.delete`)

#### FR-3: Request Interceptors

The client MUST support a chain of request interceptors that can modify headers, body, or URL before a request is dispatched.

- **Acceptance Criterion**: An interceptor that adds an `Authorization` header is invoked before every request and the header appears in the outgoing request.
- **Traceability**: `src/interceptors/` (request interceptor module)

#### FR-4: Response Interceptors

The client MUST support a chain of response interceptors that can transform or validate the server response before it reaches the caller.

- **Acceptance Criterion**: A response interceptor that parses a custom header is invoked after every successful response and the parsed value is available on the result.
- **Traceability**: `src/interceptors/` (response interceptor module)

#### FR-5: Error Interceptors

The client MUST support error interceptors that catch network errors and HTTP error statuses before they propagate to the caller.

- **Acceptance Criterion**: An error interceptor that logs 5xx errors is invoked when the server returns a 500-range status.
- **Traceability**: `src/interceptors/` (error interceptor module)

#### FR-6: Retry with Backoff

The client MUST automatically retry failed requests (network errors, 5xx) with configurable retry count and exponential backoff.

- **Acceptance Criterion**: A request that fails 3 times with a network error is retried up to the configured max retries; the fourth attempt's result is returned.
- **Traceability**: `src/retry/` (retry module); `src/client.ts` (retry integration)

#### FR-7: Mock Utilities

The library MUST export mock utilities that allow tests to simulate HTTP responses without a live server.

- **Acceptance Criterion**: `mockResponse({ status: 200, body: { ok: true } })` causes the next `api.get('/test')` to resolve with the provided body without making a network call.
- **Traceability**: `src/mock/` (mocking module)

---

### Rust Crate (`httpora-core`)

#### FR-8: Token Bucket Rate Limiter

`RateLimiter::token_bucket(capacity, refill_per_sec)` MUST create a token-bucket rate limiter that allows bursts up to `capacity` and refills at `refill_per_sec` tokens per second.

- **Acceptance Criterion**: Calling `check(1.0)` on a full bucket of capacity 10 succeeds 10 times; the 11th call returns `HttptoraError::RateLimited`.
- **Traceability**: `crates/httpora-core/src/middleware/rate_limit.rs:153` (`RateLimiter::token_bucket`)

#### FR-9: Fixed Window Rate Limiter

`RateLimiter::fixed_window(limit, window_seconds)` MUST create a fixed-window rate limiter that allows `limit` requests per `window_seconds` window.

- **Acceptance Criterion**: A limiter with limit 5 and window 1.0 allows 5 `check()` calls; the 6th returns `HttptoraError::RateLimited` until the window resets.
- **Traceability**: `crates/httpora-core/src/middleware/rate_limit.rs:173` (`RateLimiter::fixed_window`)

#### FR-10: Circuit Breaker

`CircuitBreaker` MUST implement a three-state (Closed / Open / Half-Open) failure detection pattern.

- **Acceptance Criterion**: After the failure rate exceeds the configured threshold, `before_request()` returns `Err(HttptoraError::CircuitOpen)`. After the reset timeout, a probe request is allowed (Half-Open). A successful probe transitions to Closed; a failed probe reopens.
- **Traceability**: `crates/httpora-core/src/middleware/circuit_breaker.rs:57` (`CircuitBreaker`)

#### FR-11: Retry Layer (Async)

`RetryLayer::execute(f)` MUST retry an async operation up to `max_attempts` times using exponential backoff with jitter.

- **Acceptance Criterion**: An operation that fails twice succeeds on the third attempt; the result is returned without error.
- **Traceability**: `crates/httpora-core/src/middleware/retry.rs:84` (`RetryLayer`), `:124` (`execute`)

#### FR-12: Retry Method Awareness

`RetryLayer::execute_for_method(method, f)` MUST only retry idempotent HTTP methods (GET, HEAD, PUT, DELETE, OPTIONS, TRACE) by default, unless `retry_non_idempotent` is set.

- **Acceptance Criterion**: `execute_for_method(HttpMethod::Post, f)` with `retry_non_idempotent: false` does NOT retry on failure.
- **Traceability**: `crates/httpora-core/src/middleware/retry.rs:157` (`execute_for_method`), `:23` (`HttpMethod::is_idempotent`)

#### FR-13: CORS Middleware

`CorsLayer` MUST handle preflight OPTIONS requests and decorate responses with `Access-Control-*` headers according to a configurable `CorsConfig`.

- **Acceptance Criterion**: A preflight request with an allowed Origin returns a 204 response with `Access-Control-Allow-Origin` set to the matching origin.
- **Traceability**: `crates/httpora-core/src/middleware/cors.rs:50` (`CorsLayer`), `:67` (`preflight`), `:92` (`decorate_response`)

#### FR-14: Response Builder

`ResponseBuilder` MUST provide constructors for JSON (`json`), plain text (`text`), 204 No Content (`no_content`), and rate-limited 429 (`rate_limited`) HTTP responses.

- **Acceptance Criterion**: `ResponseBuilder::json(200, &json!({"ok":true}))` returns an `HttpResponse` with status 200 and `Content-Type: application/json`.
- **Traceability**: `crates/httpora-core/src/builder.rs:39` (`ResponseBuilder`)

#### FR-15: Request Extractor

`RequestExtractor` MUST support extracting a Bearer token from the Authorization header, performing a case-insensitive header lookup, and parsing a JSON body.

- **Acceptance Criterion**: `RequestExtractor::bearer_token(req)` returns `Some("token")` when the request has `Authorization: Bearer token`.
- **Traceability**: `crates/httpora-core/src/builder.rs:89` (`RequestExtractor`)

#### FR-16: Error Types

`HttptoraError` MUST be a single enum with variants for `RateLimited`, `CircuitOpen`, `RetryExhausted`, and `ParseError`, implementing `std::error::Error`.

- **Acceptance Criterion**: `HttptoraError::RateLimited { retry_after }` can be matched and its `Display` output includes the retry-after duration.
- **Traceability**: `crates/httpora-core/src/error.rs:6` (`HttptoraError`)

---

## Non-Functional Requirements

#### NFR-1: Type Safety (TypeScript)

The TypeScript public API MUST provide full static typing with zero `any` escape hatches in exported function signatures.

- **Acceptance Criterion**: `tsc --noEmit` passes with `strict: true` on any project importing `@kooshapari/quillts`.
- **Traceability**: `tsconfig.json:6` (`strict: true`)

#### NFR-2: Thread Safety (Rust)

All Rust middleware types that maintain shared state (`RateLimiter`, `CircuitBreaker`) MUST be `Send + Sync`.

- **Acceptance Criterion**: `RateLimiter` and `CircuitBreaker` are accepted by Tower's `ServiceBuilder` without Send/Sync errors.
- **Traceability**: `crates/httpora-core/src/middleware/rate_limit.rs:136` (inner `Mutex`); `circuit_breaker.rs:57` (inner `Mutex`)

#### NFR-3: Time Determinism

Time-dependent middleware MUST accept an injectable `Clock` type (`Arc<dyn Fn() -> Instant + Send + Sync>`) to enable deterministic testing.

- **Acceptance Criterion**: Each time-sensitive constructor has a `_with_clock` variant (e.g., `token_bucket_with_clock`).
- **Traceability**: `crates/httpora-core/src/middleware/clock.rs:5` (`Clock` type); `rate_limit.rs:157`, `circuit_breaker.rs:84`

#### NFR-4: Configurable Defaults

Every middleware MUST provide a `Default` implementation with sensible production values and allow full customization via `Config` structs.

- **Acceptance Criterion**: `RateLimiter::default()` creates a token-bucket limiter with capacity 100 and refill rate 10.0.
- **Traceability**: `rate_limit.rs:26` (`Default for RateLimitConfig`); `retry.rs:43` (`Default for BackoffConfig`), `:64` (`Default for RetryConfig`); `circuit_breaker.rs:34` (`Default for CircuitBreakerConfig`); `cors.rs:44` (`Default for CorsConfig`)

#### NFR-5: Cargo Feature Flags

The Rust crate MUST use Cargo feature flags (`tower`, `serde`, `serde_json`, `full`) to conditionally compile async-tower and serialization functionality.

- **Acceptance Criterion**: Building with `--no-default-features` excludes all tower and serde dependencies; the core rate limiter and circuit breaker compile without them.
- **Traceability**: `crates/httpora-core/Cargo.toml:19-24`

#### NFR-6: Error Trait Implementation

`HttptoraError` MUST implement `std::error::Error` and `Display`, enabling integration with Rust's error handling ecosystem.

- **Acceptance Criterion**: `fn handle(e: HttptoraError)` compiles and the error can be converted via `Box<dyn std::error::Error>`.
- **Traceability**: `crates/httpora-core/src/error.rs:20-39`

#### NFR-7: Zero Unsafe Code

The Rust crate MUST contain zero `unsafe` blocks in production code.

- **Acceptance Criterion**: `cargo build` produces no warnings; `#![forbid(unsafe_code)]` compiles successfully.
- **Traceability**: All source files (no `unsafe` blocks found)

#### NFR-8: Dependency Minimality

The Rust crate MUST NOT re-export or depend on Tokio types in its public API unless the `tower` feature is enabled.

- **Acceptance Criterion**: `pub use tokio::*` does not appear anywhere; `tokio` is optional and gated behind `cfg(feature = "tower")`.
- **Traceability**: `Cargo.toml:12` (`tokio` optional); `retry.rs:3-4` (`#[cfg(feature = "tower")]`)
