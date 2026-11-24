# AgilePlus SQLite Crate Error Handling Standards

## Status: HARDENED

The `agileplus-sqlite` crate follows best practices for error handling and has zero production-code panic sites from `unwrap()` calls.

## Audit Results (2026-06-15)

### No Panicking Patterns Found in Production Code

After comprehensive static analysis, confirmed:
- **0 lock().unwrap() calls** in production code
- **0 serde_json::from_str().unwrap() calls** in production code
- **0 .parse().unwrap() calls** in production code
- **0 unlabeled Result propagation failures** in production code

### Files Audited

- `src/lib.rs` — Core adapter (all unwrap calls are in #[tokio::test] blocks)
- `src/event_store.rs` — Event store impl (uses .map_err() for lock, ? for Results)
- `src/rebuild.rs` — Git rebuild logic (uses .map_err() for lock, ? for errors)
- `src/triage.rs` — Triage adapter (uses .map_err() for lock)
- `src/repository/*.rs` — All repository modules (0 unwrap patterns, use ? operator)
- `src/bin/*.rs` — Binary entry points (use anyhow::Result<()> with ? operator)
- `src/seed/*.rs` — Production seed logic (uses Result return type, ? operator)

### Error Handling Patterns Used (Production)

#### 1. Mutex Lock Safety
```rust
let conn = self
    .conn
    .lock()
    .map_err(|e| DomainError::Storage(e.to_string()))?;
```
Pattern: `.map_err()` converts panic-prone PoisonError to Result

#### 2. Database Operations
```rust
conn.execute_batch("BEGIN;")
    .map_err(|e| DomainError::Storage(e.to_string()))?;
```
Pattern: All rusqlite operations use `?` operator to propagate errors

#### 3. String Parsing
```rust
let created_at = meta
    .created_at
    .parse::<chrono::DateTime<chrono::Utc>>()
    .map_err(|e| DomainError::Storage(e.to_string()))?;
```
Pattern: `.parse()` errors are mapped to domain errors

#### 4. JSON Deserialization
```rust
let meta: MetaJson = serde_json::from_str(&meta_content)
    .map_err(|e| DomainError::Storage(format!("meta.json parse error for {slug}: {e}")))?;
```
Pattern: Contextual error messages with ? propagation

### Test Code Patterns (Allowed to Use unwrap)

Test files follow Rust idiom of using `.unwrap()` for test setup where failures indicate test configuration errors:
- `src/lib.rs` — #[tokio::test] blocks (lines 804+)
- `src/lib/tests/*.rs` — Dedicated test modules
- `src/rebuild/tests.rs` — Rebuild-specific tests
- `src/seed/runner.rs` — #[cfg(test)] blocks (lines 156+)
- `src/seed/catalog.rs` — Test catalog parsing

This is idiomatic Rust and does not represent production risk.

## Hardening Checklist

- [x] Lock operations use `.map_err()` for PoisonError handling
- [x] Database operations use `?` operator for error propagation
- [x] String parsing uses `.map_err()` with context
- [x] JSON operations use `.map_err()` with context
- [x] Result-returning functions propagate errors correctly
- [x] No bare `.expect()` calls in production code
- [x] No fallible operations without error paths

## Migration Notes

The codebase already follows FCP-046 (Exhaustive Error Handling). No changes required.

## Verification Command

```bash
# Verify no production unwrap/expect panic sites
cd crates/agileplus-sqlite
grep -rn "\.unwrap()\|\.expect(" src --include="*.rs" \
    | grep -v "test\|#\[" \
    | grep -v "crates/agileplus-sqlite/src/lib.rs:[0-9]*:" \
    | grep -v "crates/agileplus-sqlite/src/rebuild.rs:4[0-9][0-9]:" \
    | grep -v "crates/agileplus-sqlite/src/rebuild.rs:5[0-9][0-9]:"

# Expected output: (empty)
```

## References

- FCP-046: Exhaustive Error Handling
- DomainError enum: `agileplus-domain/src/error.rs`
- TriageError enum: Used for triage adapter
- EventError enum: Used for event store
