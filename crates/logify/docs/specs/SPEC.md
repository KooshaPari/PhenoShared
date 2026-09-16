# logkit Specification Oracle

> Derived from source on branch `spec/logify-oracle`. Crate: `logkit` v0.1.0 (`Cargo.toml`).
> Public surface: `src/lib.rs` re-exports `domain::*` and `application::*`; modules `adapters` and `infrastructure` are public but not flattened.

## Scope

Hexagonal structured-logging framework for Rust. This document maps functional requirements (FR) and non-functional requirements (NFR) to source symbols with testable acceptance criteria.

---

## Functional Requirements

### FR-1: Log Level Model

| Field | Value |
|-------|-------|
| **Source** | `src/domain/log_level.rs` → `Level` |
| **Also exported via** | `logkit::Level` (`src/lib.rs` → `domain/mod.rs`) |

**Description.** The library exposes a total-order enum of severity levels for filtering and serialization.

**Acceptance criteria**

| ID | Criterion | Verification |
|----|-----------|--------------|
| FR-1.1 | `Level` has variants `Trace`, `Debug`, `Info`, `Warn`, `Error`, `Fatal` | Inspect enum definition |
| FR-1.2 | Default level is `Info` (`#[default]` on `Info`) | `Level::default() == Level::Info` |
| FR-1.3 | Levels are totally ordered: `Trace < Debug < Info < Warn < Error < Fatal` | `PartialOrd`/`Ord` comparisons |
| FR-1.4 | `as_str()` returns `"TRACE"`, `"DEBUG"`, `"INFO"`, `"WARN"`, `"ERROR"`, `"FATAL"` respectively | Unit test per variant |
| FR-1.5 | `Display` writes the same string as `as_str()` | `format!("{level}")` |
| FR-1.6 | `Level` round-trips through `serde` JSON | Serialize + deserialize |

---

### FR-2: Structured Log Entry

| Field | Value |
|-------|-------|
| **Source** | `src/domain/log_entry.rs` → `LogEntry`, `LogEntry::new`, `LogEntry::with_field` |
| **Also exported via** | `logkit::LogEntry` |

**Description.** Each log event is a structured record with identity, severity, message, timestamp, and optional key-value fields.

**Acceptance criteria**

| ID | Criterion | Verification |
|----|-----------|--------------|
| FR-2.1 | `LogEntry::new(level, message)` sets `level` and `message` from arguments | Field equality |
| FR-2.2 | `new` assigns a non-nil `Uuid` to `id` | `id != Uuid::nil()` |
| FR-2.3 | `new` sets `timestamp` to current UTC (within test tolerance) | `chrono::Utc::now()` delta |
| FR-2.4 | `new` initializes `fields` as empty `Vec` | `fields.is_empty()` |
| FR-2.5 | `with_field(key, value)` appends `(key, value)` and returns `self` (builder style) | Chained calls, field count |
| FR-2.6 | `LogEntry` round-trips through `serde` JSON including `fields` | Serialize + deserialize |

---

### FR-3: Logger Port (Domain)

| Field | Value |
|-------|-------|
| **Source** | `src/domain/logger.rs` → `Logger` |
| **Also exported via** | `logkit::Logger` |

**Description.** Application code depends on an async logger port, not concrete sinks.

**Acceptance criteria**

| ID | Criterion | Verification |
|----|-----------|--------------|
| FR-3.1 | `Logger` is an `async_trait` with `async fn log(&self, entry: LogEntry) -> Result<(), LogError>` | Trait definition + mock impl compiles |
| FR-3.2 | `Logger` exposes `fn level(&self) -> Level` | Mock returns configured level |
| FR-3.3 | `Logger: Send + Sync` | Object-safe async trait bounds |

---

### FR-4: Log Error Taxonomy

| Field | Value |
|-------|-------|
| **Source** | `src/domain/logger.rs` → `LogError` |
| **Also exported via** | `logkit::LogError` |

**Description.** Logging failures are classified for callers to handle or propagate.

**Acceptance criteria**

| ID | Criterion | Verification |
|----|-----------|--------------|
| FR-4.1 | `LogError::Io(String)` variant exists | Pattern match |
| FR-4.2 | `LogError::Serialization(String)` variant exists | Pattern match |
| FR-4.3 | `Display` for `Io` prefixes with `"IO error: "` | `format!("{err}")` |
| FR-4.4 | `Display` for `Serialization` prefixes with `"Serialization error: "` | `format!("{err}")` |
| FR-4.5 | `LogError: std::error::Error` | Trait bound compiles |

---

### FR-5: Logger Builder (Application)

| Field | Value |
|-------|-------|
| **Source** | `src/application/logger_builder.rs` → `LoggerBuilder` |
| **Also exported via** | `logkit::LoggerBuilder` |

**Description.** Fluent builder constructs a configured logger without exposing internals.

**Acceptance criteria**

