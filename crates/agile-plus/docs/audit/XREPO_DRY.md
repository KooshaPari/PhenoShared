# Cross-Repo DRY Audit — AgilePlus vs Tracera

> **Scope:** Read-only source analysis. No builds, tests, or git operations performed.
> **Date:** 2026-06-14
> **Repos:** `C:/Users/koosh/Dev/AgilePlus` (Rust) and `E:/Dev/Tracera` (Go/Python/Rust)
> **Target:** `phenoShared` workspace (`C:/Users/koosh/Dev/phenoShared`)

---

## 1. Executive Summary

| Category | AgilePlus | Tracera | Already in phenoShared | Extraction Candidate |
|----------|-----------|---------|----------------------|----------------------|
| Error types | 6+ enums (`DomainError`, `AppError`, `TriageError`, `TelemetryError`, `ConfigError`, `LoadError`) | 8+ custom structs (`ServiceUnavailableError`, `CircuitBreakerOpenError`, `ItemNotFoundError`, `RateLimitError`, `NotFoundError`, `ValidationError`, `ProtocolError`, `SyncError`) | `phenotype-error-core` (`ErrorCode`, `ErrorContext`, `ErrorEnvelope`, `ApiError`, `ConfigError`, `DomainError`, `RepositoryError`, `StorageError`) | **Yes — canonical `ErrorCode` projection** |
| Telemetry init | `agileplus-telemetry` (165 LOC) + `phenotype-logging` (29 LOC) | `internal/tracing` (9 files, ~700 LOC total) | `phenotype-logging` (stub) | **Yes — language-agnostic OTel init spec** |
| Config loading | `agileplus-config` macro (205 LOC) + `phenotype-config-core` (428 LOC) | `internal/config` (226 LOC) + `cmd/tracertm/config.go` (40 LOC) + `cmd/tracertm/env_validation.go` (202 LOC) | `phenotype-config-core` (`ConfigLoader`, `EnvConfig`, `FileConfig`, `merge_configs`) | **Yes — env-var helpers + validation** |
| Traceability model | `agileplus-trace-validator` (5 files, ~460 LOC) + `tracera-core` (shared) | `internal/traceability` (10 files, ~900 LOC) + `tracera-core` (122 LOC) | None | **Yes — `TraceLink`, `ArtifactRef`, coverage types** |

---

## 2. Error Types — HIGH PRIORITY

### 2.1 Current State

**AgilePlus (Rust)**
- `DomainError` — 14 variants (`NotFound`, `Validation`, `Storage`, `Conflict`, `InvalidTransition`, `LockPoisoned`, etc.)  
  `crates/agileplus-domain/src/error.rs:1-172`
- `AppError` — 3 variants (`Domain`, `NotFound`, `Storage`)  
  `crates/agileplus-application/src/error.rs:1-66`
- `TriageError` — 4 variants (`NoTicketAvailable`, `InvalidTicketId`, `TicketNotFound`, `Storage`)  
  `crates/agileplus-domain/src/ports.rs:107-117`
- `TelemetryError` — 3 variants (`Log`, `Config`, `Otel`)  
  `crates/agileplus-telemetry/src/adapter.rs:13-21`
- `ConfigError` — 3 variants (`Io`, `Yaml`, `Validation`)  
  `crates/agileplus-telemetry/src/config.rs:20-28`
- `LoadError` — 3 variants (`Walk`, `Read`, `Parse`)  
  `crates/agileplus-trace-validator/src/loaders.rs:8-22`
- `TraceLinkError` — 3 variants (`SelfLoop`, `BadConfidence`, `WrongArtifactKind`)  
  `E:/Dev/Tracera/crates/tracera-core/src/lib.rs:60-68`

**Tracera (Go)**
- `ServiceUnavailableError` — cross-service communication  
  `backend/internal/services/cross_service.go:32-44`
- `CircuitBreakerOpenError` — resilience pattern  
  `backend/internal/services/cross_service.go:52-65`
