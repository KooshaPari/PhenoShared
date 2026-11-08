# logctx Product Requirements Document

**Document ID:** PHENOTYPE_LOGCTX_PRD_001  
**Version:** 1.0.0  
**Status:** Approved  
**Last Updated:** 2026-04-05  
**Author:** Phenotype Product Team  
**Stakeholders:** Backend Engineering, Platform Teams, DevOps

---

## 1. Executive Summary

### 1.1 Product Vision

logctx provides a production-grade, context-based logger storage system for Go applications using the standard log/slog package. It enables seamless propagation of structured loggers through Go's context.Context, ensuring request-scoped fields are automatically included in all log output without manual logger passing.

### 1.2 Mission Statement

To eliminate the boilerplate and context-loss issues of traditional logging by storing structured loggers in Go's context tree, enabling zero-allocation retrieval and automatic field propagation across function boundaries.

### 1.3 Key Value Propositions

| Value Proposition | Description | Business Impact |
|-------------------|-------------|-----------------|
| **Zero Dependencies** | Standard library only | Minimal supply chain risk |
| **Zero-Allocation** | Optimized hot path | Production performance |
| **Panic-on-Missing** | Fail-fast for bugs | Catch issues early |
| **Middleware Ready** | HTTP/gRPC support | Easy integration |
| **Immutable Safety** | Thread-safe by design | Concurrent safety |
| **slog Native** | Built for Go 1.21+ | Future-proof |

### 1.4 Positioning Statement

For Go developers building concurrent applications, logctx is the logging utility that eliminates logger parameter passing while maintaining thread safety, unlike traditional approaches that require passing loggers through every function call or risk context loss.

---

## 2. Problem Statement

### 2.1 Current Pain Points

#### 2.1.1 Logger Passing Overhead

Traditional Go logging approaches create significant boilerplate:

```go
// Traditional approach - logger passed everywhere
func handleRequest(w http.ResponseWriter, r *http.Request, logger *slog.Logger) {
    logger.Info("handling request", "path", r.URL.Path)
    result, err := processData(r.Context(), logger, r.Body)
    if err != nil {
        logger.Error("processing failed", "error", err)
        return
    }
    // ... logger passed through entire call chain
}

func processData(ctx context.Context, logger *slog.Logger, body io.Reader) (Result, error) {
    logger.Debug("processing data")
    // ... logger passed to every helper
}
```

Problems with this approach:
- **Function signature pollution**: Every function needs logger parameter
- **Refactoring burden**: Adding logging requires changing many signatures
- **Testing complexity**: Mocking loggers as parameters adds test overhead
- **Inconsistent usage**: Some functions omit logger, losing log context

#### 2.1.2 Context Loss at Boundaries

When crossing API boundaries (HTTP, gRPC, channels), logger context is frequently lost:

```go
// Logger context lost when spawning goroutine
func handler(logger *slog.Logger) {
    go func() {
        // Logger not available here!
        processAsync()
    }()
}
```

#### 2.1.3 Inconsistent Field Application

Request identifiers and other contextual fields are inconsistently applied:

- Some log entries have request_id, others don't
- User ID may be present in some logs but missing in others
- Trace correlation requires manual field addition at each log site

#### 2.1.4 Global Logger Anti-Pattern

Using global loggers avoids parameter passing but introduces other issues:

- **No request context**: Can't correlate logs by request
- **Race conditions**: Concurrent modifications unsafe
- **Testing difficulty**: Global state hard to mock
- **Configuration complexity**: Changing settings affects all loggers

### 2.2 Use Cases

#### 2.2.1 HTTP Request Handling

Middleware injects request-scoped logger with automatic request ID, user ID, and path context. All downstream handlers log with these fields automatically.

#### 2.2.2 gRPC Services

Interceptor adds trace context and method information. Service implementations retrieve logger from context without parameter changes.

#### 2.2.3 Background Workers

Job metadata (job ID, queue name, attempt count) stored in context propagates through job processing pipeline.

#### 2.2.4 Event-Driven Systems

