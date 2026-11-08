# Architecture Decision Records — helix-logging

## ADR-001: log Crate Facade for Ecosystem Compatibility

**Status:** Accepted

**Context:** Rust has two competing logging ecosystems: `log` (facade) and `tracing`. The library must choose one.

**Decision:** Implement `log::Log` trait. This makes `helix-logging` compatible with any existing Rust code that uses `log::info\!()`, `log::warn\!()`, etc. without requiring migration.

**Rationale:** The `log` crate is the standard for structured logging in the Rust ecosystem. `tracing` is used for distributed tracing (spans, events) and is handled by `helix-tracing`.

**Alternatives Considered:**
- `tracing` subscriber: would require all services to migrate to `tracing` macros.
- Custom macro system: incompatible with ecosystem libraries that use `log`.

**Consequences:** Services that want structured tracing alongside logging must use both `helix-logging` (for `log` compatibility) and `helix-tracing` (for spans).

---

## ADR-002: Thread-Local Correlation ID Storage

**Status:** Accepted

**Context:** Correlation IDs must propagate through a request without passing them as function parameters to every log call.

**Decision:** Store correlation IDs in a `thread_local\!` variable. Async code that crosses thread boundaries must re-set the correlation ID using `with_correlation_id`.

**Rationale:** Thread-local storage is the simplest, zero-overhead approach for synchronous code. For async, services are expected to re-propagate IDs at task spawn boundaries.

**Alternatives Considered:**
- `tokio::task_local\!`: requires Tokio-specific code; makes the library non-portable.
- Context propagation via function parameters: requires API changes to all logging sites.

**Consequences:** Async services must be aware of thread-local limitation and re-set correlation IDs after spawning tasks.

---

## ADR-003: NDJSON Output Format

**Status:** Accepted

**Context:** JSON log output format options include pretty-printed, single-line object, and NDJSON (newline-delimited JSON).

**Decision:** Use NDJSON (one JSON object per line) for structured output.

**Rationale:** NDJSON is the standard for log aggregators (Loki, Elasticsearch, Splunk). Each line is independently parseable.

**Consequences:** Log files are not human-readable without a JSON formatter (e.g., `jq`). Offset by rich text format for development use.
