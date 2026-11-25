# PhenoObservability — FR/NFR Catalog

Auto-generated from `docs/FUNCTIONAL_REQUIREMENTS.md` for Tracera traceability ingestion.

---

## 1. Tracing

### FR-OBS-001 — Configurable tracing with log levels

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** System must support configurable tracing with log levels (TRACE, DEBUG, INFO, WARN, ERROR).

**Acceptance Criteria**
- Configurable log level accepted at initialization
- Each log level filters output correctly

**Traceability**
- Crate: `pheno-tracing`
- tests/unit/pheno-tracing/test_config_level_validation.rs

---

### FR-OBS-002 — Unique span IDs and trace IDs via UUID v4

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** System must generate unique span IDs and trace IDs using UUID v4.

**Traceability**
- Crate: `pheno-tracing`
- tests/unit/pheno-tracing/test_span_id_generation.rs
- tests/unit/pheno-tracing/test_trace_id_generation.rs

---

### FR-OBS-003 — Async-safe trace context propagation

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Tracing context must propagate across async boundaries with correct parent-child relationships.

**Traceability**
- Crate: `pheno-tracing`
- tests/unit/pheno-tracing/test_trace_context_creation.rs
- tests/unit/pheno-tracing/test_trace_context_clone.rs

---

### FR-OBS-004 — Optional span event recording

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** System must support optional span event recording (open, close, new_message).

**Traceability**
- Crate: `pheno-tracing`
- tests/unit/pheno-tracing/test_config_span_events.rs

---

### FR-OBS-005 — Thread ID and name in trace spans

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** System must support thread ID and thread name inclusion in trace spans.

**Traceability**
- Crate: `pheno-tracing`
- tests/unit/pheno-tracing/test_config_thread_info.rs

---

### FR-OBS-006 — Graceful double-init failure

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Tracing initialization must fail gracefully when subscriber already initialized.

**Traceability**
- Crate: `pheno-tracing`
- tests/unit/pheno-tracing/test_double_init_error.rs

---

### FR-OBS-007 — Trace level string-to-enum mapping

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Trace level strings must map correctly to tracing Level enum.

**Traceability**
- Crate: `pheno-tracing`
- tests/unit/pheno-tracing/test_level_as_str_all_levels.rs

---

### FR-OBS-008 — TraceKey Display and Debug serialization

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** TraceKey must implement Display and Debug for serialization.

**Traceability**
- Crate: `pheno-tracing`
- tests/unit/pheno-tracing/test_trace_key_display.rs

---

## 2. Logging

### FR-OBS-009 — Structured logging with correlation IDs

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** System must support structured logging with correlation IDs.

**Traceability**
- Crate: `helix-logging`
- tests/unit/helix-logging/test_logger_config_defaults.rs

---

### FR-OBS-010 — Auto-generated correlation IDs

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** System must generate unique correlation IDs when none provided.

**Traceability**
- Crate: `helix-logging`
- tests/unit/helix-logging/test_log_context_autogen_id.rs

---

### FR-OBS-011 — Preserve provided correlation IDs

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** System must preserve provided correlation IDs in logging context.

**Traceability**
- Crate: `helix-logging`
- tests/unit/helix-logging/test_log_context_with_provided_id.rs

---

### FR-OBS-012 — All standard log levels supported

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Logger must support all standard log levels (Trace, Debug, Info, Warn, Error).

**Traceability**
- Crate: `helix-logging`
- tests/unit/helix-logging/test_logger_level_filter.rs

---

### FR-OBS-013 — Timestamps in log output

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Logger must include timestamps in output.

**Traceability**
- Crate: `helix-logging`
- tests/unit/helix-logging/test_logger_include_timestamps.rs

---

### FR-OBS-014 — File and line location in logs

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Logger must include file and line location information.

**Traceability**
- Crate: `helix-logging`
- tests/unit/helix-logging/test_logger_include_location.rs

---

### FR-OBS-015 — JSON logging macro serialization

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** JSON logging macro must serialize structured data correctly.

**Traceability**
- Crate: `helix-logging`
- tests/unit/helix-logging/test_log_json_serialization.rs

---

## 3. Rate Limiting

### FR-OBS-016 — Token bucket starts at full capacity

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Token bucket must start with full capacity.

**Traceability**
- Crate: `tracely-sentinel`
- tests/unit/tracely-sentinel/test_token_bucket_initial_capacity.rs