Event correlation IDs flow through event handlers via context, enabling end-to-end traceability.

### 2.3 Market Analysis

| Solution | Approach | Strengths | Weaknesses |
|----------|----------|-----------|------------|
| **logctx** | Context storage | Zero deps, slog native | Go 1.21+ only |
| **zap ctx** | Context wrapper | Mature, fast | Zap dependency |
| **logr** | Interface based | Kubernetes standard | Extra interface layer |
| **zerolog ctx** | Context wrapper | High performance | Zerolog dependency |
| **Manual passing** | Parameter | Explicit, simple | Verbose, error-prone |

---

## 3. Target Users and Personas

### 3.1 Primary Personas

#### 3.1.1 Backend Engineer Ben

**Demographics**: Go developer, 2-5 years experience, building web services
**Goals**:
- Add structured logging to services
- Correlate logs by request
- Keep function signatures clean
- Maintain high performance

**Pain Points**:
- Frustrated with logger parameter passing
- Wants request ID in all logs automatically
- Needs thread-safe solution
- Values simplicity over features

**Technical Profile**:
- Uses Go 1.21+ for slog
- Building HTTP APIs with net/http or Gin
- Wants minimal dependencies
- Performance-conscious

**Quote**: "I just want to call `slog.Info()` and have the request ID already there without passing it through 10 function calls."

#### 3.1.2 Platform Engineer Priya

**Demographics**: Platform/Infrastructure engineer, 5+ years experience
**Goals**:
- Standardize logging across organization
- Ensure security (no secrets in logs)
- Enable log correlation for debugging
- Minimize supply chain risk

**Pain Points**:
- Fragmented logging approaches across teams
- Concerned about dependency bloat
- Needs audit trail capabilities
- Wants consistent log format

**Technical Profile**:
- Defines organizational standards
- Reviews code for best practices
- Security-focused
- Values maintainability

**Quote**: "We need a logging approach that's consistent, secure, and doesn't add dependencies that could become vulnerabilities."

### 3.2 Secondary Personas

#### 3.2.1 DevOps Engineer Dave

- Consumes logs in observability platform
- Needs structured logs for parsing
- Sets up log aggregation pipelines

#### 3.2.2 SRE Sally

- Debugs production issues
- Correlates logs across services
- Builds dashboards and alerts

### 3.3 User Segmentation

| Segment | Size | Primary Need |
|---------|------|--------------|
| HTTP API developers | 40% | Middleware integration |
| Microservices developers | 30% | Cross-service context |
| Library authors | 15% | Clean API design |
| CLI tool developers | 10% | Simple structured logging |
| Other | 5% | Various |

---

## 4. Functional Requirements

### 4.1 Core API (FR-CA)

#### FR-CA-001: Logger Storage

**Requirement**: Store and retrieve loggers from context

**Priority**: P0 - Critical

**Description**: Provide functions to store a slog.Logger in a context.Context and retrieve it later with fail-fast semantics for developer experience.

**API Specification**:
```go
// WithLogger stores a logger in the context and returns the new context
func WithLogger(ctx context.Context, logger *slog.Logger) context.Context

// From retrieves the logger from context, panicking if not found
// Use for code paths where logger MUST be present
func From(ctx context.Context) *slog.Logger

// FromOk retrieves the logger, returning ok=false if not found
// Use for optional logging or graceful degradation
func FromOk(ctx context.Context) (*slog.Logger, bool)
```

**Acceptance Criteria**:
1. [ ] WithLogger creates new context node with logger stored
2. [ ] From retrieves stored logger without modification
3. [ ] From panics if no logger in context (fail-fast for bugs)
4. [ ] FromOk returns nil, false if no logger present
5. [ ] Zero-allocation retrieval path (no heap allocations)
6. [ ] Thread-safe concurrent access
7. [ ] No logger modification (immutable pattern)

**Performance Targets**:
| Operation | Target |
|-----------|--------|
| WithLogger | <100ns |
| From | <50ns |
| FromOk | <50ns |
| Allocations | 0 |