- `ItemNotFoundError` — domain lookup  
  `backend/internal/services/cross_service.go:68-80`
- `RateLimitError` — middleware  
  `backend/internal/middleware/ratelimit_middleware.go:282-290`
- `NotFoundError` — journey repository  
  `backend/internal/journey/repository.go:217-221`
- `ValidationError` — auth, equivalence, validation packages (3 separate definitions)  
  `backend/internal/auth/password.go:50`, `backend/internal/equivalence/import/validator.go:20`, `backend/internal/validation/validators.go:432-443`
- `ProtocolError` — agent protocol  
  `backend/internal/agents/protocol.go:443-447`
- `SyncError` — storybook  
  `backend/internal/storybook/types.go:186`

### 2.2 Duplication Analysis

Both repos independently classify errors into the same semantic families:

| Semantic Family | AgilePlus | Tracera | phenoShared Mapping |
|-----------------|-----------|---------|---------------------|
| Not found | `DomainError::NotFound`, `AppError::NotFound`, `TriageError::TicketNotFound` | `ItemNotFoundError`, `NotFoundError` | `ErrorCode::NotFound` |
| Validation | `DomainError::Validation`, `DomainError::InvalidTransition`, `DomainError::FeatureNotInModuleScope` | `ValidationError` (3 defs) | `ErrorCode::ValidationError` |
| Storage / Infrastructure | `DomainError::Storage`, `AppError::Storage`, `TriageError::Storage`, `LoadError` | `ServiceUnavailableError` | `ErrorCode::InternalError`, `StorageError` |
| Conflict / Already exists | `DomainError::Conflict`, `DomainError::ModuleHasDependents` | — | `ErrorCode::AlreadyExists` |
| Unauthenticated | — | — | `ErrorCode::Unauthenticated` |
| Rate limit | — | `RateLimitError` | `ErrorCode::ResourceExhausted` |

**`phenotype-error-core` already provides `ErrorCode` (26 variants) and layered error types (`ApiError`, `ConfigError`, `DomainError`, `RepositoryError`, `StorageError`).**

AgilePlus already projects `DomainError` and `AppError` onto `ErrorCode`:
- `crates/agileplus-domain/src/error.rs:64-88`
- `crates/agileplus-application/src/error.rs:33-40`

Tracera has **no equivalent** — its Go errors are entirely ad-hoc with no cross-language wire contract.

### 2.3 Extraction Recommendation

**Extract `phenotype-error-go` (or `phenotype-error-core/go` bindings)**
- Mirror `ErrorCode` as a Go string enum (or int enum)
- Provide `ErrorCodeClassifier` interface that Tracera's `ValidationError`, `ItemNotFoundError`, etc. can implement
- Re-use `ErrorEnvelope` JSON schema for HTTP responses across both repos

**Immediate:** Ensure every new error type in Tracera maps to `ErrorCode`.  
**Effort:** Medium (requires Go wrapper + contract test).  
**Impact:** High — unifies observability, error dashboards, and wire formats.

---

## 3. Telemetry Init — HIGH PRIORITY

### 3.1 Current State

**AgilePlus (Rust)**
- `init_subscriber()` — 68 LOC, OTLP gated on `OTEL_EXPORTER_OTLP_ENDPOINT` env var  
  `crates/agileplus-telemetry/src/lib.rs:38-105`
- `init_telemetry(config)` — 30 LOC, builds `TracerProvider` + `SdkMeterProvider`  
  `crates/agileplus-telemetry/src/adapter.rs:222-252`
- `TelemetryAdapter` — 158 LOC, implements `ObservabilityPort` with `tracing` + `opentelemetry`  
  `crates/agileplus-telemetry/src/adapter.rs:29-220`
- `TelemetryGuard` / `SubscriberGuard` — RAII shutdown  
  `crates/agileplus-telemetry/src/adapter.rs:23-27`, `crates/agileplus-telemetry/src/lib.rs:29-32`
- `phenotype-logging` — 29 LOC stub (`init_tracing`, `init_tracing_with_default`, `init_tracing_for_test`)  
  `phenoShared/crates/phenotype-logging/src/lib.rs:1-29`