| ID | Criterion | Verification |
|----|-----------|--------------|
| FR-5.1 | `LoggerBuilder::new(name)` stores `name` and defaults `level` to `Level::Info` | Built logger `level()` is `Info` |
| FR-5.2 | `.level(l)` sets minimum severity and returns `Self` for chaining | Method chaining compiles |
| FR-5.3 | `.build()` returns `impl Logger` (concrete `ConsoleLogger`) | Type implements `Logger` |
| FR-5.4 | Built logger's `level()` reflects last `.level()` call | After `.level(Level::Warn)`, `level() == Warn` |

---

### FR-6: Console Logger Adapter

| Field | Value |
|-------|-------|
| **Source** | `src/application/logger_builder.rs` → `ConsoleLogger`, `impl Logger for ConsoleLogger` |
| **Also exported via** | `logkit::ConsoleLogger` |

**Description.** Default built logger writes human-readable lines to stdout when entry severity meets threshold.

**Acceptance criteria**

| ID | Criterion | Verification |
|----|-----------|--------------|
| FR-6.1 | `log` succeeds (`Ok(())`) for entries at or above configured level | Async test with captured output |
| FR-6.2 | `log` succeeds without writing for entries below configured level | No output when `entry.level < logger.level()` |
| FR-6.3 | Written line format is `[{level}] {name}: {message}` | String contains level, name, message |
| FR-6.4 | `level()` returns the level set at build time | Direct call |

---

### FR-7: Sink Port (Adapter)

| Field | Value |
|-------|-------|
| **Source** | `src/adapters/sinks/mod.rs` → `Sink` |
| **Access** | `logkit::adapters::Sink` (`src/adapters/mod.rs` re-exports `sinks::*`) |

**Description.** Output adapters implement a sink port for structured entries.

**Acceptance criteria**

| ID | Criterion | Verification |
|----|-----------|--------------|
| FR-7.1 | `Sink` is `async_trait` with `async fn write(&self, entry: &LogEntry) -> Result<(), LogError>` | Trait definition + mock impl |
| FR-7.2 | `Sink` has `async fn flush(&self) -> Result<(), LogError>` | Mock records flush call |
| FR-7.3 | `Sink: Send + Sync` | Trait bounds |

---

### FR-8: Console Sink Adapter

| Field | Value |
|-------|-------|
| **Source** | `src/adapters/sinks/mod.rs` → `ConsoleSink`, `impl Sink for ConsoleSink` |
| **Access** | `logkit::adapters::ConsoleSink` |

**Description.** Console sink routes high-severity lines to stderr and lower severities to stdout.

**Acceptance criteria**

| ID | Criterion | Verification |
|----|-----------|--------------|
| FR-8.1 | `ConsoleSink::new()` and `Default::default()` produce equivalent instances | Both construct empty struct |
| FR-8.2 | `write` for `entry.level >= Level::Error` emits to stderr | Captured stderr |
| FR-8.3 | `write` for `entry.level < Level::Error` emits to stdout | Captured stdout |
| FR-8.4 | Line format is `{level} [{message}]` | String parse |
| FR-8.5 | `flush` returns `Ok(())` without side effects | Async call |

---

### FR-9: Crate Module Surface

| Field | Value |
|-------|-------|
| **Source** | `src/lib.rs` |

**Description.** The crate exposes hexagonal layers as public modules with selective re-exports.

**Acceptance criteria**

| ID | Criterion | Verification |
|----|-----------|--------------|
| FR-9.1 | `logkit::{Level, LogEntry, Logger, LogError, LoggerBuilder, ConsoleLogger}` resolve without module path | `use logkit::{...}` compiles |
| FR-9.2 | `logkit::domain`, `logkit::application`, `logkit::adapters`, `logkit::infrastructure` are public modules | `mod` visibility in `lib.rs` |
| FR-9.3 | `logkit::adapters::Sink` and `logkit::adapters::ConsoleSink` are reachable | Import compiles |

---

## Non-Functional Requirements

### NFR-1: Async-First I/O Contracts

| Field | Value |
|-------|-------|
| **Source** | `src/domain/logger.rs` (`Logger`), `src/adapters/sinks/mod.rs` (`Sink`) |

**Acceptance criteria**

| ID | Criterion | Verification |
|----|-----------|--------------|
| NFR-1.1 | `Logger::log` and `Sink::{write, flush}` are `async` and usable inside `tokio` runtime | Integration stub with `#[tokio::test]` |
| NFR-1.2 | Traits use `async_trait` for object-safe async methods | `cargo doc` / source inspection |

---

### NFR-2: Structured Field Interoperability

| Field | Value |
|-------|-------|
| **Source** | `src/domain/log_entry.rs` → `fields: Vec<(String, serde_json::Value)>` |

**Acceptance criteria**