#### FR-CA-002: Context Enhancement

**Requirement**: Add fields to logger in context

**Priority**: P1 - High

**Description**: Provide utilities to add attributes to a logger and store the enhanced logger back in context, creating immutable copies.

**API Specification**:
```go
// WithField adds a single key-value pair to the logger in context
func WithField(ctx context.Context, key string, value any) context.Context

// WithFields adds multiple attributes to the logger in context
func WithFields(ctx context.Context, attrs ...slog.Attr) context.Context

// WithGroup creates a nested logger group in context
func WithGroup(ctx context.Context, name string) context.Context
```

**Acceptance Criteria**:
1. [ ] WithField adds single attribute to logger
2. [ ] WithFields adds multiple attributes efficiently
3. [ ] WithGroup creates namespaced attribute group
4. [ ] All methods return new context (immutability)
5. [ ] Original context unchanged
6. [ ] Chainable calls work correctly

**Usage Example**:
```go
// Middleware adds request context
func middleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        logger := slog.With("request_id", generateID())
        ctx := logctx.WithLogger(r.Context(), logger)
        next.ServeHTTP(w, r.WithContext(ctx))
    })
}

// Handler adds user context
func handler(w http.ResponseWriter, r *http.Request) {
    ctx := logctx.WithField(r.Context(), "user_id", getUserID(r))
    processRequest(ctx)
}

// Deep in call stack, logger has all fields
func processRequest(ctx context.Context) {
    logctx.From(ctx).Info("processing") 
    // Output: {"msg":"processing","request_id":"abc","user_id":"123"}
}
```

#### FR-CA-003: Logger Creation Helpers

**Requirement**: Convenience functions for common logger configurations

**Priority**: P2 - Medium

**API Specification**:
```go
// NewLogger creates a logger with standard configuration
func NewLogger(w io.Writer, opts ...LoggerOption) *slog.Logger

// WithJSON configures JSON output
func WithJSON() LoggerOption

// WithLevel configures minimum log level
func WithLevel(level slog.Level) LoggerOption

// WithSource includes source file/line
func WithSource() LoggerOption
```

### 4.2 Middleware (FR-MW)

#### FR-MW-001: HTTP Middleware

**Requirement**: Automatic logger injection for HTTP handlers

**Priority**: P1 - High

**Description**: Provide ready-to-use HTTP middleware that injects configured loggers with request-scoped fields.

**API Specification**:
```go
// HTTPMiddleware creates logging middleware
func HTTPMiddleware(opts ...HTTPMiddlewareOption) func(http.Handler) http.Handler

// Middleware options
func WithRequestIDHeader(header string) HTTPMiddlewareOption
func WithUserIDFunc(fn func(*http.Request) string) HTTPMiddlewareOption
func WithStaticFields(attrs ...slog.Attr) HTTPMiddlewareOption
```

**Acceptance Criteria**:
1. [ ] Middleware injects logger into request context
2. [ ] Automatic request ID generation (UUID or custom)
3. [ ] Request ID extraction from header (configurable)
4. [ ] User ID extraction via callback function
5. [ ] Static field injection (service name, version)
6. [ ] Request ID echoed in response header
7. [ ] Compatible with net/http and popular frameworks

**Injected Fields**:
| Field | Source | Example |
|-------|--------|---------|
| request_id | Generated or from header | "550e8400-e29b-41d4-a716-446655440000" |
| http.method | Request | "GET" |
| http.path | Request URL | "/api/users" |
| http.host | Request Host | "api.example.com" |
| user_id | Callback | "user-123" |
| service | Static config | "user-service" |

#### FR-MW-002: gRPC Interceptor

**Requirement**: Logger injection for gRPC services

**Priority**: P1 - High

**Description**: Provide unary and streaming interceptors for gRPC that inject loggers with method and trace context.

