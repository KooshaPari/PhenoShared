# Langfuse OTLP Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in, privacy-preserving OTLP/HTTP exporter that sends SessionLedger operational spans to Langfuse-compatible endpoints without making external telemetry authoritative.

**Architecture:** Keep local ingestion, replay, and persistence unchanged. Add a small daemon telemetry adapter behind the existing `otel` feature; configure endpoint, auth headers, and enablement through environment variables, redact content-bearing attributes, and treat exporter errors as non-fatal.

**Tech Stack:** Rust, OpenTelemetry SDK/OTLP HTTP, existing `sl-daemon` feature flags, unit/integration tests.

---

### Task 1: Define exporter configuration and privacy contract

**Files:**

- Modify: `crates/sl-daemon/Cargo.toml`
- Modify: `crates/sl-daemon/src/otel.rs`
- Test: `crates/sl-daemon/src/otel.rs`

- [ ] Add an `LangfuseConfig` parser with `SL_LANGFUSE_ENABLED` (default false), `SL_LANGFUSE_OTLP_ENDPOINT`, and `SL_LANGFUSE_PUBLIC_KEY`/`SL_LANGFUSE_SECRET_KEY` environment inputs.
- [ ] Require endpoint plus both keys when enabled; reject malformed configuration with an actionable error.
- [ ] Build Basic auth only in memory and never log key values.
- [ ] Add tests covering disabled defaults, missing-key rejection, and endpoint normalization.

### Task 2: Wire OTLP/HTTP exporter into daemon telemetry

**Files:**

- Modify: `crates/sl-daemon/src/otel.rs`
- Modify: `crates/sl-daemon/src/main.rs`
- Test: `crates/sl-daemon/tests/otel_langfuse.rs`

- [ ] Construct an OTLP HTTP exporter only when configuration is enabled.
- [ ] Attach a batch span processor and preserve existing tracing behavior when disabled.
- [ ] Export only operation metadata (route, operation, outcome, duration, request correlation); explicitly omit prompts, responses, session bodies, file paths, and credentials.
- [ ] Ensure exporter initialization or export failure logs a warning and does not stop daemon startup or request handling.
- [ ] Add an integration test with a local HTTP receiver asserting sanitized payloads and non-fatal receiver failure.

### Task 3: Document operation and verify

**Files:**

- Modify: `crates/sl-daemon/README.md`
- Modify: `README.md`
- Test: existing daemon feature/build suites

- [ ] Document opt-in environment variables, privacy guarantees, endpoint examples, and shutdown/flush behavior.
- [ ] Run `cargo fmt --all --check`.
- [ ] Run `cargo test --manifest-path crates/sl-daemon/Cargo.toml` and the `otel` feature test suite.
- [ ] Run the repository quality gates relevant to daemon changes.
- [ ] Commit the adapter and documentation as one focused change.