---

### FR-OBS-017 — Token bucket refuses acquisition when exhausted

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Token bucket must refuse acquisition when exhausted.

**Traceability**
- Crate: `tracely-sentinel`
- tests/unit/tracely-sentinel/test_token_bucket_exhaustion.rs

---

### FR-OBS-018 — Token bucket refills at configured rate

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Token bucket must refill at configured rate.

**Traceability**
- Crate: `tracely-sentinel`
- tests/unit/tracely-sentinel/test_token_bucket_refill_rate.rs

---

### FR-OBS-019 — Token bucket capacity ceiling during refill

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Token bucket must not exceed capacity during refill.

**Traceability**
- Crate: `tracely-sentinel`
- tests/unit/tracely-sentinel/test_token_bucket_capacity_ceiling.rs

---

### FR-OBS-020 — Leaky bucket enforces queue capacity

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Leaky bucket must enforce queue capacity.

**Traceability**
- Crate: `tracely-sentinel`
- tests/unit/tracely-sentinel/test_leaky_bucket_capacity_limit.rs

---

### FR-OBS-021 — Leaky bucket pending request tracking

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Leaky bucket must track pending requests accurately.

**Traceability**
- Crate: `tracely-sentinel`
- tests/unit/tracely-sentinel/test_leaky_bucket_pending_count.rs

---

### FR-OBS-022 — Leaky bucket leak rate

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Leaky bucket must leak at configured rate.

**Traceability**
- Crate: `tracely-sentinel`
- tests/unit/tracely-sentinel/test_leaky_bucket_leak_rate.rs

---

## 4. Circuit Breaker

### FR-OBS-023 — Circuit breaker starts Closed

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Circuit breaker must start in Closed state.

**Traceability**
- Crate: `tracely-sentinel`
- tests/unit/tracely-sentinel/test_circuit_breaker_initial_state.rs

---

### FR-OBS-024 — Circuit breaker failure count tracking

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Circuit breaker must track failure count.

**Traceability**
- Crate: `tracely-sentinel`
- tests/unit/tracely-sentinel/test_circuit_breaker_failure_tracking.rs

---

### FR-OBS-025 — Transition to Open on threshold exceeded

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Circuit breaker must transition to Open when threshold exceeded.

**Traceability**
- Crate: `tracely-sentinel`
- tests/unit/tracely-sentinel/test_circuit_breaker_open_transition.rs

---

### FR-OBS-026 — Open state blocks requests

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Circuit breaker must block requests in Open state.

**Traceability**
- Crate: `tracely-sentinel`
- tests/unit/tracely-sentinel/test_circuit_breaker_open_blocks_requests.rs

---

### FR-OBS-027 — Half-Open state after timeout

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Circuit breaker must enter Half-Open state after timeout.

**Traceability**
- Crate: `tracely-sentinel`
- tests/unit/tracely-sentinel/test_circuit_breaker_half_open_transition.rs

---

### FR-OBS-028 — Close on success in Half-Open

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Circuit breaker must close on successful request in Half-Open state.

**Traceability**
- Crate: `tracely-sentinel`
- tests/unit/tracely-sentinel/test_circuit_breaker_half_open_success.rs

---

### FR-OBS-029 — Reset failure count on success

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Circuit breaker must reset failure count on success.

**Traceability**
- Crate: `tracely-sentinel`
- tests/unit/tracely-sentinel/test_circuit_breaker_failure_reset.rs

---

### FR-OBS-030 — Config validates thresholds

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Circuit breaker configuration must validate thresholds.

**Traceability**
- Crate: `tracely-sentinel`
- tests/unit/tracely-sentinel/test_circuit_breaker_config_validation.rs

---

## 5. Bulkhead

### FR-OBS-031 — Bulkhead enforces partition count limits

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Bulkhead must enforce partition count limits.

**Traceability**
- Crate: `tracely-sentinel`
- tests/unit/tracely-sentinel/test_bulkhead_partition_limit.rs

---

### FR-OBS-032 — Bulkhead creates guards for successful acquisitions

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Bulkhead must create guards for successful acquisitions.

**Traceability**
- Crate: `tracely-sentinel`
- tests/unit/tracely-sentinel/test_bulkhead_guard_creation.rs

---

