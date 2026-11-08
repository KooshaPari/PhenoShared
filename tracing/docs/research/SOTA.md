# Tracing Library - State of the Art

> OpenTelemetry Distributed Tracing for Go - Observability Patterns

**Version**: 1.0  
**Status**: Active  
**Last Updated**: 2026-04-05

---

## Part I: Observability Evolution (2024-2026)

### 1.1 Telemetry Signal Evolution

Observability has evolved from isolated metrics, logs, and traces to unified telemetry systems.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Observability Evolution                                │
│                                                                             │
│  Metrics ──────► Logs ───────► Traces ───────► Profiles ──────► Correlation│
│                                                                             │
│  2010          2012          2016          2020          2024+              │
│    │             │              │              │              │              │
│    ▼             ▼              ▼              ▼              ▼              │
│  ┌────┐      ┌────┐       ┌────┐        ┌────┐        ┌────┐              │
│  │Prom│      │ELK │       │Zip │        │Par │        │OTel│              │
│  │ethe│      │Stack│       │kin │        │f  │        │    │              │
│  │us  │      │    │       │    │        │    │        │    │              │
│  └────┘      └────┘       └────┘        └────┘        └────┘              │
│                                                                             │
│  Time-series  Text search   Distributed   Continuous   Unified signals     │
│  aggregation  & analytics   request flow  profiling      correlation       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Tracing Standards Comparison

| Standard | Vendor | Status | Ecosystem | Performance |
|----------|--------|--------|-----------|-------------|
| **OpenTelemetry** | CNCF | Stable | Excellent | Good |
| **OpenCensus** | Google | Deprecated | Legacy | Good |
| **OpenTracing** | CNCF | Deprecated | Legacy | Good |
| **Zipkin** | Twitter | Stable | Good | Excellent |
| **Jaeger** | Uber/CNCF | Stable | Good | Excellent |
| **AWS X-Ray** | Amazon | Proprietary | AWS only | Good |
| **Google Cloud Trace** | Google | Proprietary | GCP only | Good |

### 1.3 Tracing Systems Matrix

| System | Sampling | Storage | UI | Scale | Best For |
|--------|----------|---------|-----|-------|----------|
| **Jaeger** | Adaptive | ES/Cassandra/Kafka | Good | High | Kubernetes |
| **Zipkin** | Head/Tail | MySQL/ES/Cassandra | Good | Medium | Simple setups |
| **Tempo** | Tail-based | Object storage | Grafana | Very high | Cost-conscious |
| **Honeycomb** | Dynamic | Columnar | Excellent | Very high | Debugging |
| **Lightstep** | Dynamic | Proprietary | Excellent | Very high | Enterprise |

---

## Part II: OpenTelemetry Deep Dive

### 2.1 OpenTelemetry Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      OpenTelemetry Architecture                             │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    Application Layer                                   │   │
│  │                                                                        │   │
│  │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │   │
│  │   │  Auto-       │  │   Manual     │  │   Open       │               │   │
│  │   │  Instrumented│  │   Instrumentation  │               │   │
│  │   │              │  │              │  │   Telemetry  │               │   │
│  │   └──────┬───────┘  └──────┬───────┘  └──────┬───────┘               │   │
│  │          │                  │                  │                      │   │
│  └──────────┼──────────────────┼──────────────────┼──────────────────────┘   │
│             │                  │                  │                          │
│             ▼                  ▼                  ▼                          │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    OpenTelemetry SDK                                  │   │
│  │                                                                        │   │
│  │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │   │
│  │   │   Tracer     │  │   Meter      │  │   Logger     │               │   │
│  │   │   Provider   │  │   Provider   │  │   Provider   │               │   │
│  │   └──────┬───────┘  └──────┬───────┘  └──────┬───────┘               │   │
│  │          │                  │                  │                      │   │
│  │          ▼                  ▼                  ▼                      │   │
│  │   ┌──────────────────────────────────────────────────────────────┐    │   │
│  │   │                      Processors                               │    │   │
│  │   │  - Span processors (Batch/Simple)                             │    │   │
│  │   │  - Attribute limits                                           │    │   │
│  │   │  - Sampling                                                   │    │   │
│  │   └──────────────────────┬──────────────────────────────────────┘    │   │
│  │                          │                                             │   │
│  │                          ▼                                             │   │
│  │   ┌──────────────────────────────────────────────────────────────┐    │   │
│  │   │                    OTLP Exporter                              │    │   │
│  │   │  - gRPC/HTTP transport                                        │    │   │
│  │   │  - Compression (gzip)                                       │    │   │
│  │   │  - Retry logic                                                │    │   │
│  │   └──────────────────────┬──────────────────────────────────────┘    │   │
│  │                          │                                             │   │
│  └──────────────────────────┼────────────────────────────────────────────┘   │
│                             │                                                │
│                             ▼                                                │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    OpenTelemetry Collector                            │   │
│  │                                                                        │   │
│  │  Receivers → Processors → Exporters → Backends                        │   │
│  │                                                                        │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Span Anatomy

