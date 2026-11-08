# PhenoObservability — FR/NFR Catalog

**Catalog version:** 2026-05-29
**Traceability baseline:** PRs #94 (QuestDB integration tests), #95 (observably-sentinel resilience), #96 (CachePort/TimeSeriesPort hexagonal ports + in-memory doubles)
**Crate inventory (13):** helix-logging · pheno-dragonfly · pheno-questdb · phenotype-llm · phenotype-mcp-server · phenotype-observably-logging · phenotype-observably-macros · phenotype-observably-ports · phenotype-observably-sentinel · phenotype-observably-tracing · tracely-core · tracely-sentinel · tracingkit

## Subsystem specification index

This catalog is the normalized spec landing page for subsystem-level requirements. Legacy spec IDs remain in [`docs/FUNCTIONAL_REQUIREMENTS.md`](../FUNCTIONAL_REQUIREMENTS.md), and this file provides traceability + status for implementation and remaining gaps.

### Canonical subsystem references

- [SOTA Observability](../research/SOTA-OBSERVABILITY.md)
- [SOTA Log Analytics](../research/SOTA-LOG-ANALYTICS.md)

| Subsystem | Requirement scope | Traceability | SOTA reference |
|---|---|---|---|
| Tracing | [Tracing Subsystem](#tracing-subsystem) | `phenotype-observably-tracing` | [SOTA-OBSERVABILITY](../research/SOTA-OBSERVABILITY.md) |
| Logging | [Logging Subsystem](#logging-subsystem) | `helix-logging`, `phenotype-observably-logging` | [SOTA-LOG-ANALYTICS](../research/SOTA-LOG-ANALYTICS.md) |
| Time-Series Ingest | [Time-Series Ingest (QuestDB / BatchIngester)](#time-series-ingest-questdb--batchingester) | `pheno-questdb` | [SOTA-OBSERVABILITY](../research/SOTA-OBSERVABILITY.md) |
| Cache Port | [Cache Port (Dragonfly Adapter)](#cache-port-dragonfly-adapter) | `phenotype-observably-ports`, `pheno-dragonfly` | [SOTA-LOG-ANALYTICS](../research/SOTA-LOG-ANALYTICS.md) |
| Time-Series Port | [Time-Series Port (Hexagonal)](#time-series-port-hexagonal) | `phenotype-observably-ports` | [SOTA-OBSERVABILITY](../research/SOTA-OBSERVABILITY.md) |
| Resilience | [Resilience Primitives (observably-sentinel / tracely-sentinel)](#resilience-primitives-observably-sentinel--tracely-sentinel) | `phenotype-observably-sentinel`, `tracely-sentinel` | [SOTA-OBSERVABILITY](../research/SOTA-OBSERVABILITY.md) |

---

## Functional Requirements

### Tracing Subsystem

| ID | Title | Description | Acceptance Criteria | Traceability |
|----|-------|-------------|---------------------|--------------|
| FR-OBS-001 | Configurable trace levels | System must support configurable tracing with levels TRACE, DEBUG, INFO, WARN, ERROR | All five levels accepted; invalid level returns error | `phenotype-observably-tracing` · `test_config_level_validation` |
| FR-OBS-002 | Unique span/trace IDs | System must generate UUID v4 span IDs and trace IDs | Each generated ID is non-empty, unique across 1000 calls | `phenotype-observably-tracing` · `test_span_id_generation`, `test_trace_id_generation` |
| FR-OBS-003 | Async context propagation | Tracing context must propagate across async boundaries preserving parent-child span relationships | Parent ID on child span matches originator span ID | `phenotype-observably-tracing` · `test_trace_context_creation`, `test_trace_context_clone` |
| FR-OBS-004 | Span event recording | System must support optional open/close/new_message span events | Events toggle via config; absent by default | `phenotype-observably-tracing` · `test_config_span_events` |
| FR-OBS-005 | Thread metadata in spans | System must optionally include thread ID and thread name in spans | Thread name and ID appear in span fields when enabled | `phenotype-observably-tracing` · `test_config_thread_info` |
| FR-OBS-006 | Idempotent subscriber init | Tracing initialisation must fail gracefully (not panic) when subscriber already registered | Returns `Err` on second init; process continues | `phenotype-observably-tracing` · `test_double_init_error` |
| FR-OBS-007 | Level string mapping | Trace level strings must map 1-to-1 to `tracing::Level` enum | `"TRACE"/"DEBUG"/"INFO"/"WARN"/"ERROR"` each return correct variant | `phenotype-observably-tracing` · `test_level_as_str_all_levels` |
| FR-OBS-008 | TraceKey serialisation | `TraceKey` must implement `Display` and `Debug` | `format!("{key}")` produces non-empty, deterministic string | `phenotype-observably-tracing` · `test_trace_key_display` |

### Logging Subsystem

| ID | Title | Description | Acceptance Criteria | Traceability |
|----|-------|-------------|---------------------|--------------|
| FR-OBS-009 | Structured logging with correlation IDs | System must emit structured log records carrying a correlation ID field | Each log record contains `correlation_id` key | `helix-logging` · `test_logger_config_defaults` |
| FR-OBS-010 | Auto-generate correlation IDs | System must generate a unique correlation ID when none is supplied | Two calls without supplied ID produce different IDs | `helix-logging` · `test_log_context_autogen_id` |
| FR-OBS-011 | Preserve caller-supplied IDs | Provided correlation IDs must pass through unchanged | ID in output equals ID passed by caller | `helix-logging` · `test_log_context_with_provided_id` |
| FR-OBS-012 | Full log-level support | Logger must honour TRACE/DEBUG/INFO/WARN/ERROR filter levels | Records below the configured level are suppressed | `helix-logging` · `test_logger_level_filter` |
| FR-OBS-013 | Timestamp inclusion | Logger must include ISO-8601 timestamps in output | Each record contains a parseable timestamp field | `helix-logging` · `test_logger_include_timestamps` |
| FR-OBS-014 | Source location | Logger must include file name and line number in records | `file` and `line` fields present in each record | `helix-logging` · `test_logger_include_location` |
| FR-OBS-015 | JSON log macro | JSON logging macro must serialise structured data correctly | `log_json!` macro output is valid JSON with all provided fields | `helix-logging` · `test_log_json_serialization` |

### Time-Series Ingest (QuestDB / BatchIngester)

| ID | Title | Description | Acceptance Criteria | Traceability |
|----|-------|-------------|---------------------|--------------|
| FR-OBS-016 | Buffered batch ingest | `BatchIngester` must buffer ILP lines and flush on demand or at `flush_size` threshold | `pending()` increments per push; returns `true` at threshold | `pheno-questdb` · PR #94 · `test_batch_ingester_*` |
| FR-OBS-017 | Configurable flush size | Flush size must be set at construction and trigger auto-flush signal | `push_metric` returns `true` exactly when `lines.len() >= flush_size` | `pheno-questdb` · PR #94 |
| FR-OBS-018 | Timestamp precision modes | Ingester must support nanosecond/microsecond/millisecond timestamp precision | ILP line timestamps match selected precision | `pheno-questdb` · PR #94 · `test_timestamp_precision_*` |
| FR-OBS-019 | Out-of-order resilience | Ingester must handle out-of-order (OOO) timestamps without data loss or panic | OOO rows buffered and flushed successfully; no panic | `pheno-questdb` · PR #94 · `test_ooo_*` |
| FR-OBS-020 | Flush clears buffer | After `flush()` the pending count must be zero | `pending()` == 0 after successful flush; flushed count returned | `pheno-questdb` · PR #94 |
| FR-OBS-021 | SQL query interface | `QuestDBClient` must execute arbitrary SQL and deserialise results | `query::<T>` returns populated `Vec<T>` on valid SQL | `pheno-questdb` |
| FR-OBS-022 | Metric aggregation | Client must support `SAMPLE BY` aggregation queries | `aggregate()` returns `avg/min/max` fields per time bucket | `pheno-questdb` |

### Cache Port (Dragonfly Adapter)

| ID | Title | Description | Acceptance Criteria | Traceability |
|----|-------|-------------|---------------------|--------------|
| FR-OBS-023 | Key-value get | `CachePort::get` must return `Some(bytes)` for existing keys, `None` for absent keys | Round-trip set→get returns original bytes; missing key returns `None` | `phenotype-observably-ports` · PR #96 · `cache_set_get_delete` |
| FR-OBS-024 | Key-value set with TTL | `CachePort::set` must store bytes at a key with a TTL in seconds | Value retrievable after set; TTL param accepted without error | `phenotype-observably-ports` · PR #96 |
| FR-OBS-025 | Key deletion | `CachePort::delete` must remove a key; deleting absent key is a no-op (not an error) | Key absent after delete; `delete` on missing key returns `Ok(())` | `phenotype-observably-ports` · PR #96 · `cache_set_get_delete` |
| FR-OBS-026 | TTL refresh | `CachePort::expire` must refresh TTL and return `true` if key exists, `false` if absent | Returns `true` for present key, `false` for missing key | `phenotype-observably-ports` · PR #96 · `cache_expire_returns_*` |

### Time-Series Port (Hexagonal)

| ID | Title | Description | Acceptance Criteria | Traceability |
|----|-------|-------------|---------------------|--------------|
| FR-OBS-027 | Metric ingest via port | `TimeSeriesPort::ingest_metric` must buffer a `TsMetric` | `pending()` increments by 1 per call | `phenotype-observably-ports` · PR #96 · `ts_ingest_and_flush` |
| FR-OBS-028 | Log ingest via port | `TimeSeriesPort::ingest_log` must buffer a `TsLogEntry` | `pending()` increments by 1 per call | `phenotype-observably-ports` · PR #96 |
| FR-OBS-029 | Port flush | `TimeSeriesPort::flush` must drain buffer and return flushed row count | `pending()` == 0 after flush; return value equals rows flushed | `phenotype-observably-ports` · PR #96 · `ts_ingest_and_flush`, `ts_flush_empty_is_zero` |
| FR-OBS-030 | Multi-flush accumulation | Successive flushes must accumulate rows in `flushed_*` collections | `flushed_count()` equals sum across all flush rounds | `phenotype-observably-ports` · PR #96 · `ts_multiple_flush_accumulates` |

### Resilience Primitives (observably-sentinel / tracely-sentinel)

| ID | Title | Description | Acceptance Criteria | Traceability |
|----|-------|-------------|---------------------|--------------|
| FR-OBS-031 | Token-bucket rate limiting | `Sentinel` must allow up to burst-capacity requests within a second window | First `rps+burst` calls succeed; subsequent call within same window returns `RateLimitExceeded` | `phenotype-observably-sentinel` · PR #95 · `sentinel_allows_requests_within_burst`, `sentinel_rejects_after_burst_exhausted` |
| FR-OBS-032 | Circuit breaker closed start | `CircuitBreaker` must initialise in `Closed` state | `cb.state() == CircuitState::Closed` on construction | `phenotype-observably-sentinel` · PR #95 · `circuit_breaker_starts_closed` |
| FR-OBS-033 | Circuit breaker trip on threshold | Breaker must transition to `Open` after `failure_threshold` consecutive failures | State == `Open` after N failures where N == `failure_threshold` | `phenotype-observably-sentinel` · PR #95 · `circuit_breaker_trips_after_threshold` |
| FR-OBS-034 | Circuit breaker rejects while open | `CircuitBreaker::call` must return `Err(CircuitOpen)` without invoking closure when in `Open` state | Closure not called; `Err(SentinelError::CircuitOpen)` returned | `phenotype-observably-sentinel` · PR #95 · `circuit_breaker_rejects_while_open` |
| FR-OBS-035 | Half-open recovery | Breaker must transition `Open→HalfOpen` after `open_duration_ms`; success in HalfOpen resets to `Closed` | State == `Closed` after successful probe call post-timeout | `phenotype-observably-sentinel` · PR #95 · `circuit_breaker_resets_on_success_after_half_open` |
| FR-OBS-036 | Half-open re-trip | Failure in `HalfOpen` state must re-open the breaker | State == `Open` after failed probe in HalfOpen | `phenotype-observably-sentinel` · PR #95 · `circuit_breaker_failure_in_half_open_reopens` |
| FR-OBS-037 | Failure counter reset on success | A successful call must reset the consecutive-failure counter | After success, `failure_threshold` additional failures required to re-open | `phenotype-observably-sentinel` · PR #95 · `circuit_breaker_failure_counter_resets_on_success` |
| FR-OBS-038 | Bulkhead concurrent slot cap | `Bulkhead` must reject acquisitions beyond its configured capacity | `acquire()` returns `BulkheadFull(N)` when `in_flight >= capacity` | `phenotype-observably-sentinel` · PR #95 · `bulkhead_rejects_beyond_capacity` |
| FR-OBS-039 | Bulkhead RAII guard release | Dropping a `BulkheadGuard` must decrement the in-flight counter | `in_flight()` == 0 after all guards dropped | `phenotype-observably-sentinel` · PR #95 · `bulkhead_guard_releases_on_drop` |
| FR-OBS-040 | Bulkhead telemetry counters | Bulkhead must track cumulative accepted and rejected call counts | `total_accepted + total_rejected` == total acquire attempts | `phenotype-observably-sentinel` · PR #95 · `bulkhead_tracks_accepted_and_rejected_counts` |
| FR-OBS-041 | Bulkhead thread safety | Bulkhead must be safe under concurrent acquisition from multiple threads | All guards released; `in_flight() == 0` after all threads finish | `phenotype-observably-sentinel` · PR #95 · `bulkhead_concurrent_contention` |

---

## Non-Functional Requirements

| ID | Title | Description | Acceptance Criteria | Traceability |
|----|-------|-------------|---------------------|--------------|
| NFR-OBS-001 | Hexagonal port object-safety (cache) | `CachePort` must be object-safe (`dyn CachePort` usable behind `Box`) | `let _: Box<dyn CachePort> = Box::new(InMemoryCache::default())` compiles and runs | PR #96 · `cache_port_is_object_safe` |
| NFR-OBS-002 | Hexagonal port object-safety (timeseries) | `TimeSeriesPort` must be object-safe | `let _: Box<dyn TimeSeriesPort> = Box::new(InMemoryTimeSeries::default())` compiles and runs | PR #96 · `ts_port_is_object_safe` |
| NFR-OBS-003 | In-memory test doubles | Both `CachePort` and `TimeSeriesPort` must have in-memory doubles gated on `test-util` feature, requiring no network | All port unit tests pass without running QuestDB or Dragonfly | PR #96 · `test_doubles` module |
| NFR-OBS-004 | No-network unit tests | All unit tests must pass without any external service dependency | `cargo test --workspace` passes with no Docker/network | PRs #94, #95, #96 |
| NFR-OBS-005 | MSRV 1.85 | All crates must compile on Rust 1.85 stable | CI passes on toolchain 1.85; `deny.toml` enforces `msrv = "1.85"` | PR #86 |
| NFR-OBS-006 | Workspace-wide lint hygiene | `cargo clippy --workspace -- -D warnings` must produce zero warnings | CI quality-gate passes | PR #93 |
| NFR-OBS-007 | Audit-clean dependencies | No active RUSTSEC advisories in dependency tree | `cargo deny check advisories` exits 0 | PRs #75, #76 |
| NFR-OBS-008 | Rate limiter config serialisability | `RateLimitConfig` and `CircuitBreakerConfig` must round-trip through JSON | Serde round-trip test passes | PR #95 · `rate_limit_config_roundtrip_json` |
| NFR-OBS-009 | SentinelError human-readable messages | All `SentinelError` variants must produce descriptive `Display` strings | Display strings match expected literals in test | PR #95 · `error_display_messages` |
| NFR-OBS-010 | Hexagonal architecture — no domain squatting | Crates `phenotype-llm` and `phenotype-mcp-server` reside inside PhenoObservability but provide LLM/MCP domain logic unrelated to observability; they must be extracted to their own Phenotype-org repos | Each crate lives in its own repo with `phenotype-observably-*` as an optional dependency, not a sibling | PARTIAL — PR refactor/remove-domain-squatters: both crates removed from workspace `members`; directories preserved with EXTRACT_NOTE.md; physical repo-move awaits user decision |
| NFR-OBS-011 | Consolidated resilience crate | `phenotype-observably-sentinel` and `tracely-sentinel` implement overlapping resilience primitives; these must be consolidated onto a single shared `phenotype-resilience` crate consumed by all Phenotype repos | PLANNED — Single crate; duplicate implementations removed; consumer repos updated | PLANNED |
| NFR-OBS-012 | Alerting depth | `tracely-sentinel` / `tracely-core` expose health-check and alerting stubs only; full alerting rule engine (threshold-based, anomaly, aggregation window) is absent | Alerting engine with rule CRUD, evaluation loop, and notification dispatch implemented and tested | SHIPPED — PR #feat/alerting-engine · `phenotype-observably-sentinel::alerting` · `AlertRule`, `AlertEvaluator`, `AlertSink` port (`InMemoryAlertSink`, `LogAlertSink`) · 16 alerting tests green |
| NFR-OBS-013 | Metrics aggregation depth | `QuestDBClient::aggregate` covers a single `SAMPLE BY` pattern; percentile (p50/p95/p99), histogram, and counter aggregation surfaces are absent | `MetricsPort` hexagonal trait (counter/gauge/histogram) + `InMemoryMetrics` test double + `PrometheusMetrics` adapter implemented in `phenotype-observably-ports`; 12 metrics tests + 4 Prometheus adapter tests = 16 new tests green | SHIPPED — PR feat/metrics-port · `MetricsPort`, `InMemoryMetrics`, `PrometheusMetrics` · 16 new metrics tests green |
| NFR-OBS-014 | Dragonfly TTL enforcement | `InMemoryCache` double does not enforce TTL expiry; real Dragonfly adapter TTL behaviour lacks integration tests | PLANNED — Integration tests (with real Dragonfly instance or testcontainer) verify TTL expiry and `expire` semantics | PLANNED |

---

## PLANNED Gap Summary

| Gap | Blocking PR | Priority |
|-----|-------------|----------|
| Physical move of `phenotype-llm` dir to own Phenotype-org repo | refactor/remove-domain-squatters (workspace member removed; code preserved) | High — user decision required |
| Physical move of `phenotype-mcp-server` dir to own Phenotype-org repo | refactor/remove-domain-squatters (workspace member removed; code preserved) | High — user decision required |
| Consolidate `phenotype-observably-sentinel` + `tracely-sentinel` → `phenotype-resilience` | PLANNED — None | High — code duplication |
| Alerting rule engine (threshold/anomaly/window) | PR feat/alerting-engine | SHIPPED |
| Metrics aggregation depth (percentile/histogram) | PR feat/metrics-port | SHIPPED |
| Dragonfly TTL integration tests | PLANNED — None | Low |