**Tracera (Go)**
- `InitTracer(ctx, endpoint, env)` — 77 LOC, OTLP/gRPC exporter, batch span processor, sampler  
  `backend/internal/tracing/tracer.go:38-114`
- `TracerProvider` wrapper — 15 LOC (`Shutdown`, `ForceFlush`)  
  `backend/internal/tracing/tracer.go:117-152`
- Span helpers — 159 LOC (`StartSpan`, `RecordError`, `DatabaseSpan`, `HTTPSpan`, `CacheSpan`, `NATSSpan`, `GraphSpan`, `TemporalSpan`, `AIAgentSpan`, `SetHTTPStatus`, `SetUserID`, `SetProjectID`)  
  `backend/internal/tracing/helpers.go:21-178`
- Echo middleware — 4 LOC (`otelecho.Middleware`)  
  `backend/internal/tracing/middleware.go:9-10`
- `initTracing()` in infrastructure — 11 LOC, conditional on `cfg.TracingEnabled`  
  `backend/internal/infrastructure/infrastructure.go:235-246`

### 3.2 Duplication Analysis

Both repos implement the same OTel bootstrap pattern independently:

| Concern | AgilePlus Rust | Tracera Go |
|---------|----------------|------------|
| Endpoint from env | `OTEL_EXPORTER_OTLP_ENDPOINT` | `PHENO_OBSERVABILITY_OTLP_GRPC_ENDPOINT` / `OTLP_ENDPOINT` |
| Fallback when absent | stdout-only (no-op) | default `127.0.0.1:4317` |
| Service name hardcoded | `agileplus` | `tracertm-backend` |
| Sampler | always on when endpoint present | dev=always, prod=10% ratio |
| Batch span processor | `with_simple_exporter` (no batch) | `WithBatcher` + max batch size 512, max queue 2048 |
| Propagator | `TraceContext` + `Baggage` (W3C) | `TraceContext` + `Baggage` (W3C) |
| Shutdown | `Drop` on `TelemetryGuard` | explicit `Shutdown(ctx)` + `ForceFlush(ctx)` |
| Span kind helpers | `ObservabilityPort` trait | `DatabaseSpan`, `HTTPSpan`, `CacheSpan`, `NATSSpan`, `GraphSpan`, `TemporalSpan`, `AIAgentSpan` |

### 3.3 Extraction Recommendation

**Expand `phenotype-logging` to `phenotype-observability`**
- **Rust side:** Merge `agileplus-telemetry` span helpers, `TelemetryConfig`, and `ObservabilityPort` into a shared crate.  
  `phenotype-logging` is currently only 29 LOC — it is too small to be useful.
- **Go side:** Provide a `phenotype/observability` package that wraps `go.opentelemetry.io/otel` with:
  - `Init(serviceName, endpoint, env)` — one-liner bootstrap
  - `Span(ctx, kind, attrs)` — generic span helper
  - `DatabaseSpan`, `HTTPSpan`, `CacheSpan`, `NATSSpan` — semantically-typed helpers
  - `Shutdown(ctx)` — graceful flush

**Rationale:** Both repos spend 200+ LOC each on the exact same OTel lifecycle. The only differences are language idioms (RAII vs explicit `defer`) and hardcoded service names.

**Effort:** Medium (requires Go package + Rust crate expansion).  
**Impact:** High — eliminates OTel version mismatch risk, reduces bootstrap code to ~10 LOC per repo.

---

## 4. Config Loading — MEDIUM PRIORITY

### 4.1 Current State

**AgilePlus (Rust)**
- `config_builder!` macro — 60 LOC, generates `Default` + `with_*` setters  
  `crates/agileplus-config/src/lib.rs:30-89`
- `TelemetryConfig` — YAML + env override loader (`AGILEPLUS_LOG_LEVEL`, `AGILEPLUS_OTLP_ENDPOINT`)  
  `crates/agileplus-telemetry/src/config.rs:88-201`