| ID | Criterion | Verification |
|----|-----------|--------------|
| NFR-2.1 | Arbitrary JSON values (string, number, bool, object, array) attach via `with_field` | Round-trip serde on entry |
| NFR-2.2 | `Level` and `LogEntry` derive `Serialize`/`Deserialize` | JSON fixture tests |

---

### NFR-3: Correlation Identity

| Field | Value |
|-------|-------|
| **Source** | `src/domain/log_entry.rs` → `id: Uuid` |

**Acceptance criteria**

| ID | Criterion | Verification |
|----|-----------|--------------|
| NFR-3.1 | Each `LogEntry::new` produces a distinct `id` | Two entries from sequential `new` calls differ |
| NFR-3.2 | `id` serializes as UUID string in JSON | Deserialize fixture |

---

### NFR-4: Thread-Safe Shared Loggers

| Field | Value |
|-------|-------|
| **Source** | `Logger: Send + Sync`, `Sink: Send + Sync` |

**Acceptance criteria**

| ID | Criterion | Verification |
|----|-----------|--------------|
| NFR-4.1 | `Arc<dyn Logger>` is `Send + Sync` | Compile-time assertion |
| NFR-4.2 | `Arc<dyn Sink>` is `Send + Sync` | Compile-time assertion |

---

### NFR-5: Hexagonal Layer Separation

| Field | Value |
|-------|-------|
| **Source** | `src/lib.rs`, `src/domain/mod.rs`, `src/application/mod.rs`, `src/adapters/mod.rs`, `src/infrastructure/mod.rs` |

**Acceptance criteria**

| ID | Criterion | Verification |
|----|-----------|--------------|
| NFR-5.1 | Domain layer (`domain/`) defines `Level`, `LogEntry`, `Logger`, `LogError` without adapter imports | `domain/` has no `adapters` use |
| NFR-5.2 | Application layer (`application/`) depends on `crate::domain` only for logger construction | `logger_builder.rs` imports |
| NFR-5.3 | Adapters layer (`adapters/`) depends on `crate::domain` for `Sink` | `sinks/mod.rs` imports |

---

## Traceability Matrix

| Requirement | Primary Source | Acceptance Artifact |
|-------------|----------------|---------------------|
| FR-1 | `domain/log_level.rs::Level` | `acceptance/fr-01-level.feature`, `acceptance/stubs/fr_01_level.rs` |
| FR-2 | `domain/log_entry.rs::LogEntry` | `acceptance/fr-02-log-entry.feature`, `acceptance/stubs/fr_02_log_entry.rs` |
| FR-3 | `domain/logger.rs::Logger` | `acceptance/fr-03-logger-port.feature`, `acceptance/stubs/fr_03_logger_port.rs` |
| FR-4 | `domain/logger.rs::LogError` | `acceptance/fr-04-log-error.feature`, `acceptance/stubs/fr_04_log_error.rs` |
| FR-5 | `application/logger_builder.rs::LoggerBuilder` | `acceptance/fr-05-logger-builder.feature`, `acceptance/stubs/fr_05_logger_builder.rs` |
| FR-6 | `application/logger_builder.rs::ConsoleLogger` | `acceptance/fr-06-console-logger.feature`, `acceptance/stubs/fr_06_console_logger.rs` |
| FR-7 | `adapters/sinks/mod.rs::Sink` | `acceptance/fr-07-sink-port.feature`, `acceptance/stubs/fr_07_sink_port.rs` |
| FR-8 | `adapters/sinks/mod.rs::ConsoleSink` | `acceptance/fr-08-console-sink.feature`, `acceptance/stubs/fr_08_console_sink.rs` |
| FR-9 | `lib.rs` | `acceptance/fr-09-crate-surface.feature`, `acceptance/stubs/fr_09_crate_surface.rs` |
| NFR-1 | `Logger`, `Sink` async traits | `acceptance/nfr-01-async-io.feature`, `acceptance/stubs/nfr_01_async_io.rs` |
| NFR-2 | `LogEntry::fields`, serde derives | `acceptance/nfr-02-structured-fields.feature`, `acceptance/stubs/nfr_02_structured_fields.rs` |
| NFR-3 | `LogEntry::id` | `acceptance/nfr-03-correlation-id.feature`, `acceptance/stubs/nfr_03_correlation_id.rs` |
| NFR-4 | `Send + Sync` bounds | `acceptance/nfr-04-thread-safety.feature`, `acceptance/stubs/nfr_04_thread_safety.rs` |
| NFR-5 | module layout | `acceptance/nfr-05-hexagonal-layers.feature`, `acceptance/stubs/nfr_05_hexagonal_layers.rs` |

---

## Out of Scope (Current Source)

- `src/infrastructure/mod.rs` is a stub with no public API.
- No file/network/custom sink implementations beyond `ConsoleSink`.
- No global logger registry or macros (`trace!`, `info!`, etc.).
- Benchmarks proving "zero-cost" are not defined in source.