### FR-OBS-033 — Bulkhead releases partition on guard drop

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Bulkhead must release partition on guard drop.

**Traceability**
- Crate: `tracely-sentinel`
- tests/unit/tracely-sentinel/test_bulkhead_guard_release.rs

---

### FR-OBS-034 — Bulkhead prevents over-allocation across partitions

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Bulkhead must prevent over-allocation across partitions.

**Traceability**
- Crate: `tracely-sentinel`
- tests/unit/tracely-sentinel/test_bulkhead_multi_partition_isolation.rs

---

### FR-OBS-035 — Bulkhead config validates partition counts

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Bulkhead configuration must validate partition counts.

**Traceability**
- Crate: `tracely-sentinel`
- tests/unit/tracely-sentinel/test_bulkhead_config_validation.rs

---

### FR-OBS-036 — Bulkhead supports concurrent partition access

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Bulkhead must support concurrent partition access.

**Traceability**
- Crate: `tracely-sentinel`
- tests/unit/tracely-sentinel/test_bulkhead_concurrent_access.rs

---

### FR-OBS-037 — Bulkhead exhausted error on capacity exceeded

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Bulkhead must return exhausted error when capacity exceeded.

**Traceability**
- Crate: `tracely-sentinel`
- tests/unit/tracely-sentinel/test_bulkhead_exhausted_error.rs

---

## 6. Configuration

### FR-OBS-038 — Rate limiter config validates capacity > 0

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Rate limiter config must validate capacity > 0.

**Traceability**
- Crate: `tracely-sentinel`
- tests/unit/tracely-sentinel/test_rate_limiter_config_validation.rs

---

### FR-OBS-039 — Circuit breaker config validates failure threshold

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Circuit breaker config must validate failure threshold.

**Traceability**
- Crate: `tracely-sentinel`
- tests/unit/tracely-sentinel/test_circuit_breaker_config_defaults.rs

---

### FR-OBS-040 — Bulkhead config validates partition count

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Bulkhead config must validate partition count.

**Traceability**
- Crate: `tracely-sentinel`
- tests/unit/tracely-sentinel/test_bulkhead_config_defaults.rs

---

### FR-OBS-041 — Sentinel config allows policy composition

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Sentinel config must allow composition of all policies.

**Traceability**
- Crate: `tracely-sentinel`
- tests/unit/tracely-sentinel/test_sentinel_config_composition.rs

---

### FR-OBS-042 — Config provides sensible defaults

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Config must provide sensible defaults for all parameters.

**Traceability**
- Crate: `tracely-sentinel`
- tests/unit/tracely-sentinel/test_config_all_defaults.rs

---

### FR-OBS-043 — Config serializable to/from TOML

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Config must be serializable to/from TOML.

**Traceability**
- Crate: `tracely-sentinel`
- tests/unit/tracely-sentinel/test_config_serialization.rs

---

## 7. Validation

### FR-OBS-044 — Validation rejects invalid log levels

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Validation must reject invalid log levels.

**Traceability**
- Crate: `tracely-sentinel`
- tests/unit/tracely-sentinel/test_validate_invalid_level.rs

---

### FR-OBS-045 — Validation accepts valid log levels

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Validation must accept valid log levels.

**Traceability**
- Crate: `tracely-sentinel`
- tests/unit/tracely-sentinel/test_validate_log_levels.rs

---

### FR-OBS-046 — Validation checks capacity constraints

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Validation must check capacity constraints.

**Traceability**
- Crate: `tracely-sentinel`
- tests/unit/tracely-sentinel/test_validate_capacity.rs

---

### FR-OBS-047 — Validation checks timeout constraints

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Validation must check timeout constraints.

**Traceability**
- Crate: `tracely-sentinel`
- tests/unit/tracely-sentinel/test_validate_timeout.rs

---

### FR-OBS-048 — Validation provides descriptive error messages

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Validation must provide descriptive error messages.

**Traceability**
- Crate: `tracely-sentinel`
- tests/unit/tracely-sentinel/test_validate_error_messages.rs

---

### FR-OBS-049 — Validation supports batch multi-field config checks

| Field | Value |
|-------|-------|
| **Status** | SHIPPED |

**Description** Validation must support batch checks for multi-field config.

**Traceability**
- Crate: `tracely-sentinel`
- tests/unit/tracely-sentinel/test_validate_batch.rs