- `EnvConfig` — prefixed env var scanner  
  `phenoShared/crates/phenotype-config-core/src/lib.rs:106-152`
- `FileConfig` — JSON/TOML/YAML loader with format detection  
  `phenoShared/crates/phenotype-config-core/src/lib.rs:156-226`
- `merge_configs()` — deep-merge multiple sources  
  `phenoShared/crates/phenotype-config-core/src/lib.rs:236-257`

**Tracera (Go)**
- `Config` struct — 64 fields, flat env var mapping  
  `backend/internal/config/config.go:22-116`
- `LoadConfig()` — 42 LOC, `getEnv` / `getEnvInt` / `getEnvBool` / `getEnvFloat` helpers  
  `backend/internal/config/config.go:119-226`
- `EnvConfig` — 40 fields, validation + connectivity checks  
  `backend/cmd/tracertm/config.go:5-40`
- `loadFromEnv()` — 162 LOC, per-section validation  
  `backend/cmd/tracertm/env_validation.go:13-202`

### 4.2 Duplication Analysis

Both repos read the same categories of env vars:

| Category | AgilePlus env vars | Tracera env vars |
|----------|-------------------|------------------|
| Server | `AGILEPLUS_*` | `PORT`, `GRPC_PORT`, `ENV` |
| Database | `DATABASE_URL` | `DATABASE_URL` |
| Redis | `REDIS_URL` | `REDIS_URL` |
| NATS | `NATS_URL` | `NATS_URL`, `NATS_CREDS`, `NATS_USER_JWT` |
| Tracing | `OTEL_EXPORTER_OTLP_ENDPOINT`, `AGILEPLUS_LOG_LEVEL` | `TRACING_ENABLED`, `TRACING_ENVIRONMENT`, `PHENO_OBSERVABILITY_OTLP_GRPC_ENDPOINT` |
| Security | `JWT_SECRET`, `CSRF_SECRET` | `JWT_SECRET`, `CSRF_SECRET` |
| S3 | `S3_*` | `S3_*` |
| WorkOS | `WORKOS_CLIENT_ID`, `WORKOS_API_KEY` | `WORKOS_CLIENT_ID`, `WORKOS_API_KEY` |

**Shared `phenotype-config-core` already provides `EnvConfig` (with prefix support), `FileConfig` (with format auto-detection), and `merge_configs()`.**

Tracera's Go code does not use these abstractions — it re-implements `getEnv`/`getEnvInt`/`getEnvBool`/`getEnvFloat` manually in `backend/internal/config/config.go:194-226`.

### 4.3 Extraction Recommendation

**Expand `phenotype-config-core` with a Go port**
- `EnvConfig` with prefix support (already exists in Rust, missing in Go)
- `FileConfig` with format detection (already exists in Rust, missing in Go)
- `ConfigValidator` trait / interface for validation rules (port range, URL format, etc.)
- Re-use `merge_configs` for layered config (env > file > default)

**Rationale:** Tracera's `cmd/tracertm/env_validation.go` (202 LOC) is almost entirely generic validation logic (port ranges, URL formats, host:port parsing). This is duplicated boilerplate.

**Effort:** Low-Medium (Go port of existing Rust logic).  
**Impact:** Medium — reduces config loading by ~150 LOC in Tracera.

---

## 5. Traceability Model — MEDIUM PRIORITY

### 5.1 Current State

**AgilePlus (Rust)**
- `TraceEntry` — JSON file format (`fr_id`, `spec_slug`, `spec_anchor`, `docs_pages`, `tests`, `code_modules`, `journeys`)  
  `crates/agileplus-trace-validator/src/lib.rs:6-15`
- `TraceDocument` — walkdir-discovered document (`id`, `kind`, `refs`, `path`)  
  `crates/agileplus-trace-validator/src/loaders.rs:25-30`
- `TraceDocumentKind` — `FunctionalRequirement`, `NonFunctionalRequirement`, `Test`, `Code`  
  `crates/agileplus-trace-validator/src/loaders.rs:33-38`