**API Specification**:
```go
// UnaryServerInterceptor creates a gRPC unary interceptor
func UnaryServerInterceptor(opts ...GRPCInterceptorOption) grpc.UnaryServerInterceptor

// StreamServerInterceptor creates a gRPC streaming interceptor
func StreamServerInterceptor(opts ...GRPCInterceptorOption) grpc.StreamServerInterceptor
```

**Acceptance Criteria**:
1. [ ] Unary server interceptor with logger injection
2. [ ] Stream server interceptor with logger injection
3. [ ] Metadata extraction for trace IDs
4. [ ] Method name extraction (service/method)
5. [ ] Peer address logging
6. [ ] Compatible with grpc-go

**Injected Fields**:
| Field | Source |
|-------|--------|
| rpc.method | Full method name |
| rpc.service | Service name |
| trace_id | From metadata |
| peer.address | Client address |

### 4.3 Utilities (FR-UT)

#### FR-UT-001: Logging Helpers

**Requirement**: Convenience functions for common logging patterns

**Priority**: P2 - Medium

**API Specification**:
```go
// Debug logs at Debug level from context logger
func Debug(ctx context.Context, msg string, attrs ...slog.Attr)

// Info logs at Info level from context logger
func Info(ctx context.Context, msg string, attrs ...slog.Attr)

// Warn logs at Warn level from context logger
func Warn(ctx context.Context, msg string, attrs ...slog.Attr)

// Error logs at Error level from context logger
func Error(ctx context.Context, msg string, err error, attrs ...slog.Attr)
```

**Acceptance Criteria**:
1. [ ] All helper functions use logger from context
2. [ ] Panic if no logger in context (for Error)
3. [ ] Consistent with slog API patterns
4. [ ] Error helper includes error attribute automatically

#### FR-UT-002: Context Extraction

**Requirement**: Extract logging context from standard context values

**Priority**: P2 - Medium

**API Specification**:
```go
// ExtractTraceID extracts trace ID from OpenTelemetry context
func ExtractTraceID(ctx context.Context) string

// ExtractSpanID extracts span ID from OpenTelemetry context
func ExtractSpanID(ctx context.Context) string

// WithTraceFields adds trace fields from OTel context
func WithTraceFields(ctx context.Context) context.Context
```

---

## 5. Non-Functional Requirements

### 5.1 Performance

#### 5.1.1 Latency Targets

| Operation | p50 | p99 | Max |
|-----------|-----|-----|-----|
| From retrieval | 20ns | 50ns | 100ns |
| WithLogger storage | 50ns | 100ns | 200ns |
| WithField enhancement | 100ns | 200ns | 500ns |
| HTTP middleware injection | 500ns | 1μs | 2μs |

#### 5.1.2 Memory Targets

| Metric | Target |
|--------|--------|
| Retrieval allocations | 0 |
| Storage allocations | 1 (context node) |
| Enhancement allocations | 1 (logger copy) |
| Per-request overhead | <1KB |

#### 5.1.3 Concurrency

- Thread-safe for all operations
- No locks on retrieval hot path
- Immutable patterns throughout
- Safe for high-concurrency services (>10K req/sec)

### 5.2 Safety

#### 5.2.1 Panic Behavior

| Function | Missing Logger Behavior | Rationale |
|----------|------------------------|-----------|
| From | Panic | Catch bugs early |
| FromOk | Return nil, false | Safe for optional |
| Helpers | Panic | Fail fast |

#### 5.2.2 Error Handling

- No logger in context = programming error (panic)
- Invalid attributes = slog handles (no panic)
- Nil context = panic (Go standard)

### 5.3 Compatibility

#### 5.3.1 Go Version Support

| Version | Support | Notes |
|---------|---------|-------|
| 1.23+ | Primary | Latest features |
| 1.22 | Supported | Full features |
| 1.21 | Supported | Minimum for slog |
| <1.21 | Not supported | Use x/exp/slog |

#### 5.3.2 slog Compatibility

- 100% compatible with stdlib slog
- Works with slog.Handler implementations
- No wrapper types (native *slog.Logger)

### 5.4 Security

#### 5.4.1 Data Protection

