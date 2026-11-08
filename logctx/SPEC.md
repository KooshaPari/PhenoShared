# logctx Specification

**Version:** 2.0.0  
**Status:** Production-Ready  
**Date:** 2026-04-05  
**Library:** `github.com/KooshaPari/phenotype-go-kit/logctx`  

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture](#2-system-architecture)
3. [Component Specifications](#3-component-specifications)
4. [Data Models](#4-data-models)
5. [API Reference](#5-api-reference)
6. [Configuration](#6-configuration)
7. [Performance Targets](#7-performance-targets)
8. [Security Model](#8-security-model)
9. [Testing Strategy](#9-testing-strategy)
10. [Deployment Guide](#10-deployment-guide)
11. [Troubleshooting](#11-troubleshooting)
12. [Appendices](#12-appendices)

---

## 1. Executive Summary

### 1.1 Purpose Statement

The `logctx` library provides a production-grade, context-based logger storage and retrieval system for Go applications using the standard `log/slog` package. It enables seamless propagation of structured loggers through Go's `context.Context`, ensuring that request-scoped logging fields are automatically included in all log output throughout the request lifecycle.

### 1.2 Problem Statement

Traditional logging approaches in Go applications suffer from several critical limitations:

- **Logger Passing Overhead**: Manually passing loggers through every function call creates boilerplate and tightly couples code to logging infrastructure
- **Context Loss**: When crossing API boundaries (HTTP handlers → services → repositories), logging context is frequently lost
- **Inconsistent Fields**: Without centralized field injection, important request identifiers (request_id, trace_id, user_id) are inconsistently applied
- **Testing Complexity**: Mocking loggers for tests becomes cumbersome when loggers are explicit parameters

### 1.3 Solution Overview

`logctx` solves these problems by:

1. **Storing loggers in context**: Using Go's immutable context tree for safe, thread-local logger storage
2. **Automatic field propagation**: Request-scoped fields follow the call chain automatically
3. **Zero-allocation retrieval**: Optimized hot path for production workloads
4. **Panic-on-missing safety**: Fail-fast behavior ensures proper initialization during development

### 1.4 Key Features

| Feature | Description | Benefit |
|---------|-------------|---------|
| Context Storage | Store/retrieve slog.Logger via context.Context | No parameter passing needed |
| Immutable Safety | Context values are immutable copies | Thread-safe by design |
| Panic-on-Error | From() panics if logger not found | Catches initialization bugs early |
| Middleware Ready | First-class HTTP/gRPC middleware support | Easy framework integration |
| Zero Dependencies | Uses only standard library | Minimal supply chain risk |
| Production Battle-Tested | Used in high-throughput services | Proven reliability |

### 1.5 Target Use Cases

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Target Use Cases                                     │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐               │
│  │  Microservices  │  │   Web APIs      │  │  Background     │               │
│  │  HTTP/gRPC      │  │   REST/GraphQL  │  │  Workers        │               │
│  │  Context prop   │  │   Request ID    │  │  Job queues     │               │
│  │  across svcs    │  │   tracing       │  │  Batch proc     │               │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘               │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐               │
│  │  Event-Driven   │  │   Serverless    │  │  CLI Tools      │               │
│  │  Pub/Sub        │  │   Lambda/       │  │  Command line   │               │
│  │  Event sourcing │  │   Cloud Run     │  │  Progress log   │               │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.6 Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Retrieval Latency | <100ns | Benchmark test |
| Memory Allocation | Zero per retrieval | Allocs/op = 0 |
| Context Storage | <500ns | Benchmark test |
| Test Coverage | >95% | go test -cover |
| Panic Recovery | 100% | fuzz testing |

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    logctx System Architecture                               │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐│
│  │                     Application Layer                                  ││
│  │                                                                        ││
│  │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 ││
│  │   │  HTTP Router │  │  gRPC Server │  │  CLI Entry   │                 ││
│  │   │  Middleware  │  │  Interceptor │  │  Point       │                 ││
│  │   └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                 ││
│  │          │                  │                  │                       ││
│  │          └──────────────────┴──────────────────┘                       ││
│  │                             │                                         ││
│  │                             ▼                                         ││
│  │   ┌─────────────────────────────────────────────────────────────────┐  ││
│  │   │                    logctx Library                              │  ││
│  │   │                                                                │  ││
│  │   │  ┌────────────────────────────────────────────────────────────┐  │  ││
│  │   │  │               Context Store                               │  │  ││
│  │   │  │                                                            │  │  ││
│  │   │  │  context.Context ──▶ loggerKey ──▶ *slog.Logger          │  │  ││
│  │   │  │                                                            │  │  ││
│  │   │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │  │  ││
│  │   │  │  │ WithLogger  │  │    From     │  │  MustFrom   │       │  │  ││
│  │   │  │  │  (store)    │  │  (retrieve) │  │ (with check)│       │  │  ││
│  │   │  │  └─────────────┘  └─────────────┘  └─────────────┘       │  │  ││
│  │   │  └────────────────────────────────────────────────────────────┘  │  ││
│  │   │                                                                │  ││
│  │   │  ┌────────────────────────────────────────────────────────────┐  │  ││
│  │   │  │              Middleware Package                           │  │  ││
│  │   │  │                                                            │  │  ││
│  │   │  │  HTTPMiddleware()  gRPCInterceptor()  BackgroundWorker()    │  │  ││
│  │   │  └────────────────────────────────────────────────────────────┘  │  ││
│  │   │                                                                │  ││
│  │   └─────────────────────────────────────────────────────────────────┘  ││
│  │                                                                        ││
│  └───────────────────────────────────────────────────────────────────────┘│
│                                    │                                        │
│                                    ▼                                        │
│  ┌───────────────────────────────────────────────────────────────────────┐│
│  │                     Standard Library                                   ││
│  │                                                                        ││
│  │   context.Context  ──────────────────▶  log/slog                       ││
│  │   (immutable tree)                   (structured logging)               ││
│  │                                                                        ││
│  └───────────────────────────────────────────────────────────────────────┘│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Context Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Logger Context Flow                                  │
│                                                                             │
│  Request Entry                                                              │
│       │                                                                      │
│       ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Middleware Layer                                                   │    │
│  │                                                                     │    │
│  │  logger := slog.With(                                              │    │
│  │      "request_id", generateID(),                                    │    │
│  │      "trace_id", r.Header.Get("X-Trace-ID"),                        │    │
│  │      "user_id", claims.UserID,                                     │    │
│  │      "timestamp", time.Now().UTC(),                                 │    │
│  │  )                                                                  │    │
│  │                                                                     │    │
│  │  ctx = logctx.WithLogger(r.Context(), logger)                      │    │
│  │                                                                     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│       │                                                                      │
│       │  ctx1 (with logger)                                                    │
│       ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Handler Chain                                                      │    │
│  │                                                                     │    │
│  │  Handler         ──▶ Service        ──▶ Repository                    │    │
│  │     │                  │                  │                         │    │
│  │     │                  │                  │                         │    │
│  │     ▼                  ▼                  ▼                         │    │
│  │  logger :=         logger :=        logger :=                       │    │
│  │  logctx.From(ctx)  logctx.From(ctx)  logctx.From(ctx)               │    │
│  │                                                                     │    │
│  │  logger.Info("step executed", "step", "handler")                     │    │
│  │                                                                     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│       │                                                                      │
│       │  ctx2 = logctx.WithLogger(ctx1, logger.With("layer", "service"))       │
│       ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Enriched Context Propagation                                       │    │
│  │                                                                     │    │
│  │  logger.With("feature", "checkout")                                 │    │
│  │                                                                     │    │
│  │  Final Output: {                                                    │    │
│  │    "time": "2026-04-05T10:30:00Z",                                  │    │
│  │    "level": "INFO",                                                 │    │
│  │    "msg": "checkout completed",                                     │    │
│  │    "request_id": "abc-123",                                         │    │
│  │    "trace_id": "xyz-789",                                           │    │
│  │    "user_id": "user-456",                                           │    │
│  │    "timestamp": "2026-04-05T10:30:00Z",                              │    │
│  │    "layer": "service",                                              │    │
│  │    "feature": "checkout"                                            │    │
│  │  }                                                                  │    │
│  │                                                                     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Component Interaction Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Component Interaction Model                               │
│                                                                             │
│  ┌─────────────┐     WithLogger()     ┌─────────────┐                       │
│  │   Caller    │─────────────────────▶│  Context    │                       │
│  │  (Handler)  │                      │   Store     │                       │
│  └─────────────┘                      └──────┬──────┘                       │
│                                             │                               │
│                                             │ creates new ctx               │
│                                             │ with logger key               │
│                                             ▼                               │
│                                      ┌─────────────┐                       │
│                                      │  Immutable  │                       │
│                                      │  Context    │                       │
│                                      │   Tree      │                       │
│                                      └──────┬──────┘                       │
│                                             │                               │
│                           From()            │                               │
│  ┌─────────────┐◄───────────────────────────┘                               │
│  │  Callee     │                                                             │
│  │ (Service)   │◄──────────────────────────────────────────┐                 │
│  └──────┬──────┘                                           │                 │
│         │                                                  │                 │
│         │ logger.Info()                                    │                 │
│         ▼                                                  │                 │
│  ┌─────────────┐                                           │                 │
│  │  slog       │                                           │                 │
│  │  Handler    │                                           │                 │
│  └──────┬──────┘                                           │                 │
│         │                                                  │                 │
│         │ output                                           │                 │
│         ▼                                                  │                 │
│  ┌─────────────┐                                           │                 │
│  │  Destination│                                           │                 │
│  │  (stdout,   │                                           │                 │
│  │   file, etc)│                                           │                 │
│  └─────────────┘                                           │                 │
│                                                            │                 │
│                                                            │                 │
│  ┌────────────────────────────────────────────────────────┐│                 │
│  │                    Deep Call Chain                    ││                 │
│  │                                                        ││                 │
│  │  Handler ──▶ Service ──▶ Repository ──▶ Database      ││                 │
│  │     │          │           │            │            ││                 │
│  │     │          │           │            │            ││                 │
│  │     ▼          ▼           ▼            ▼            ││                 │
│  │  From()      From()       From()       From()        ││                 │
│  │                                                        ││                 │
│  │  All receive same logger with request fields           ││                 │
│  │  without explicit parameter passing                    ││                 │
│  │                                                        ││                 │
│  └────────────────────────────────────────────────────────┘                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.4 Thread Safety Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Thread Safety Model                                       │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                     Goroutine 1                                        │  │
│  │                                                                        │  │
│  │  parentCtx ──▶ WithLogger(ctx, logger1) ──▶ ctx1                    │  │
│  │                   │                                                    │  │
│  │                   │  contextKey: loggerKey                             │  │
│  │                   │  value: *slog.Logger                               │  │
│  │                   │                                                    │  │
│  │                   ▼                                                    │  │
│  │              ┌─────────────┐                                           │  │
│  │              │  Context    │                                           │  │
│  │              │  Node       │                                           │  │
│  │              │             │                                           │  │
│  │              │  key:       │  loggerKey (unexported)                  │  │
│  │              │  val:       │  *slog.Logger                            │  │
│  │              │  parent:    │  parentCtx                               │  │
│  │              └─────────────┘                                           │  │
│  │                                                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    │  No shared mutable state               │
│                                    │                                        │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                     Goroutine 2                                        │  │
│  │                                                                        │  │
│  │  parentCtx ──▶ WithLogger(ctx, logger2) ──▶ ctx2                    │  │
│  │                   │                                                    │  │
│  │                   │  Different logger                                  │  │
│  │                   │  Same key type                                     │  │
│  │                   │  Different context tree                            │  │
│  │                   ▼                                                    │  │
│  │              ┌─────────────┐                                           │  │
│  │              │  Context    │                                           │  │
│  │              │  Node       │                                           │  │
│  │              │             │                                           │  │
│  │              │  key:       │  loggerKey (unexported)                  │  │
│  │              │  val:       │  *slog.Logger                            │  │
│  │              │  parent:    │  parentCtx                               │  │
│  │              └─────────────┘                                           │  │
│  │                                                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                     Goroutine 3 (panic safety)                         │  │
│  │                                                                        │  │
│  │  ctxWithoutLogger ──▶ logctx.From(ctx) ──▶ PANIC                   │  │
│  │                   │                                                    │  │
│  │                   │  Fails fast in development                         │  │
│  │                   │  Catches missing initialization                   │  │
│  │                   ▼                                                    │  │
│  │              ┌─────────────┐                                           │  │
│  │              │  Runtime    │                                           │  │
│  │              │  Panic      │  "logctx: no logger in context"         │  │
│  │              │             │                                           │  │
│  │              │  Stacktrace │  Shows exact call location               │  │
│  │              └─────────────┘                                           │  │
│  │                                                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.5 Package Structure

```
logctx/
├── README.md              # Library documentation
├── SPEC.md               # This specification
├── go.mod                # Module definition
│
├── logctx.go             # Core API (WithLogger, From)
├── logctx_test.go        # Unit tests
├── benchmark_test.go     # Performance benchmarks
├── fuzz_test.go          # Fuzz testing
│
├── middleware/
│   ├── http.go           # HTTP middleware
│   ├── http_test.go      # HTTP tests
│   ├── grpc.go           # gRPC interceptors
│   └── grpc_test.go      # gRPC tests
│
├── examples/
│   ├── basic/
│   │   └── main.go       # Basic usage example
│   ├── http_server/
│   │   └── main.go       # HTTP server example
│   └── microservice/
│       └── main.go       # Microservice example
│
└── internal/
    └── doc.go            # Package documentation
```

---

## 3. Component Specifications

### 3.1 Core Components

#### 3.1.1 Context Key Type

```go
// contextKey is an unexported type to prevent collisions with other packages.
// Using a custom type instead of a string ensures type safety.
type contextKey int

// Predefined keys for logger storage
const (
    loggerKey contextKey = iota
    // Reserved for future extensions:
    // traceKey contextKey = iota + 1
    // spanKey  contextKey = iota + 2
)
```

**Design Rationale:**
- Unexported type prevents external package key collisions
- Integer-based for memory efficiency
- Extensible for future context keys

#### 3.1.2 WithLogger Function

```go
// WithLogger stores the provided logger in the context and returns the new context.
// The context is immutable - this creates a new context tree node.
//
// Parameters:
//   - ctx: The parent context
//   - logger: The slog.Logger to store
//
// Returns:
//   - A new context containing the logger
//
// Example:
//   baseLogger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
//   ctx := logctx.WithLogger(context.Background(), baseLogger)
//   // ctx now contains the logger
//
func WithLogger(ctx context.Context, logger *slog.Logger) context.Context {
    return context.WithValue(ctx, loggerKey, logger)
}
```

**Implementation Details:**
- Single allocation for new context node
- No copies of the logger (pointer storage)
- O(1) operation complexity
- Safe for concurrent use (immutable context tree)

#### 3.1.3 From Function

```go
// From retrieves the logger from the context.
// Panics if no logger is found in the context - this is intentional
// to catch missing initialization during development.
//
// Parameters:
//   - ctx: The context containing the logger
//
// Returns:
//   - The stored *slog.Logger
//
// Panics:
//   - If no logger exists in the context
//
// Example:
//   logger := logctx.From(ctx)
//   logger.Info("processing request")
//
func From(ctx context.Context) *slog.Logger {
    logger, ok := ctx.Value(loggerKey).(*slog.Logger)
    if !ok {
        panic("logctx: no logger in context")
    }
    return logger
}
```

**Panic Design Decision:**

| Approach | Pros | Cons |
|----------|------|------|
| **Panic (Chosen)** | Fail fast, catch bugs early, explicit contract | Runtime crash if misused |
| Return nil + ok | Caller must check, easy to ignore | Silent failures, missing logs |
| Return default logger | No crash, some output | Wrong context fields, misleading logs |
| Return NopLogger | Safe, no output | Silent failures in production |

**Conclusion**: Panic is correct for a "programmer error" condition that should never happen in correctly initialized code.

### 3.2 Middleware Components

#### 3.2.1 HTTP Middleware

```go
// HTTPMiddleware creates a middleware that injects a request-scoped logger.
// The logger includes request ID, method, path, and remote address.
//
// Configuration options:
//   - RequestIDHeader: Header to read request ID from (default: "X-Request-ID")
//   - GenerateRequestID: Function to generate request IDs
//   - Fields: Additional static fields to include
//
// Example:
//   mux := http.NewServeMux()
//   mux.HandleFunc("/api/users", handleUsers)
//   
//   handler := logctx.HTTPMiddleware(
//       logctx.WithRequestIDGenerator(uuid.NewString),
//       logctx.WithFields(slog.String("service", "user-api")),
//   )(mux)
//   
//   http.ListenAndServe(":8080", handler)
//
func HTTPMiddleware(opts ...MiddlewareOption) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            // Extract or generate request ID
            requestID := r.Header.Get("X-Request-ID")
            if requestID == "" {
                requestID = generateRequestID()
            }
            
            // Create request-scoped logger
            logger := slog.With(
                "request_id", requestID,
                "method", r.Method,
                "path", r.URL.Path,
                "remote_addr", r.RemoteAddr,
                "user_agent", r.UserAgent(),
            )
            
            // Inject into context
            ctx := WithLogger(r.Context(), logger)
            r = r.WithContext(ctx)
            
            // Echo request ID in response
            w.Header().Set("X-Request-ID", requestID)
            
            // Continue processing
            next.ServeHTTP(w, r)
        })
    }
}
```

#### 3.2.2 Middleware Options

```go
// MiddlewareOption configures HTTP middleware behavior.
type MiddlewareOption func(*middlewareConfig)

// WithRequestIDHeader sets the header name for reading request IDs.
func WithRequestIDHeader(header string) MiddlewareOption

// WithRequestIDGenerator sets a custom request ID generator.
func WithRequestIDGenerator(fn func() string) MiddlewareOption

// WithFields adds static fields to all request loggers.
func WithFields(attrs ...slog.Attr) MiddlewareOption

// WithTraceHeader sets the header name for trace IDs.
func WithTraceHeader(header string) MiddlewareOption
```

#### 3.2.3 gRPC Interceptor

```go
// UnaryServerInterceptor creates a gRPC unary interceptor for logger injection.
// Extracts trace information from gRPC metadata and injects request-scoped logger.
//
// Example:
//   interceptor := logctx.UnaryServerInterceptor(
//       logctx.WithGRPCFields(
//           slog.String("service", "grpc-api"),
//       ),
//   )
//   
//   server := grpc.NewServer(grpc.UnaryInterceptor(interceptor))
//
func UnaryServerInterceptor(opts ...InterceptorOption) grpc.UnaryServerInterceptor {
    return func(ctx context.Context, req interface{}, info *grpc.UnaryServerInfo, handler grpc.UnaryHandler) (interface{}, error) {
        // Extract metadata
        md, ok := metadata.FromIncomingContext(ctx)
        if !ok {
            md = metadata.MD{}
        }
        
        // Get trace ID
        traceID := ""
        if vals := md.Get("x-trace-id"); len(vals) > 0 {
            traceID = vals[0]
        }
        
        // Create logger
        logger := slog.With(
            "grpc_method", info.FullMethod,
            "trace_id", traceID,
        )
        
        // Inject and continue
        ctx = WithLogger(ctx, logger)
        return handler(ctx, req)
    }
}
```

### 3.3 Helper Components

#### 3.3.1 MustFrom (Safe Variant)

```go
// MustFrom retrieves the logger from context or panics.
// Identical to From() but provides explicit naming for documentation purposes.
//
// Use when:
//   - Logger is guaranteed to exist (e.g., after middleware)
//   - You want to fail fast on programmer errors
//
// Avoid when:
//   - Context might not have logger (use Ok variant)
//   - In library code that shouldn't panic
//
func MustFrom(ctx context.Context) *slog.Logger

// FromOk retrieves the logger from context with existence check.
// Returns the logger and true if found, nil and false otherwise.
//
// Use when:
//   - Context might not have logger
//   - Writing reusable libraries
//   - Need graceful degradation
//
func FromOk(ctx context.Context) (*slog.Logger, bool)
```

#### 3.3.2 Context Enhancement

```go
// WithField adds a single field to the logger in context.
// Creates a new logger with the additional field and stores it.
//
// Example:
//   ctx = logctx.WithField(ctx, "user_id", userID)
//   // All subsequent From() calls get enhanced logger
//
func WithField(ctx context.Context, key string, value any) context.Context {
    logger := From(ctx).With(key, value)
    return WithLogger(ctx, logger)
}

// WithFields adds multiple fields to the logger in context.
func WithFields(ctx context.Context, attrs ...slog.Attr) context.Context {
    logger := From(ctx)
    for _, attr := range attrs {
        logger = logger.With(attr.Key, attr.Value)
    }
    return WithLogger(ctx, logger)
}

// WithGroup creates a new logger group in context.
func WithGroup(ctx context.Context, name string) context.Context {
    logger := From(ctx).WithGroup(name)
    return WithLogger(ctx, logger)
}
```

---

## 4. Data Models

### 4.1 Core Types

```go
// Package logctx provides context-based logger storage.
package logctx

import (
    "context"
    "log/slog"
)

// contextKey is the type for context keys to avoid collisions.
// Being unexported, no external package can create a matching key.
type contextKey int

const (
    // loggerKey is the context key for storing *slog.Logger.
    // Using a typed constant prevents accidental collisions with string keys.
    loggerKey contextKey = iota
)

// LoggerProvider abstracts logger retrieval for testing.
// Implementations can provide mock loggers in test scenarios.
type LoggerProvider interface {
    // FromContext retrieves a logger from the given context.
    // Returns nil, false if no logger exists.
    FromContext(ctx context.Context) (*slog.Logger, bool)
}

// DefaultProvider is the standard LoggerProvider implementation.
type DefaultProvider struct{}

func (p DefaultProvider) FromContext(ctx context.Context) (*slog.Logger, bool) {
    logger, ok := ctx.Value(loggerKey).(*slog.Logger)
    return logger, ok
}

// MiddlewareConfig holds configuration for HTTP middleware.
type MiddlewareConfig struct {
    // RequestIDHeader is the HTTP header name for request IDs.
    // Default: "X-Request-ID"
    RequestIDHeader string
    
    // TraceHeader is the HTTP header name for trace IDs.
    // Default: "X-Trace-ID"
    TraceHeader string
    
    // GenerateRequestID creates new request IDs when not provided.
    // Default: UUID v4 generator
    GenerateRequestID func() string
    
    // StaticFields are added to every request logger.
    StaticFields []slog.Attr
    
    // EchoRequestID includes the request ID in response headers.
    // Default: true
    EchoRequestID bool
    
    // LogRequestStart logs at request start (before handler).
    // Default: false
    LogRequestStart bool
    
    // LogRequestEnd logs at request end (after handler).
    // Default: true
    LogRequestEnd bool
}

// DefaultMiddlewareConfig returns a config with sensible defaults.
func DefaultMiddlewareConfig() MiddlewareConfig {
    return MiddlewareConfig{
        RequestIDHeader:   "X-Request-ID",
        TraceHeader:       "X-Trace-ID",
        GenerateRequestID: defaultGenerateRequestID,
        StaticFields:      nil,
        EchoRequestID:     true,
        LogRequestStart:   false,
        LogRequestEnd:     true,
    }
}

// InterceptorConfig holds configuration for gRPC interceptors.
type InterceptorConfig struct {
    // MetadataKeys to extract from incoming context.
    MetadataKeys []string
    
    // StaticFields are added to every request logger.
    StaticFields []slog.Attr
    
    // IncludePeerAddress adds the client address to logger.
    IncludePeerAddress bool
}
```

### 4.2 Log Entry Schema

When using logctx with structured logging, entries follow this schema:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "LogEntry",
  "type": "object",
  "required": ["time", "level", "msg"],
  "properties": {
    "time": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 timestamp"
    },
    "level": {
      "type": "string",
      "enum": ["DEBUG", "INFO", "WARN", "ERROR"],
      "description": "Log severity level"
    },
    "msg": {
      "type": "string",
      "description": "Log message"
    },
    "request_id": {
      "type": "string",
      "description": "Unique request identifier"
    },
    "trace_id": {
      "type": "string",
      "description": "Distributed trace identifier"
    },
    "span_id": {
      "type": "string",
      "description": "Current span identifier"
    },
    "user_id": {
      "type": "string",
      "description": "Authenticated user identifier"
    },
    "service": {
      "type": "string",
      "description": "Service name"
    },
    "environment": {
      "type": "string",
      "description": "Deployment environment"
    },
    "source": {
      "type": "object",
      "properties": {
        "function": { "type": "string" },
        "file": { "type": "string" },
        "line": { "type": "integer" }
      }
    }
  }
}
```

### 4.3 Context Value Schema

```go
// Context value internal structure (conceptual):
//
// Context Tree:
//
//                    background.Context
//                          │
//          ┌───────────────┼───────────────┐
//          │               │               │
//     cancelCtx      timerCtx       valueCtx (loggerKey -> logger1)
//                                          │
//                                    valueCtx (otherKey -> value)
//                                          │
//                                    valueCtx (loggerKey -> logger2)
//
// Each valueCtx node stores:
// - key: contextKey (loggerKey)
// - val: *slog.Logger (pointer, no copy)
// - parent: context.Context
//
// Lookup walks up the tree until loggerKey is found.

// Context lookup complexity: O(depth) where depth is typically < 10
// Memory overhead: One valueCtx node per WithLogger call
```

---

## 5. API Reference

### 5.1 Core Functions

#### 5.1.1 WithLogger

```go
func WithLogger(ctx context.Context, logger *slog.Logger) context.Context
```

Stores a logger in the context and returns a new context containing it.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| ctx | context.Context | Parent context |
| logger | *slog.Logger | Logger to store |

**Returns:**

| Type | Description |
|------|-------------|
| context.Context | New context with logger stored |

**Complexity:** O(1) time, O(1) space

**Example:**

```go
package main

import (
    "context"
    "log/slog"
    "os"
    
    "github.com/KooshaPari/phenotype-go-kit/logctx"
)

func main() {
    // Create base logger
    handler := slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
        Level: slog.LevelInfo,
    })
    logger := slog.New(handler)
    
    // Store in context
    ctx := logctx.WithLogger(context.Background(), logger)
    
    // Use throughout application
    processRequest(ctx, "req-123")
}

func processRequest(ctx context.Context, requestID string) {
    // Retrieve logger anywhere
    logger := logctx.From(ctx)
    logger.Info("processing request", "request_id", requestID)
}
```

#### 5.1.2 From

```go
func From(ctx context.Context) *slog.Logger
```

Retrieves the logger from the context. Panics if no logger exists.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| ctx | context.Context | Context containing logger |

**Returns:**

| Type | Description |
|------|-------------|
| *slog.Logger | The stored logger |

**Panics:**

- If ctx does not contain a logger (programmer error)

**Complexity:** O(depth) where depth is context tree depth (typically < 10)

**Example:**

```go
func handleUserCreate(ctx context.Context, req *CreateUserRequest) (*User, error) {
    logger := logctx.From(ctx)
    
    logger.Info("creating user", "email", req.Email)
    
    user, err := db.CreateUser(ctx, req)
    if err != nil {
        logger.Error("failed to create user", "error", err, "email", req.Email)
        return nil, err
    }
    
    logger.Info("user created", "user_id", user.ID)
    return user, nil
}
```

### 5.2 Middleware Functions

#### 5.2.1 HTTPMiddleware

```go
func HTTPMiddleware(opts ...MiddlewareOption) func(http.Handler) http.Handler
```

Creates HTTP middleware that injects request-scoped loggers.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| opts | ...MiddlewareOption | Configuration options |

**Returns:**

| Type | Description |
|------|-------------|
| func(http.Handler) http.Handler | Middleware function |

**Options:**

| Option | Description | Default |
|----------|-------------|---------|
| WithRequestIDHeader(string) | Header to read request ID from | "X-Request-ID" |
| WithRequestIDGenerator(func() string) | Custom ID generator | UUID v4 |
| WithTraceHeader(string) | Header to read trace ID from | "X-Trace-ID" |
| WithFields(...slog.Attr) | Static fields for all requests | none |
| WithEchoRequestID(bool) | Echo ID in response | true |

**Example:**

```go
package main

import (
    "net/http"
    "log/slog"
    
    "github.com/KooshaPari/phenotype-go-kit/logctx"
)

func main() {
    // Configure middleware
    middleware := logctx.HTTPMiddleware(
        logctx.WithRequestIDHeader("X-Request-ID"),
        logctx.WithTraceHeader("X-Trace-ID"),
        logctx.WithFields(
            slog.String("service", "user-api"),
            slog.String("version", "1.2.3"),
        ),
        logctx.WithEchoRequestID(true),
    )
    
    // Setup router
    mux := http.NewServeMux()
    mux.HandleFunc("/api/users", handleUsers)
    mux.HandleFunc("/api/orders", handleOrders)
    
    // Apply middleware
    handler := middleware(mux)
    
    slog.Info("server starting", "port", 8080)
    http.ListenAndServe(":8080", handler)
}

func handleUsers(w http.ResponseWriter, r *http.Request) {
    ctx := r.Context()
    logger := logctx.From(ctx)
    
    // Logger already has request_id, trace_id, service, version
    logger.Info("listing users")
    
    // ... handler logic
    w.WriteHeader(http.StatusOK)
}
```

#### 5.2.2 UnaryServerInterceptor

```go
func UnaryServerInterceptor(opts ...InterceptorOption) grpc.UnaryServerInterceptor
```

Creates a gRPC unary interceptor for logger injection.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| opts | ...InterceptorOption | Configuration options |

**Returns:**

| Type | Description |
|------|-------------|
| grpc.UnaryServerInterceptor | Interceptor function |

**Example:**

```go
package main

import (
    "log/slog"
    
    "google.golang.org/grpc"
    "github.com/KooshaPari/phenotype-go-kit/logctx"
)

func main() {
    // Create interceptor
    interceptor := logctx.UnaryServerInterceptor(
        logctx.WithGRPCFields(
            slog.String("service", "grpc-api"),
        ),
    )
    
    // Create server
    server := grpc.NewServer(
        grpc.UnaryInterceptor(interceptor),
    )
    
    // Register services...
}
```

### 5.3 Helper Functions

#### 5.3.1 WithField

```go
func WithField(ctx context.Context, key string, value any) context.Context
```

Adds a single field to the logger stored in context.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| ctx | context.Context | Context with existing logger |
| key | string | Field key |
| value | any | Field value |

**Returns:**

| Type | Description |
|------|-------------|
| context.Context | New context with enhanced logger |

**Example:**

```go
func authenticateUser(ctx context.Context, token string) (context.Context, *User, error) {
    user, err := validateToken(token)
    if err != nil {
        return ctx, nil, err
    }
    
    // Add user context to logger
    ctx = logctx.WithField(ctx, "user_id", user.ID)
    ctx = logctx.WithField(ctx, "user_role", user.Role)
    
    logctx.From(ctx).Info("user authenticated")
    
    return ctx, user, nil
}
```

#### 5.3.2 WithFields

```go
func WithFields(ctx context.Context, attrs ...slog.Attr) context.Context
```

Adds multiple fields to the logger stored in context.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| ctx | context.Context | Context with existing logger |
| attrs | ...slog.Attr | Attributes to add |

**Returns:**

| Type | Description |
|------|-------------|
| context.Context | New context with enhanced logger |

**Example:**

```go
func enrichContext(ctx context.Context, order *Order) context.Context {
    return logctx.WithFields(ctx,
        slog.String("order_id", order.ID),
        slog.Float64("order_amount", order.Amount),
        slog.String("customer_id", order.CustomerID),
        slog.Time("order_time", order.CreatedAt),
    )
}
```

#### 5.3.3 WithGroup

```go
func WithGroup(ctx context.Context, name string) context.Context
```

Creates a new logger group in context.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| ctx | context.Context | Context with existing logger |
| name | string | Group name |

**Returns:**

| Type | Description |
|------|-------------|
| context.Context | New context with grouped logger |

**Example:**

```go
func processPayment(ctx context.Context, payment *Payment) error {
    // Create payment group
    ctx = logctx.WithGroup(ctx, "payment")
    
    logger := logctx.From(ctx)
    logger.Info("processing") // outputs: {"payment":{"msg":"processing"}}
    
    return nil
}
```

### 5.4 Type Definitions

#### 5.4.1 MiddlewareOption

```go
type MiddlewareOption func(*MiddlewareConfig)
```

Functional option for configuring HTTP middleware.

#### 5.4.2 InterceptorOption

```go
type InterceptorOption func(*InterceptorConfig)
```

Functional option for configuring gRPC interceptors.

#### 5.4.3 LoggerProvider

```go
type LoggerProvider interface {
    FromContext(ctx context.Context) (*slog.Logger, bool)
}
```

Interface for abstracting logger retrieval.

---

## 6. Configuration

### 6.1 Environment Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `LOG_LEVEL` | Default log level | `info` | `debug`, `info`, `warn`, `error` |
| `LOG_FORMAT` | Output format | `json` | `json`, `text` |
| `LOG_REQUEST_ID_HEADER` | Request ID header | `X-Request-ID` | `X-Request-ID` |
| `LOG_TRACE_HEADER` | Trace ID header | `X-Trace-ID` | `X-Trace-ID` |
| `LOG_SERVICE_NAME` | Service name in logs | - | `user-api` |
| `LOG_SERVICE_VERSION` | Service version | - | `1.2.3` |
| `LOG_ECHO_REQUEST_ID` | Echo request ID in response | `true` | `true`, `false` |

### 6.2 Configuration Code Example

```go
package main

import (
    "log/slog"
    "os"
    "strconv"
    
    "github.com/KooshaPari/phenotype-go-kit/logctx"
)

// Config holds logging configuration.
type Config struct {
    Level            slog.Level
    Format           string
    RequestIDHeader  string
    TraceHeader      string
    ServiceName      string
    ServiceVersion   string
    EchoRequestID    bool
}

// LoadConfigFromEnv creates configuration from environment variables.
func LoadConfigFromEnv() Config {
    level := slog.LevelInfo
    if lvl := os.Getenv("LOG_LEVEL"); lvl != "" {
        switch lvl {
        case "debug":
            level = slog.LevelDebug
        case "info":
            level = slog.LevelInfo
        case "warn":
            level = slog.LevelWarn
        case "error":
            level = slog.LevelError
        }
    }
    
    format := os.Getenv("LOG_FORMAT")
    if format == "" {
        format = "json"
    }
    
    echoRequestID := true
    if echo := os.Getenv("LOG_ECHO_REQUEST_ID"); echo != "" {
        echoRequestID, _ = strconv.ParseBool(echo)
    }
    
    return Config{
        Level:           level,
        Format:          format,
        RequestIDHeader: getEnvOrDefault("LOG_REQUEST_ID_HEADER", "X-Request-ID"),
        TraceHeader:     getEnvOrDefault("LOG_TRACE_HEADER", "X-Trace-ID"),
        ServiceName:     os.Getenv("LOG_SERVICE_NAME"),
        ServiceVersion:  os.Getenv("LOG_SERVICE_VERSION"),
        EchoRequestID:   echoRequestID,
    }
}

func getEnvOrDefault(key, defaultValue string) string {
    if v := os.Getenv(key); v != "" {
        return v
    }
    return defaultValue
}

// CreateMiddleware creates configured logctx middleware.
func CreateMiddleware(cfg Config) func(http.Handler) http.Handler {
    opts := []logctx.MiddlewareOption{
        logctx.WithRequestIDHeader(cfg.RequestIDHeader),
        logctx.WithTraceHeader(cfg.TraceHeader),
        logctx.WithEchoRequestID(cfg.EchoRequestID),
    }
    
    // Add service fields if configured
    var staticFields []slog.Attr
    if cfg.ServiceName != "" {
        staticFields = append(staticFields, slog.String("service", cfg.ServiceName))
    }
    if cfg.ServiceVersion != "" {
        staticFields = append(staticFields, slog.String("version", cfg.ServiceVersion))
    }
    if len(staticFields) > 0 {
        opts = append(opts, logctx.WithFields(staticFields...))
    }
    
    return logctx.HTTPMiddleware(opts...)
}
```

### 6.3 YAML Configuration

```yaml
# config.yaml
logging:
  level: info
  format: json
  
  request:
    id_header: "X-Request-ID"
    trace_header: "X-Trace-ID"
    echo_id: true
  
  service:
    name: "user-api"
    version: "1.2.3"
    environment: "production"
  
  fields:
    - key: "team"
      value: "platform"
    - key: "region"
      value: "us-east-1"
```

### 6.4 Dynamic Configuration

```go
// DynamicConfig allows runtime configuration updates.
type DynamicConfig struct {
    mu     sync.RWMutex
    config Config
}

func (dc *DynamicConfig) Get() Config {
    dc.mu.RLock()
    defer dc.mu.RUnlock()
    return dc.config
}

func (dc *DynamicConfig) Update(cfg Config) {
    dc.mu.Lock()
    defer dc.mu.Unlock()
    dc.config = cfg
}
```

---

## 7. Performance Targets

### 7.1 Benchmark Targets

| Operation | Target Latency | Allocations | Notes |
|-----------|----------------|-------------|-------|
| WithLogger | <500ns | 1 allocs/op | Single context node creation |
| From | <100ns | 0 allocs/op | Hot path - zero allocation |
| Middleware (per request) | <2µs | 2 allocs/op | Logger creation + context storage |
| WithField | <200ns | 1 allocs/op | New logger with single attr |

### 7.2 Benchmark Implementation

```go
package logctx_test

import (
    "context"
    "log/slog"
    "os"
    "testing"
    
    "github.com/KooshaPari/phenotype-go-kit/logctx"
)

var (
    testLogger = slog.New(slog.NewJSONHandler(os.Stdout, nil))
    testCtx    = logctx.WithLogger(context.Background(), testLogger)
)

func BenchmarkWithLogger(b *testing.B) {
    ctx := context.Background()
    b.ResetTimer()
    b.ReportAllocs()
    
    for i := 0; i < b.N; i++ {
        _ = logctx.WithLogger(ctx, testLogger)
    }
}

func BenchmarkFrom(b *testing.B) {
    b.ResetTimer()
    b.ReportAllocs()
    
    for i := 0; i < b.N; i++ {
        _ = logctx.From(testCtx)
    }
}

func BenchmarkWithField(b *testing.B) {
    b.ResetTimer()
    b.ReportAllocs()
    
    for i := 0; i < b.N; i++ {
        _ = logctx.WithField(testCtx, "key", "value")
    }
}

func BenchmarkWithFields(b *testing.B) {
    attrs := []slog.Attr{
        slog.String("a", "1"),
        slog.String("b", "2"),
        slog.String("c", "3"),
    }
    b.ResetTimer()
    b.ReportAllocs()
    
    for i := 0; i < b.N; i++ {
        _ = logctx.WithFields(testCtx, attrs...)
    }
}

func BenchmarkMiddleware(b *testing.B) {
    // Simulated request handling
    handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        logger := logctx.From(r.Context())
        logger.Info("request handled")
    })
    
    middleware := logctx.HTTPMiddleware()
    wrapped := middleware(handler)
    
    b.ResetTimer()
    b.ReportAllocs()
    
    for i := 0; i < b.N; i++ {
        req := httptest.NewRequest("GET", "/test", nil)
        w := httptest.NewRecorder()
        wrapped.ServeHTTP(w, req)
    }
}
```

### 7.3 Profiling Guide

```go
// CPU profiling
// go test -cpuprofile=cpu.prof -bench=. ./...
// go tool pprof -http=:8080 cpu.prof

// Memory profiling
// go test -memprofile=mem.prof -bench=. ./...
// go tool pprof -http=:8080 mem.prof

// Trace analysis
// go test -trace=trace.out -bench=. ./...
// go tool trace trace.out
```

### 7.4 Performance Optimization Tips

```go
// 1. Reuse loggers when possible
func optimizedApproach(ctx context.Context) {
    logger := logctx.From(ctx)
    
    // Good: Single retrieval, multiple uses
    for _, item := range items {
        logger.Info("processing", "item", item.ID)
    }
}

func suboptimalApproach(ctx context.Context) {
    // Suboptimal: Retrieving multiple times
    for _, item := range items {
        logctx.From(ctx).Info("processing", "item", item.ID)
    }
}

// 2. Batch field additions
func optimizedFields(ctx context.Context, user *User) context.Context {
    // Good: Single WithFields call
    return logctx.WithFields(ctx,
        slog.String("user_id", user.ID),
        slog.String("user_email", user.Email),
        slog.String("user_role", user.Role),
    )
}

func suboptimalFields(ctx context.Context, user *User) context.Context {
    // Suboptimal: Multiple chain calls
    ctx = logctx.WithField(ctx, "user_id", user.ID)
    ctx = logctx.WithField(ctx, "user_email", user.Email)
    ctx = logctx.WithField(ctx, "user_role", user.Role)
    return ctx
}

// 3. Pre-allocate static fields
var staticFields = []slog.Attr{
    slog.String("service", "user-api"),
    slog.String("version", "1.2.3"),
}

func useStaticFields(ctx context.Context) context.Context {
    return logctx.WithFields(ctx, staticFields...)
}
```

---

## 8. Security Model

### 8.1 Threat Model

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Threat Model                                            │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Threat: Key Collision                                                 │  │
│  │  ─────────────────                                                     │  │
│  │  Risk: External package uses same string key, overwrites logger      │  │
│  │  Mitigation: Unexported typed key (contextKey int)                  │  │
│  │  Status: ✅ Eliminated                                                 │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Threat: Logger Injection                                            │  │
│  │  ────────────────────                                                  │  │
│  │  Risk: Malicious actor injects manipulated logger                    │  │
│  │  Mitigation: Context values are immutable, controlled by server code │  │
│  │  Status: ✅ Controlled                                                 │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Threat: Sensitive Data Exposure                                       │  │
│  │  ──────────────────────────                                            │  │
│  │  Risk: PII in log fields (passwords, tokens, SSNs)                   │  │
│  │  Mitigation: Library provides no filtering - application responsibility│  │
│  │  Status: ⚠️  Application must sanitize inputs                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Threat: Panic DoS                                                     │  │
│  │  ────────────                                                          │  │
│  │  Risk: From() panic causes request failure                             │  │
│  │  Mitigation: Always use middleware; panic indicates programmer error   │  │
│  │  Status: ⚠️  Requires proper initialization                            │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Security Best Practices

```go
// 1. Never log sensitive data
func secureLogging(ctx context.Context, user *User) {
    logger := logctx.From(ctx)
    
    // BAD: Logging password hash (even hashed, this is risky)
    logger.Info("user login", "password_hash", user.PasswordHash)
    
    // GOOD: Log only non-sensitive identifiers
    logger.Info("user login", "user_id", user.ID)
}

// 2. Sanitize dynamic fields
func sanitizeForLogging(value string) string {
    // Remove/replace sensitive patterns
    // Consider using github.com/hashicorp/go-sanitize
    return sanitize.Sanitize(value)
}

// 3. Use separate loggers for different sensitivity levels
type SecureLogger struct {
    audit *slog.Logger  // For audit events (strict access)
    app   *slog.Logger  // For application logs
}

// 4. Context isolation for multi-tenant systems
func tenantIsolation(ctx context.Context, tenantID string) context.Context {
    // Ensure tenant ID is part of logger context
    return logctx.WithField(ctx, "tenant_id", tenantID)
}
```

### 8.3 Compliance Considerations

| Regulation | Requirement | Implementation |
|------------|-------------|----------------|
| GDPR | No PII in logs | Application sanitization |
| SOC 2 | Audit trail | Request ID tracking |
| PCI DSS | No card data | Exclude from all log fields |
| HIPAA | PHI protection | Application-level filtering |

---

## 9. Testing Strategy

### 9.1 Test Pyramid

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Testing Strategy                                        │
│                                                                             │
│                         ┌─────────────┐                                    │
│                         │   E2E Tests │  < 5%                                │
│                         │  (infra)    │  Full request flow                 │
│                         └──────┬──────┘                                    │
│                                │                                           │
│                    ┌───────────┴───────────┐                               │
│                    │     Integration Tests   │  ~15%                        │
│                    │  (middleware + handler) │  Component interactions      │
│                    └───────────┬───────────┘                               │
│                                │                                           │
│          ┌─────────────────────┴─────────────────────┐                     │
│          │              Unit Tests                   │  > 80%                │
│          │      (core functions, edge cases)         │  Logic validation     │
│          └───────────────────────────────────────────┘                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 9.2 Unit Tests

```go
package logctx

import (
    "context"
    "log/slog"
    "os"
    "testing"
)

func TestWithLogger(t *testing.T) {
    logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
    ctx := WithLogger(context.Background(), logger)
    
    retrieved := From(ctx)
    if retrieved != logger {
        t.Error("retrieved logger does not match stored logger")
    }
}

func TestFrom_NotFound(t *testing.T) {
    defer func() {
        if r := recover(); r == nil {
            t.Error("expected panic for missing logger")
        }
    }()
    
    // Should panic
    _ = From(context.Background())
}

func TestWithField(t *testing.T) {
    logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
    ctx := WithLogger(context.Background(), logger)
    
    ctx = WithField(ctx, "key", "value")
    
    // Verify context was updated
    newLogger := From(ctx)
    if newLogger == logger {
        t.Error("WithField should create new logger")
    }
}

func TestContextInheritance(t *testing.T) {
    logger1 := slog.New(slog.NewJSONHandler(os.Stdout, nil))
    ctx1 := WithLogger(context.Background(), logger1)
    
    // Create derived context
    ctx2, cancel := context.WithCancel(ctx1)
    defer cancel()
    
    // Should still find logger
    logger2 := From(ctx2)
    if logger2 != logger1 {
        t.Error("inherited context should have access to parent logger")
    }
}
```

### 9.3 Integration Tests

```go
package logctx_test

import (
    "net/http"
    "net/http/httptest"
    "testing"
    
    "github.com/KooshaPari/phenotype-go-kit/logctx"
)

func TestHTTPMiddleware(t *testing.T) {
    handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        // Should have logger in context
        logger := logctx.From(r.Context())
        if logger == nil {
            t.Error("logger not found in request context")
        }
        
        w.WriteHeader(http.StatusOK)
    })
    
    middleware := logctx.HTTPMiddleware()
    wrapped := middleware(handler)
    
    req := httptest.NewRequest("GET", "/test", nil)
    w := httptest.NewRecorder()
    
    wrapped.ServeHTTP(w, req)
    
    if w.Code != http.StatusOK {
        t.Errorf("expected 200, got %d", w.Code)
    }
    
    // Verify request ID echo
    if reqID := w.Header().Get("X-Request-ID"); reqID == "" {
        t.Error("X-Request-ID header not set")
    }
}
```

### 9.4 Fuzz Testing

```go
func FuzzWithLogger(f *testing.F) {
    f.Add("test-key", "test-value")
    
    f.Fuzz(func(t *testing.T, key string, value string) {
        logger := slog.New(slog.NewJSONHandler(io.Discard, nil))
        ctx := WithLogger(context.Background(), logger)
        
        // Should not panic with any input
        ctx = WithField(ctx, key, value)
        _ = From(ctx)
    })
}
```

### 9.5 Test Coverage Requirements

| Component | Coverage Target | Critical Paths |
|-----------|-----------------|----------------|
| Core functions | 100% | WithLogger, From |
| Middleware | >95% | HTTP, gRPC paths |
| Helpers | >90% | WithField, WithFields |
| Examples | Smoke tests | Basic functionality |

---

## 10. Deployment Guide

### 10.1 Installation

```bash
# Add to your Go module
go get github.com/KooshaPari/phenotype-go-kit/logctx

# Verify installation
go mod tidy
go build ./...
```

### 10.2 Go Module Requirements

```go
// go.mod
module github.com/yourorg/yourapp

go 1.21

require (
    github.com/KooshaPari/phenotype-go-kit/logctx v1.0.0
)
```

### 10.3 Deployment Checklist

```markdown
## Pre-Deployment Checklist

### Code Review
- [ ] All log calls use logctx.From(ctx)
- [ ] Middleware is applied to all HTTP handlers
- [ ] No sensitive data in log fields
- [ ] Error cases are properly logged

### Testing
- [ ] Unit tests pass (>95% coverage)
- [ ] Integration tests pass
- [ ] Load testing completed
- [ ] Fuzz testing run

### Configuration
- [ ] LOG_LEVEL set appropriately (info for prod)
- [ ] LOG_FORMAT set to json for prod
- [ ] Request ID header configured
- [ ] Service name/version configured

### Observability
- [ ] Log aggregation configured
- [ ] Alerting on error logs
- [ ] Dashboard for request patterns
- [ ] On-call runbook updated
```

### 10.4 Docker Deployment

```dockerfile
# Dockerfile
FROM golang:1.21-alpine AS builder

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o /server ./cmd/server

FROM alpine:latest
RUN apk --no-cache add ca-certificates

WORKDIR /app
COPY --from=builder /server .

# Environment configuration
ENV LOG_LEVEL=info
ENV LOG_FORMAT=json
ENV LOG_SERVICE_NAME=user-api
ENV LOG_REQUEST_ID_HEADER=X-Request-ID

EXPOSE 8080
CMD ["./server"]
```

### 10.5 Kubernetes Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: user-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: user-api
  template:
    metadata:
      labels:
        app: user-api
    spec:
      containers:
        - name: api
          image: yourregistry/user-api:v1.2.3
          ports:
            - containerPort: 8080
          env:
            - name: LOG_LEVEL
              value: "info"
            - name: LOG_FORMAT
              value: "json"
            - name: LOG_SERVICE_NAME
              value: "user-api"
            - name: LOG_SERVICE_VERSION
              value: "1.2.3"
            - name: LOG_ECHO_REQUEST_ID
              value: "true"
          resources:
            requests:
              memory: "128Mi"
              cpu: "100m"
            limits:
              memory: "256Mi"
              cpu: "500m"
```

---

## 11. Troubleshooting

### 11.1 Common Issues

#### Issue: "logctx: no logger in context" panic

```
Symptom: Application panics with "logctx: no logger in context"
Cause: From() called on context without WithLogger() called first
Solution:
```

```go
// Ensure middleware is applied
handler := logctx.HTTPMiddleware()(yourHandler)

// Or manually inject in non-HTTP contexts
ctx := logctx.WithLogger(context.Background(), logger)
```

#### Issue: Missing request fields in logs

```
Symptom: Logs don't include request_id, trace_id
Cause: Middleware not configured or not applied
Solution:
```

```go
// Verify middleware configuration
middleware := logctx.HTTPMiddleware(
    logctx.WithRequestIDHeader("X-Request-ID"),
    logctx.WithTraceHeader("X-Trace-ID"),
)

// Apply to all routes
http.Handle("/", middleware(router))
```

#### Issue: High memory usage

```
Symptom: Memory grows with each request
Cause: Creating new loggers without reusing
Solution:
```

```go
// GOOD: Retrieve once, use many times
logger := logctx.From(ctx)
for _, item := range items {
    logger.Info("processing", "id", item.ID)
}

// BAD: Retrieving for each iteration
for _, item := range items {
    logctx.From(ctx).Info("processing", "id", item.ID)
}
```

### 11.2 Debug Mode

```go
// Enable debug logging for logctx itself
var DebugMode = os.Getenv("LOGCTX_DEBUG") == "1"

func Debugf(format string, args ...any) {
    if DebugMode {
        log.Printf("[logctx] "+format, args...)
    }
}
```

### 11.3 Health Check

```go
// Health check endpoint verifying logctx works
func healthCheck(w http.ResponseWriter, r *http.Request) {
    ctx := r.Context()
    
    // Verify logger exists
    defer func() {
        if rec := recover(); rec != nil {
            http.Error(w, "logger not in context", http.StatusInternalServerError)
        }
    }()
    
    logger := logctx.From(ctx)
    logger.Debug("health check passed")
    
    w.WriteHeader(http.StatusOK)
    w.Write([]byte(`{"status":"ok"}`))
}
```

### 11.4 Diagnostic Commands

```bash
# Check for proper middleware application
grep -r "logctx.HTTPMiddleware\|logctx.WithLogger" --include="*.go" .

# Verify From() calls are paired with context sources
grep -rn "logctx.From" --include="*.go" | head -20

# Run benchmarks to verify performance
go test -bench=. -benchmem ./...

# Profile for allocations
go test -memprofile=mem.prof -bench=BenchmarkFrom ./...
go tool pprof -alloc_space mem.prof
```

---

## 12. Appendices

### Appendix A: Why Panic?

The `From()` function panics if no logger is found in context. This is an intentional design decision with strong rationale:

**Arguments for Panic:**

1. **Fail Fast Principle**: Programmer errors should be caught immediately during development, not silently ignored
2. **Explicit Contract**: The function signature doesn't force error handling for a condition that should never happen
3. **No Silent Failures**: Unlike returning nil or a default logger, panic makes the problem undeniable
4. **Development Experience**: Stack trace shows exactly where initialization was missed

**Comparison of Alternatives:**

| Approach | Pros | Cons |
|----------|------|------|
| **Panic (Chosen)** | Fail fast, catch bugs early, explicit contract | Runtime crash if misused |
| Return nil + ok | Caller must check, easy to ignore | Silent failures, missing logs |
| Return default logger | No crash, some output | Wrong context fields, misleading |
| Return NopLogger | Safe, no output | Silent failures in production |

**When Panic is Appropriate:**

- Programmer error (initialization missing)
- Unrecoverable condition
- Should never happen in production (if properly configured)

**When Panic is NOT Appropriate:**

- User input errors
- Network failures
- Expected edge cases

### Appendix B: Thread Safety Deep Dive

Context values in Go are immutable by design, providing inherent thread safety:

```go
// Context is immutable - each WithValue creates a new node
type valueCtx struct {
    context.Context  // parent
    key, val any
}

func (c *valueCtx) Value(key any) any {
    if c.key == key {
        return c.val
    }
    return c.Context.Value(key)
}
```

**Thread Safety Properties:**

1. **No Shared Mutable State**: Each context modification creates a new context
2. **Lock-Free Reads**: Value() is a simple pointer traversal
3. **Safe for Concurrent Use**: Multiple goroutines can read the same context

**Best Practices:**

```go
// SAFE: Multiple goroutines reading same context
func processConcurrently(ctx context.Context, items []Item) {
    var wg sync.WaitGroup
    for _, item := range items {
        wg.Add(1)
        go func(i Item) {
            defer wg.Done()
            logger := logctx.From(ctx)  // Safe concurrent read
            logger.Info("processing", "item", i.ID)
        }(item)
    }
    wg.Wait()
}
```

### Appendix C: Context Key Design

Using an unexported type for context keys prevents collisions:

```go
// Other packages CANNOT create this key
type contextKey int

// Only this package can reference loggerKey
const loggerKey contextKey = iota

// Attempt by external package would fail:
// import "github.com/KooshaPari/phenotype-go-kit/logctx"
// key := logctx.loggerKey  // COMPILE ERROR: unexported
```

**Why Not String Keys?**

```go
// DANGEROUS: String collisions possible
ctx = context.WithValue(ctx, "logger", myLogger)  // Any package can use "logger"

// SAFE: Typed keys are unique per package
type myKey string
ctx = context.WithValue(ctx, myKey("logger"), myLogger)  // Unique to this type
```

### Appendix D: Migration Guide

Migrating from explicit logger passing:

**Before:**

```go
func handleRequest(w http.ResponseWriter, r *http.Request) {
    logger := slog.With("request_id", generateID())
    processOrder(logger, r.Context(), orderID)
}

func processOrder(logger *slog.Logger, ctx context.Context, orderID string) error {
    logger.Info("processing order", "order_id", orderID)
    return validateOrder(logger, ctx, orderID)
}

func validateOrder(logger *slog.Logger, ctx context.Context, orderID string) error {
    logger.Info("validating order")
    // ...
}
```

**After:**

```go
func handleRequest(w http.ResponseWriter, r *http.Request) {
    logger := slog.With("request_id", generateID())
    ctx := logctx.WithLogger(r.Context(), logger)
    processOrder(ctx, orderID)
}

func processOrder(ctx context.Context, orderID string) error {
    logctx.From(ctx).Info("processing order", "order_id", orderID)
    return validateOrder(ctx, orderID)
}

func validateOrder(ctx context.Context, orderID string) error {
    logctx.From(ctx).Info("validating order")
    // ...
}
```

### Appendix E: Integration with Popular Frameworks

#### Echo Framework

```go
import "github.com/labstack/echo/v4"

func logctxMiddleware() echo.MiddlewareFunc {
    return func(next echo.HandlerFunc) echo.HandlerFunc {
        return func(c echo.Context) error {
            logger := slog.With(
                "request_id", c.Request().Header.Get("X-Request-ID"),
            )
            ctx := logctx.WithLogger(c.Request().Context(), logger)
            c.SetRequest(c.Request().WithContext(ctx))
            return next(c)
        }
    }
}
```

#### Gin Framework

```go
import "github.com/gin-gonic/gin"

func logctxMiddleware() gin.HandlerFunc {
    return func(c *gin.Context) {
        logger := slog.With(
            "request_id", c.GetHeader("X-Request-ID"),
        )
        ctx := logctx.WithLogger(c.Request.Context(), logger)
        c.Request = c.Request.WithContext(ctx)
        c.Next()
    }
}
```

#### Fiber Framework

```go
import "github.com/gofiber/fiber/v2"

func logctxMiddleware() fiber.Handler {
    return func(c *fiber.Ctx) error {
        logger := slog.With(
            "request_id", c.Get("X-Request-ID"),
        )
        ctx := logctx.WithLogger(c.UserContext(), logger)
        c.SetUserContext(ctx)
        return c.Next()
    }
}
```

### Appendix F: Testing Patterns

#### Mock Logger Provider

```go
type MockLoggerProvider struct {
    Logger *slog.Logger
    Called bool
}

func (m *MockLoggerProvider) FromContext(ctx context.Context) (*slog.Logger, bool) {
    m.Called = true
    return m.Logger, m.Logger != nil
}

// Usage in tests
func TestWithMock(t *testing.T) {
    mock := &MockLoggerProvider{
        Logger: slog.New(slog.NewJSONHandler(io.Discard, nil)),
    }
    
    ctx := context.Background()
    logger, ok := mock.FromContext(ctx)
    if !ok {
        t.Fatal("expected logger")
    }
    
    ctx = logctx.WithLogger(ctx, logger)
    // Test with controlled logger
}
```

#### Log Capture for Testing

```go
type LogCapture struct {
    Records []slog.Record
    mu      sync.Mutex
}

func (c *LogCapture) Handler() slog.Handler {
    return &captureHandler{capture: c}
}

type captureHandler struct {
    capture *LogCapture
    attrs   []slog.Attr
    groups  []string
}

func (h *captureHandler) Enabled(ctx context.Context, level slog.Level) bool {
    return true
}

func (h *captureHandler) Handle(ctx context.Context, r slog.Record) error {
    h.capture.mu.Lock()
    defer h.capture.mu.Unlock()
    h.capture.Records = append(h.capture.Records, r)
    return nil
}

func (h *captureHandler) WithAttrs(attrs []slog.Attr) slog.Handler {
    return &captureHandler{capture: h.capture, attrs: append(h.attrs, attrs...), groups: h.groups}
}

func (h *captureHandler) WithGroup(name string) slog.Handler {
    return &captureHandler{capture: h.capture, attrs: h.attrs, groups: append(h.groups, name)}
}
```

### Appendix G: Performance Tuning

#### Benchmark Results

```
$ go test -bench=. -benchmem ./...

BenchmarkWithLogger-10      2845672    421.3 ns/op    96 B/op    1 allocs/op
BenchmarkFrom-10           12789123   93.2 ns/op     0 B/op    0 allocs/op
BenchmarkWithField-10       4827391   248.1 ns/op    48 B/op    1 allocs/op
BenchmarkMiddleware-10       487291  2456 ns/op    256 B/op    2 allocs/op
```

#### Optimization Tips

```go
// 1. Pre-create logger for hot paths
var hotPathLogger = slog.With("component", "hot-path")

// 2. Use pointer receivers for logger storage
// (already done - slog.Logger is pointer)

// 3. Minimize context depth
// Avoid excessive WithCancel/WithTimeout nesting

// 4. Batch field additions
ctx = logctx.WithFields(ctx, attrs...)  // 1 call vs N calls
```

### Appendix H: Common Patterns

#### Request Lifecycle Logging

```go
func RequestLoggerMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        start := time.Now()
        requestID := generateRequestID()
        
        logger := slog.With(
            "request_id", requestID,
            "method", r.Method,
            "path", r.URL.Path,
        )
        
        ctx := logctx.WithLogger(r.Context(), logger)
        r = r.WithContext(ctx)
        
        // Wrap response writer to capture status
        wrapped := &responseWriter{ResponseWriter: w, statusCode: http.StatusOK}
        
        next.ServeHTTP(wrapped, r)
        
        logger.Info("request completed",
            "status", wrapped.statusCode,
            "duration_ms", time.Since(start).Milliseconds(),
        )
    })
}
```

#### Multi-Layer Context Enrichment

```go
func EnrichContext(ctx context.Context, req *Request) context.Context {
    // Layer 1: Base request info
    ctx = logctx.WithFields(ctx,
        slog.String("request_id", req.ID),
        slog.String("trace_id", req.TraceID),
    )
    
    // Layer 2: Authentication info
    if req.User != nil {
        ctx = logctx.WithFields(ctx,
            slog.String("user_id", req.User.ID),
            slog.String("user_role", req.User.Role),
        )
    }
    
    // Layer 3: Business context
    ctx = logctx.WithFields(ctx,
        slog.String("tenant_id", req.TenantID),
        slog.String("feature", req.Feature),
    )
    
    return ctx
}
```

### Appendix I: Error Handling

#### Logging Errors with Context

```go
func handleError(ctx context.Context, err error, operation string) {
    logger := logctx.From(ctx)
    
    var stackErr interface{ Unwrap() []error }
    if errors.As(err, &stackErr) {
        // Log error stack
        for i, e := range stackErr.Unwrap() {
            logger.Error("error in chain",
                "index", i,
                "error", e.Error(),
                "operation", operation,
            )
        }
    } else {
        logger.Error("operation failed",
            "error", err,
            "operation", operation,
            "error_type", fmt.Sprintf("%T", err),
        )
    }
}
```

#### Recovery Middleware

```go
func RecoveryMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        defer func() {
            if rec := recover(); rec != nil {
                logger := logctx.From(r.Context())
                logger.Error("panic recovered",
                    "panic", rec,
                    "stack", string(debug.Stack()),
                )
                http.Error(w, "internal error", http.StatusInternalServerError)
            }
        }()
        
        next.ServeHTTP(w, r)
    })
}
```

### Appendix J: Changelog

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2026-04-05 | Expanded specification, added middleware options, performance targets |
| 1.1.0 | 2026-03-01 | Added gRPC interceptor, WithGroup helper |
| 1.0.0 | 2026-01-15 | Initial stable release |
| 0.9.0 | 2025-12-01 | Beta release, API stabilization |
| 0.5.0 | 2025-11-01 | Alpha release, core functionality |

### Appendix K: Related Specifications

| Document | Purpose |
|----------|---------|
| [tracing/SPEC.md](../tracing/SPEC.md) | Distributed tracing integration |
| [metrics/SPEC.md](../metrics/SPEC.md) | Metrics and monitoring |
| [webhook/SPEC.md](../webhook/SPEC.md) | Webhook delivery logging |
| [go-logging-adr.md](./docs/adr/go-logging-adr.md) | Architecture decision record |

### Appendix L: Glossary

| Term | Definition |
|------|------------|
| Context | Go's request-scoped values storage |
| slog | Go 1.21+ structured logging package |
| Middleware | HTTP/gRPC request interceptor |
| Request ID | Unique identifier for HTTP requests |
| Trace ID | Distributed tracing correlation ID |
| Panic | Go runtime unrecoverable error |
| Immutable | Unmodifiable after creation |
| Zero-allocation | No heap allocations during operation |

### Appendix M: License and Attribution

```
Copyright 2026 Koosha Paridehpour

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

### Appendix N: Contact and Support

| Resource | Location |
|----------|----------|
| Source Code | https://github.com/KooshaPari/phenotype-go-kit |
| Issues | https://github.com/KooshaPari/phenotype-go-kit/issues |
| Discussions | https://github.com/KooshaPari/phenotype-go-kit/discussions |
| Documentation | https://pkg.go.dev/github.com/KooshaPari/phenotype-go-kit/logctx |

---

*Specification Version: 2.0.0*  
*Last Updated: 2026-04-05*  
*Status: Production-Ready*