- `TraceGraph` / `TraceNode` — BTreeMap graph with duplicate detection  
  `crates/agileplus-trace-validator/src/graph.rs:6-63`
- `ValidationIssue` — `BrokenReference`, `DuplicateId`, `MissingTestCoverage`, `OrphanFunctionalRequirement`  
  `crates/agileplus-trace-validator/src/rules.rs:5-18`
- `TraceLink` / `ArtifactRef` / `TraceLinkType` — shared via `tracera-core`  
  `E:/Dev/Tracera/crates/tracera-core/src/lib.rs:38-82`

**Tracera (Go)**
- `Matrix` — project-level traceability matrix (`ProjectID`, `Requirements`, `TestCases`, `Links`, `Coverage`)  
  `backend/internal/traceability/types.go:6-13`
- `MatrixItem` — item in matrix (`ItemID`, `Title`, `Type`, `Status`, `TraceCount`)  
  `backend/internal/traceability/types.go:16-23`
- `Link` — relationship (`SourceID`, `TargetID`, `Type`, `Bidirectional`)  
  `backend/internal/traceability/types.go:26-31`
- `CoverageMetrics` — `TotalRequirements`, `TracedRequirements`, `CoveragePercent`, `UntracedItems`  
  `backend/internal/traceability/types.go:34-39`
- `CoverageReport` — `Overall`, `ByType`, `Recommendations`  
  `backend/internal/traceability/types.go:42-47`
- `GapAnalysis` — `MissingForward`, `MissingBackward`, `Orphaned`, `Recommendations`  
  `backend/internal/traceability/types.go:50-56`
- `ValidationReport` — `IsComplete`, `Score`, `Issues`  
  `backend/internal/traceability/types.go:75-82`
- `ValidationIssue` — `Severity`, `ItemID`, `Message`, `Suggestion`  
  `backend/internal/traceability/types.go:85-90`
- `ChangeImpact` — `DirectImpact`, `IndirectImpact`, `TestsToRun`, `DocsToUpdate`  
  `backend/internal/traceability/types.go:93-99`
- `TraceLink` / `ArtifactRef` / `TraceLinkType` — shared Rust crate (`tracera-core`)  
  `E:/Dev/Tracera/crates/tracera-core/src/lib.rs:38-82`

### 5.2 Duplication Analysis

The `tracera-core` Rust crate is **already shared** between both repos (it lives in Tracera but is referenced by AgilePlus). However, the Go side of Tracera re-implements the same concepts in a separate type system:

| Concept | Rust (shared) | Go (Tracera) |
|---------|---------------|--------------|
| Trace link | `TraceLink` (source_artifact_id, target_artifact_id, link_type, confidence) | `Link` (SourceID, TargetID, Type, Metadata) |
| Artifact | `ArtifactRef` (Requirement, Test, Code, Document) | `Item` (Type field: feature, task, bug, etc.) |
| Coverage | `TraceGraph::incoming_refs` + `has_test_coverage` | `CoverageMetrics` + `CoverageReport` |
| Validation | `ValidationIssue` (BrokenReference, DuplicateId, MissingTestCoverage, OrphanFunctionalRequirement) | `ValidationIssue` (Severity, ItemID, Message, Suggestion) |
| Gap analysis | `TraceGraph` orphan detection | `GapAnalysis` (MissingForward, MissingBackward, Orphaned) |
| Impact analysis | N/A in AgilePlus | `ChangeImpact` (DirectImpact, IndirectImpact, TestsToRun, DocsToUpdate) |

### 5.3 Extraction Recommendation

**Create `phenotype-traceability` crate (Rust) + `phenotype/traceability` package (Go)**
- **Core types:** `TraceLink`, `ArtifactRef`, `TraceLinkType`, `ArtifactKind` — already in `tracera-core`; move to `phenotype-traceability`
- **Coverage model:** `CoverageMetrics`, `CoverageReport`, `GapAnalysis` — merge Rust + Go logic into shared spec + bindings
- **Validation rules:** `TraceValidator` trait / interface with `BrokenReference`, `Orphan`, `MissingTestCoverage` rules
- **Impact analysis:** `ChangeImpact` — currently only in Tracera; port to Rust for AgilePlus reuse