- No sensitive data in context keys
- Logger attributes may contain sensitive data (user responsibility)
- No logging of context internals

#### 5.4.2 Supply Chain

- Zero external dependencies
- Standard library only
- Minimal attack surface

---

## 6. User Stories

### 6.1 Primary User Stories

#### US-001: Basic Context Logging

**As a** backend engineer  
**I want** to store a logger in context  
**So that** I can retrieve it without passing as parameter

**Acceptance Criteria**:
- Given a context with logger stored via WithLogger
- When I call logctx.From(ctx)
- Then I receive the exact same logger
- And it has all configured fields
- And retrieval is zero-allocation

**Priority**: P0

#### US-002: Request Tracing

**As a** backend engineer  
**I want** request IDs in all logs  
**So that** I can trace requests through the system

**Acceptance Criteria**:
- Given HTTP middleware applied to my handlers
- When a request arrives
- Then the logger in context has request_id field
- And all downstream logs include the request_id
- Even in goroutines spawned from the handler

**Priority**: P0

#### US-003: Field Enhancement

**As a** backend engineer  
**I want** to add fields as I process a request  
**So that** deeper logs have more context

**Acceptance Criteria**:
- Given a context with a logger
- When I call WithField or WithFields
- Then the returned context has enhanced logger
- And the original context is unchanged
- And the new fields appear in subsequent logs

**Priority**: P1

#### US-004: Fail-Fast Debugging

**As a** backend engineer  
**I want** panics when logger is missing  
**So that** I catch configuration bugs early

**Acceptance Criteria**:
- Given a context without a logger
- When I call logctx.From(ctx)
- Then it panics with clear error message
- Identifying which code path forgot to set up logging

**Priority**: P1

### 6.2 Secondary User Stories

#### US-005: gRPC Logging

**As a** microservices developer  
**I want** automatic logging in gRPC services  
**So that** I can debug RPC calls

**Priority**: P1

#### US-006: Safe Optional Logging

**As a** library author  
**I want** optional logging that doesn't panic  
**So that** my library works without logger setup

**Priority**: P2

#### US-007: Framework Integration

**As a** framework developer  
**I want** easy integration with my framework  
**So that** users get logging automatically

**Priority**: P2

---

## 7. Feature Specifications

### 7.1 Context Key Design

```go
// Internal context key type (unexported for safety)
type loggerKey struct{}

var activeLoggerKey = loggerKey{}

// WithLogger implementation
func WithLogger(ctx context.Context, logger *slog.Logger) context.Context {
    return context.WithValue(ctx, activeLoggerKey, logger)
}

// From implementation
func From(ctx context.Context) *slog.Logger {
    logger, ok := ctx.Value(activeLoggerKey).(*slog.Logger)
    if !ok || logger == nil {
        panic("logctx: no logger in context")
    }
    return logger
}
```

### 7.2 Middleware Implementation

```go
func HTTPMiddleware(opts ...HTTPMiddlewareOption) func(http.Handler) http.Handler {
    config := defaultMiddlewareConfig()
    for _, opt := range opts {
        opt(&config)
    }
    
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            requestID := r.Header.Get(config.requestIDHeader)
            if requestID == "" {
                requestID = generateRequestID()
            }
            
            logger := config.baseLogger.With(
                slog.String("request_id", requestID),
                slog.String("http.method", r.Method),
                slog.String("http.path", r.URL.Path),
                slog.String("http.host", r.Host),
            )
            
            if config.userIDFunc != nil {
                if userID := config.userIDFunc(r); userID != "" {
                    logger = logger.With(slog.String("user_id", userID))
                }
            }
            
            ctx := WithLogger(r.Context(), logger)
            w.Header().Set(config.requestIDHeader, requestID)
            
            next.ServeHTTP(w, r.WithContext(ctx))
        })
    }
}
```

---

## 8. Success Metrics

### 8.1 Adoption Metrics