| Component | Description | Example |
|-----------|-------------|---------|
| **TraceID** | 128-bit unique identifier | `4bf92f3577b34da6a3ce929d0e0e4736` |
| **SpanID** | 64-bit span identifier | `00f067aa0ba902b7` |
| **ParentSpanID** | Reference to parent | `00f067aa0ba902b6` |
| **Name** | Operation name | `GET /api/users` |
| **Kind** | Span type | `Server`, `Client`, `Producer`, `Consumer`, `Internal` |
| **Attributes** | Key-value metadata | `http.method=GET` |
| **Events** | Timestamped annotations | `Processing started` |
| **Links** | Cross-trace references | `Related batch job` |
| **Status** | Error indication | `OK`, `Error` |

---

## Part III: Sampling Strategies

### 3.1 Sampling Types

| Type | When | Use Case | Complexity |
|------|------|----------|------------|
| **Head-based** | At start | Simple percentage | Low |
| **Tail-based** | After completion | Error detection | High |
| **Rate limiting** | Per time unit | Budget enforcement | Medium |
| **Probabilistic** | Statistical | Consistent sampling | Medium |
| **Adaptive** | Dynamic | Error rate-based | High |

### 3.2 Sampling Rates

| Traffic Volume | Recommended Rate | Rationale |
|----------------|------------------|-----------|
| < 100 RPS | 100% | Low volume, full visibility |
| 100-1000 RPS | 50% | Balanced visibility/cost |
| 1K-10K RPS | 10% | Cost-conscious |
| 10K+ RPS | 1-5% | Statistical representation |
| Errors | Always 100% | Never miss errors |

---

## Part IV: Go Implementation

### 4.1 Configuration

```go
type Config struct {
    ServiceName           string
    ServiceVersion        string
    Environment           string
    TraceExporterEndpoint string
    TraceSamplingRate     float64  // 0.0 to 1.0
}

// Parent-based sampling with ratio
sampler := sdktrace.ParentBased(sdktrace.TraceIDRatioBased(0.1))
```

### 4.2 Context Propagation

| Format | Standard | Use Case |
|--------|----------|----------|
| **W3C Trace Context** | Recommendation | HTTP services |
| **B3** | OpenZipkin | Legacy Zipkin |
| **Jaeger** | Uber | Legacy Jaeger |
| **AWS X-Ray** | Amazon | AWS services |

---

## Part V: References

| Resource | URL | Description |
|----------|-----|-------------|
| OpenTelemetry | https://opentelemetry.io | Official site |
| W3C Trace Context | https://www.w3.org/TR/trace-context/ | Standard spec |
| Jaeger | https://www.jaegertracing.io | Tracing system |
| Zipkin | https://zipkin.io | Tracing system |

---

*This document reflects SOTA in distributed tracing as of April 2026.*