**Rationale:** Tracera's `MatrixService` (452 LOC in `matrix_service.go`) and AgilePlus's `TraceGraph` + `ValidationIssue` (140 LOC in `graph.rs` + `rules.rs`) are solving the same problem with different data structures. A unified `TraceGraph` trait with Rust + Go implementations would allow both repos to share coverage algorithms.

**Effort:** High (requires unified data model + language bindings).  
**Impact:** Medium-High — eliminates drift between traceability models.

---

## 6. Additional Candidates — LOW PRIORITY

### 6.1 Retry / Backoff

- **Tracera:** `RetryWithBackoff` in `backend/internal/services/cross_service.go:231-272` (42 LOC) + `RetryConfig` struct
- **AgilePlus:** No explicit retry abstraction found in domain/telemetry crates
- **Recommendation:** Extract to `phenotype-resilience` (Rust + Go) if AgilePlus adds retry logic.

### 6.2 Circuit Breaker

- **Tracera:** `CircuitBreaker` in `backend/internal/services/cross_service.go:424-480` (57 LOC)
- **AgilePlus:** No circuit breaker found
- **Recommendation:** Wait until AgilePlus needs it; then extract to `phenotype-resilience`.

### 6.3 Rate Limiting

- **Tracera:** `RateLimitMiddleware` (260 LOC) + `SlidingWindowLimiter` (not examined in detail)
- **AgilePlus:** No rate limiting found
- **Recommendation:** Not a candidate for extraction unless AgilePlus adopts the same middleware.

### 6.4 Cross-Service Communication Helpers

- **Tracera:** `ValidateItemExists`, `GetItemWithFallback`, `BulkItemValidation`, `ValidateAllItemsExist`, `GetMultipleItems`, `ValidateLinkCompatibility`, `GetItemsByProject` (175 LOC)  
  `backend/internal/services/cross_service.go:88-417`
- **AgilePlus:** No equivalent helpers found
- **Recommendation:** Not a candidate — domain-specific to Tracera's item/link model.

---

## 7. phenoShared Workspace — Already Shared Assets

| Crate | LOC | Used by AgilePlus | Used by Tracera | Maturity |
|-------|-----|-------------------|-----------------|----------|
| `phenotype-error-core` | ~200 | Yes (`ErrorCode` projection) | No | **Mature** |
| `phenotype-logging` | 29 | Yes (`init_tracing`) | No | **Stub — needs expansion** |
| `phenotype-config-core` | 428 | Yes (`EnvConfig`, `FileConfig`, `merge_configs`) | No | **Mature** |
| `tracera-core` | 122 | Yes (trace-link types) | Yes (trace-link types) | **Shared but lives in Tracera** |

### 7.1 Recommendation: Move `tracera-core` into `phenoShared`

`tracera-core` is currently a crate inside `E:/Dev/Tracera/crates/tracera-core`. It is the **only** code already shared between both repos. It should be moved to `phenoShared/crates/phenotype-traceability-core` (or similar) so it is not owned by either repo.

---

## 8. Implementation Priority

| Priority | Task | Effort | Impact | First Step |
|----------|------|--------|--------|------------|
| **P0** | Expand `phenotype-logging` to `phenotype-observability` (Rust + Go) | Medium | High | Write unified OTel init spec |
| **P0** | Port `ErrorCode` projection to Tracera Go | Medium | High | Create `phenotype-error-go` package |
| **P1** | Port `phenotype-config-core` to Go | Low-Medium | Medium | Extract `EnvConfig` + `FileConfig` + validation |
| **P1** | Move `tracera-core` into `phenoShared` | Low | Medium | Relocate crate, update both `Cargo.toml` references |
| **P1** | Expand `tracera-core` to full `phenotype-traceability` (coverage + validation) | High | Medium-High | Design unified `TraceGraph` trait |
| **P2** | Extract `RetryWithBackoff` + `CircuitBreaker` to `phenotype-resilience` | Medium | Low-Medium | Wait for AgilePlus adoption |