| Metric | Target | Timeline | Measurement |
|--------|--------|----------|-------------|
| pkg.go.dev downloads | 50K | 6 months | pkg.go.dev |
| GitHub stars | 300 | 6 months | GitHub API |
| Known production users | 20 | 12 months | Surveys |
| Middleware integrations | 5 | 6 months | Ecosystem |

### 8.2 Quality Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Test coverage | >95% | Codecov |
| Benchmark compliance | Pass | go test -bench |
| Zero-allocation verified | Yes | Benchmark mem allocs |
| Panic scenarios tested | 100% | Unit tests |
| Race detector clean | Yes | go test -race |

### 8.3 Performance Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| From retrieval | <50ns | Benchmark |
| WithLogger storage | <100ns | Benchmark |
| Middleware overhead | <1μs | Benchmark |
| Memory per request | <1KB | Heap profiling |

---

## 9. Release Criteria

### 9.1 MVP (v0.1.0)

**Goal**: Core functionality for early adopters

**Requirements**:
- [ ] Core WithLogger/From/FromOk API
- [ ] Panic-on-missing behavior with clear messages
- [ ] HTTP middleware with request ID
- [ ] Basic documentation with examples
- [ ] Unit tests >90% coverage

**Success Criteria**:
- Zero-allocation retrieval verified by benchmarks
- Panic includes helpful error message
- Middleware works with net/http
- Examples compile and run

### 9.2 Beta (v0.5.0)

**Goal**: Production-ready with more integrations

**Requirements**:
- [ ] gRPC interceptors (unary and stream)
- [ ] Context enhancement helpers (WithField, WithFields, WithGroup)
- [ ] Helper functions (Debug, Info, Warn, Error)
- [ ] Comprehensive documentation
- [ ] Race detector clean
- [ ] Production usage guide

### 9.3 Production (v1.0.0)

**Goal**: Stable, widely adopted release

**Requirements**:
- [ ] All P0/P1 functional requirements
- [ ] Framework integrations (Gin, Echo, Fiber examples)
- [ ] OpenTelemetry trace correlation
- [ ] Performance benchmarks published
- [ ] Production runbook
- [ ] Security review passed

---

## 10. Implementation Details

### 10.1 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Application Layer                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   HTTP       │  │   gRPC       │  │   Background │         │
│  │   Handler    │  │   Handler    │  │   Worker     │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
└─────────┼─────────────────┼─────────────────┼───────────────────┘
          │                 │                 │
          ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Middleware Layer                            │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Inject logger with contextual fields                 │  │
│  │  - Request ID                                         │  │
│  │  - User ID                                            │  │
│  │  - Service metadata                                   │  │
│  └─────────────────────────┬─────────────────────────────┘  │
└────────────────────────────┼──────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Context Storage                             │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  context.WithValue(ctx, loggerKey, logger)            │  │
│  │                                                         │  │
│  │  Zero-allocation retrieval:                             │  │
│  │  ctx.Value(loggerKey).(*slog.Logger)                 │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Retrieval & Usage                           │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  logctx.From(ctx) → *slog.Logger                        │  │
│  │  logger.Info("message", "key", value)                  │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 10.2 Key Design Decisions

| Decision | Rationale | Trade-off |
|----------|-----------|-----------|
| Context storage | Go idiomatic, thread-safe | Requires context propagation |
| Panic on missing | Fail fast, catch bugs early | Requires proper setup |
| slog native | Standard library, future-proof | Go 1.21+ required |
| Zero dependencies | Security, minimal footprint | No advanced features |
| Immutable loggers | Thread safety | Logger copies on enhancement |

### 10.3 Context Key Safety

```go
// Private type ensures no collisions with other packages
type loggerKey struct{}

// Singleton key instance
var key = loggerKey{}

// This approach:
// 1. Prevents external packages from accessing our values
// 2. Guarantees no key collisions
// 3. Allows type assertion without string parsing
```

---

## 11. Testing Strategy

### 11.1 Test Categories

| Category | Coverage Target | Focus |
|----------|-----------------|-------|
| Unit | 95% | Core API, edge cases |
| Integration | 80% | Middleware, interceptors |
| Performance | N/A | Benchmarks, allocations |
| Race | Clean | Concurrent access patterns |

### 11.2 Test Scenarios

1. **Basic storage/retrieval**: Store logger, retrieve unchanged
2. **Missing logger**: From panics, FromOk returns false
3. **Concurrent access**: Multiple goroutines, no races
4. **Context chains**: Multiple WithLogger calls, correct isolation
5. **Middleware**: Request ID generation, field injection
6. **Enhancement**: WithField creates new logger, old unchanged

### 11.3 Benchmarks

```go
func BenchmarkFrom(b *testing.B) {
    ctx := WithLogger(context.Background(), slog.Default())
    b.ResetTimer()
    b.ReportAllocs()
    
    for i := 0; i < b.N; i++ {
        _ = From(ctx)
    }
}

func BenchmarkFromParallel(b *testing.B) {
    ctx := WithLogger(context.Background(), slog.Default())
    b.ResetTimer()
    b.ReportAllocs()
    
    b.RunParallel(func(pb *testing.PB) {
        for pb.Next() {
            _ = From(ctx)
        }
    })
}
```

---

## 12. Deployment and Operations

### 12.1 Setup Checklist

- [ ] Add logctx to go.mod
- [ ] Set up HTTP middleware (if applicable)
- [ ] Set up gRPC interceptors (if applicable)
- [ ] Configure base logger with service name
- [ ] Test retrieval in handler
- [ ] Verify request IDs in logs
- [ ] Run race detector in CI

### 12.2 Operational Runbook

**Missing Logger Panics**:
1. Check that middleware is applied to all routes
2. Verify WithLogger called before From
3. Look for context cancellation issues
4. Check for goroutine boundary issues

**High Memory Usage**:
1. Check for context retention (leaks)
2. Verify logger isn't storing large objects
3. Review WithField usage (creates copies)

**Performance Issues**:
1. Run benchmarks to verify targets
2. Check for unnecessary WithField calls
3. Verify zero-allocation retrieval

---

## 13. Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Panic in production | High | Medium | Clear documentation, FromOk alternative |
| Memory leaks | Medium | Low | Context lifecycle testing |
| slog API changes | Low | Low | Standard library stability |
| Performance regression | Medium | Low | Benchmarks in CI |
| Context key collision | Low | Low | Private key type |

---

## 14. Future Roadmap

### 14.1 v1.1.0 (Near-term)

- [ ] Additional framework middleware (Gin, Echo, Fiber)
- [ ] OpenTelemetry span correlation helpers
- [ ] Dynamic log level changes
- [ ] Log sampling utilities

### 14.2 v2.0.0 (Long-term)

- [ ] Structured error wrapping with log context
- [ ] Log correlation across async boundaries
- [ ] Automatic sensitive data filtering
- [ ] Custom handler support

---

## 15. Appendix

### 15.1 Glossary

| Term | Definition |
|------|------------|
| **Context** | Go's request-scoped value storage |
| **slog** | Go 1.21+ structured logging package |
| **Middleware** | HTTP/gRPC request interceptor |
| **Fail-fast** | Panic on error to catch bugs early |
| **Zero-allocation** | No heap allocations in hot path |

### 15.2 References

- [Go slog package](https://pkg.go.dev/log/slog)
- [Context package](https://pkg.go.dev/context)
- [Middleware patterns](https://drstearns.github.io/tutorials/gomiddleware/)

### 15.3 Migration Guide

**From manual passing**:
```go
// Before
func handle(w http.ResponseWriter, r *http.Request) {
    logger := slog.With("request_id", id)
    process(r.Context(), logger, data)
}

func process(ctx context.Context, logger *slog.Logger, data Data) {
    logger.Info("processing")
}

// After
func handle(w http.ResponseWriter, r *http.Request) {
    ctx := logctx.WithLogger(r.Context(), logger)
    process(ctx, data)
}

func process(ctx context.Context, data Data) {
    logctx.From(ctx).Info("processing")
}
```

---

*End of logctx PRD v1.0.0*