---

## 9. File Counts & Lines of Code

### AgilePlus (relevant files)

| File | Lines | Language |
|------|-------|----------|
| `crates/agileplus-domain/src/error.rs` | 172 | Rust |
| `crates/agileplus-application/src/error.rs` | 66 | Rust |
| `crates/agileplus-telemetry/src/lib.rs` | 165 | Rust |
| `crates/agileplus-telemetry/src/adapter.rs` | 350 | Rust |
| `crates/agileplus-telemetry/src/config.rs` | 271 | Rust |
| `crates/agileplus-config/src/lib.rs` | 205 | Rust |
| `crates/agileplus-trace-validator/src/lib.rs` | 159 | Rust |
| `crates/agileplus-trace-validator/src/graph.rs` | 82 | Rust |
| `crates/agileplus-trace-validator/src/rules.rs` | 98 | Rust |
| `crates/agileplus-trace-validator/src/loaders.rs` | 150 | Rust |
| `phenoShared/crates/phenotype-error-core/src/lib.rs` | 15 | Rust |
| `phenoShared/crates/phenotype-error-core/src/code.rs` | 94 | Rust |
| `phenoShared/crates/phenotype-logging/src/lib.rs` | 29 | Rust |
| `phenoShared/crates/phenotype-config-core/src/lib.rs` | 428 | Rust |

**Total AgilePlus relevant LOC:** ~2,294

### Tracera (relevant files)

| File | Lines | Language |
|------|-------|----------|
| `backend/internal/tracing/tracer.go` | 152 | Go |
| `backend/internal/tracing/helpers.go` | 178 | Go |
| `backend/internal/tracing/middleware.go` | 11 | Go |
| `backend/internal/tracing/context.go` | ~50 | Go |
| `backend/internal/tracing/database.go` | ~30 | Go |
| `backend/internal/tracing/grpc.go` | ~60 | Go |
| `backend/internal/config/config.go` | 226 | Go |
| `backend/cmd/tracertm/config.go` | 40 | Go |
| `backend/cmd/tracertm/env_validation.go` | 202 | Go |
| `backend/internal/traceability/types.go` | 99 | Go |
| `backend/internal/traceability/matrix_service.go` | 452 | Go |
| `backend/internal/traceability/matrix_logic.go` | 76 | Go |
| `backend/internal/services/cross_service.go` | 500 | Go |
| `backend/internal/middleware/ratelimit_middleware.go` | 328 | Go |
| `crates/tracera-core/src/lib.rs` | 122 | Rust |

**Total Tracera relevant LOC:** ~2,526

---

## 10. Conclusion

Both repos independently implement ~2,500 LOC of overlapping infrastructure:

1. **Error classification** — Both classify errors into the same 5-6 semantic families. `phenotype-error-core` already solves this for Rust; Tracera Go needs a port.
2. **Telemetry bootstrap** — Both use OpenTelemetry OTLP with nearly identical configuration (endpoint, sampler, propagator, batch processor). `phenotype-logging` is a 29-line stub; it should be expanded to a full `phenotype-observability` crate.
3. **Config loading** — Both read the same env vars (PORT, DATABASE_URL, REDIS_URL, NATS_URL, OTEL endpoint, JWT_SECRET, etc.). `phenotype-config-core` already has the Rust abstractions; Tracera Go re-implements them manually.
4. **Traceability model** — `tracera-core` is already shared but lives in Tracera. It should be moved to `phenoShared` and expanded to include coverage + validation types.

**The highest-impact, lowest-effort wins are:**
1. Expand `phenotype-logging` to `phenotype-observability` (unifies OTel init)
2. Port `ErrorCode` to Go (unifies error dashboards)
3. Port `phenotype-config-core` to Go (eliminates env-validation boilerplate)

---

*End of audit.*
