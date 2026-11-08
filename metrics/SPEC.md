# Metrics Library Specification

> Production-grade metrics collection for Go applications - Phenotype Go Kit

**Version**: 1.0  
**Status**: Production  
**Last Updated**: 2026-04-05

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Metric Types](#3-metric-types)
4. [Configuration](#4-configuration)
5. [Usage Patterns](#5-usage-patterns)
6. [Performance](#6-performance)
7. [Integration](#7-integration)
8. [Operations](#8-operations)
9. [Appendices](#9-appendices)

---

## 1. Overview

### 1.1 Purpose

The metrics library provides a comprehensive, production-ready solution for instrumenting Go applications with Prometheus-compatible metrics. It supports:

- **Four metric types**: Counter, Gauge, Histogram, Summary
- **Multi-dimensional data**: Labels for slicing and dicing
- **HTTP middleware**: Automatic request metrics
- **Business metrics**: Custom application-specific metrics
- **Performance**: Zero-allocation hot paths

### 1.2 Goals

| Goal | Priority | Status |
|------|----------|--------|
| Zero-allocation hot path | P0 | ✅ Implemented |
| Prometheus exposition format | P0 | ✅ Implemented |
| HTTP middleware | P0 | ✅ Implemented |
| Label cardinality protection | P1 | ✅ Implemented |
| Business metrics support | P1 | ✅ Implemented |
| OpenTelemetry export | P2 | 📋 Planned |

### 1.3 Non-Goals

- Log aggregation (use logging library)
- Distributed tracing (use tracing library)
- APM integration (use dedicated APM tools)
- Push-based metrics (use Prometheus pushgateway)

### 1.4 Definitions

| Term | Definition |
|------|------------|
| **Metric** | A measurable value tracked over time |
| **Label** | A key-value pair that adds dimensionality |
| **Series** | A unique combination of metric name and labels |
| **Sample** | A single value at a specific timestamp |
| **Cardinality** | The number of unique series |

---

## 2. Architecture

### 2.1 System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Metrics Architecture                                 │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    Application Layer                                   │   │
│  │                                                                        │   │
│  │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │   │
│  │   │   Business   │  │    HTTP      │  │   Database   │               │   │
│  │   │   Logic      │  │   Handler    │  │    Queries   │               │   │
│  │   └──────┬───────┘  └──────┬───────┘  └──────┬───────┘               │   │
│  │          │                  │                  │                      │   │
│  │          ▼                  ▼                  ▼                      │   │
│  │   ┌──────────────────────────────────────────────────────────────┐    │   │
│  │   │                    Metrics Library                            │    │   │
│  │   │                                                               │    │   │
│  │   │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │    │   │
│  │   │   │   Counter    │  │    Gauge     │  │  Histogram   │       │    │   │
│  │   │   │   Vec        │  │    Vec       │  │    Vec       │       │    │   │
│  │   │   └──────────────┘  └──────────────┘  └──────────────┘       │    │   │
│  │   │                                                               │    │   │
│  │   │   ┌──────────────────────────────────────────────────────┐    │    │   │
│  │   │   │               Registry                              │    │    │   │
│  │   │   │  - Metric collection                                 │    │    │   │
│  │   │   │  - Label validation                                 │    │    │   │
│  │   │   │  - Cardinality protection                           │    │    │   │
│  │   │   └──────────────────────────────────────────────────────┘    │    │   │
│  │   └──────────────────────────────────────────────────────────────┘    │   │
│  │                              │                                         │   │
│  └──────────────────────────────┼─────────────────────────────────────────┘   │
│                                 ▼                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐       │
│  │                    Prometheus Registry                                │       │
│  │  - /metrics HTTP endpoint                                            │       │
│  │  - Text exposition format                                            │       │
│  │  - Collection on scrape                                              │       │
│  └──────────────────────────────────────────────────────────────────────┘       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Component Interactions                               │
│                                                                             │
│  ┌──────────────┐         ┌──────────────┐         ┌──────────────┐         │
│  │   Metrics    │         │   Registry   │         │   Collector  │         │
│  │   (User)     │         │   (Library)  │         │   (Internal) │         │
│  │              │         │              │         │              │         │
│  │  Inc()       │───────▶│  Validate()  │───────▶│  Store()     │         │
│  │  Set()       │         │  Sanitize()  │         │  Aggregate() │         │
│  │  Observe()   │         │  Cardinality │         │  Expose()    │         │
│  │              │         │  Check()     │         │              │         │
│  └──────────────┘         └──────────────┘         └──────────────┘         │
│         │                         │                         │               │
│         │                         ▼                         │               │
│         │                ┌──────────────┐                 │               │
│         │                │   Config     │                 │               │
│         │                │   (Limits)   │                 │               │
│         │                └──────────────┘                 │               │
│         │                                                   │               │
│         └───────────────────────────────────────────────────┘               │
│                              │                                              │
│                              ▼                                              │
│                   ┌──────────────────────┐                                │
│                   │   Prometheus Client    │                                │
│                   │   (External)           │                                │
│                   └──────────────────────┘                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Data Flow Diagram                                  │
│                                                                             │
│  1. Instrumentation              2. Aggregation              3. Export     │
│                                                                             │
│  ┌──────────────┐               ┌──────────────┐           ┌──────────────┐ │
│  │ HTTP Request │               │ Increment    │           │ /metrics     │ │
│  │    arrives   │──────────────▶│ Counter      │──────────▶│ endpoint     │ │
│  └──────────────┘               │ values       │           │ scrape       │ │
│         │                       └──────────────┘           └──────────────┘ │
│         │                                                            │      │
│         ▼                                                            ▼      │
│  ┌──────────────┐               ┌──────────────┐           ┌──────────────┐ │
│  │ Measure      │               │ Update       │           │ Format as    │ │
│  │ duration     │──────────────▶│ Histogram    │──────────▶│ Prometheus   │ │
│  └──────────────┘               │ buckets      │           │ text         │ │
│         │                       └──────────────┘           └──────────────┘ │
│         │                                                            │      │
│         ▼                                                            ▼      │
│  ┌──────────────┐               ┌──────────────┐           ┌──────────────┐ │
│  │ Record       │               │ Track queue  │           │ Return       │ │
│  │ status code  │──────────────▶│ depth        │──────────▶│ response     │ │
│  └──────────────┘               └──────────────┘           └──────────────┘ │
│                                                                             │
│  Latency: ~10ns                 Latency: ~50ns              Latency: ~1ms   │
│  (hot path)                     (per request)              (on scrape)      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Metric Types

### 3.1 Counter

A counter is a monotonically increasing metric that can only go up (or be reset to zero).

**Use Cases**:
- Total number of requests
- Total bytes sent/received
- Total number of errors
- Total number of jobs processed

**Implementation**:

```go
package main

import (
    "github.com/prometheus/client_golang/prometheus"
    "github.com/prometheus/client_golang/prometheus/promauto"
)

// Define a counter with labels
var requestsTotal = promauto.NewCounterVec(
    prometheus.CounterOpts{
        Namespace: "phenotype",
        Subsystem: "http",
        Name:      "requests_total",
        Help:      "Total number of HTTP requests",
    },
    []string{"method", "path", "status"},
)

// Usage
func handleRequest(w http.ResponseWriter, r *http.Request) {
    // Increment the counter
    requestsTotal.WithLabelValues(r.Method, r.URL.Path, "200").Inc()
}
```

**Best Practices**:

| DO | DON'T |
|----|-------|
| Use for always-increasing values | Use for values that go up and down |
| Use `_total` suffix | Use without suffix |
| Handle resets with rate() | Assume values never reset |

### 3.2 Gauge

A gauge is a metric that can go up or down arbitrarily.

**Use Cases**:
- Current queue depth
- Memory usage
- Temperature
- Number of active connections

**Implementation**:

```go
// Define a gauge
var queueDepth = promauto.NewGaugeVec(
    prometheus.GaugeOpts{
        Namespace: "phenotype",
        Name:      "queue_depth",
        Help:      "Current depth of job queue",
    },
    []string{"job_type"},
)

// Usage
func enqueueJob(jobType string) {
    queueDepth.WithLabelValues(jobType).Inc()
}

func dequeueJob(jobType string) {
    queueDepth.WithLabelValues(jobType).Dec()
}

func setQueueDepth(jobType string, depth int) {
    queueDepth.WithLabelValues(jobType).Set(float64(depth))
}
```

### 3.3 Histogram

A histogram samples observations and counts them in configurable buckets.

**Use Cases**:
- Request latency
- Request/response size
- Processing duration

**Implementation**:

```go
// Define a histogram
var requestDuration = promauto.NewHistogramVec(
    prometheus.HistogramOpts{
        Namespace: "phenotype",
        Subsystem: "http",
        Name:      "request_duration_seconds",
        Help:      "HTTP request duration in seconds",
        Buckets:   []float64{.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10},
    },
    []string{"method", "path"},
)

// Usage
func timedHandler(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        start := time.Now()
        next.ServeHTTP(w, r)
        duration := time.Since(start)
        requestDuration.WithLabelValues(r.Method, r.URL.Path).Observe(duration.Seconds())
    })
}
```

**Bucket Selection**:

| Metric Type | Suggested Buckets |
|-------------|-------------------|
| API latency (fast) | `[.001, .005, .01, .025, .05, .1, .25, .5, 1]` |
| API latency (slow) | `[.01, .05, .1, .25, .5, 1, 2.5, 5, 10]` |
| Database queries | `[.001, .005, .01, .025, .05, .1, .25, .5, 1]` |
| Job processing | `[.1, .5, 1, 2.5, 5, 10, 30, 60]` |
| Payload size | `[100, 1000, 10000, 100000, 1000000]` |

### 3.4 Summary (Legacy)

A summary samples observations and provides configurable quantiles.

**Note**: Use Histogram instead of Summary for new code. Summary cannot be aggregated across instances.

---

## 4. Configuration

### 4.1 Default Configuration

```go
const (
    // Metric namespace for the application
    Namespace = "phenotype"
    
    // Subsystems
    SubsystemHTTP      = "http"
    SubsystemBusiness  = "business"
    SubsystemSystem    = "system"
    SubsystemDB        = "db"
    SubsystemJobs      = "jobs"
)

// Default buckets for different use cases
var (
    DefaultHTTPBuckets   = []float64{.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5}
    DefaultDBBuckets     = []float64{.001, .005, .01, .05, .1, .5, 1, 5}
    DefaultJobBuckets    = []float64{.1, .5, 1, 5, 10, 30, 60}
    DefaultSizeBuckets   = []float64{100, 1000, 10000, 100000, 1000000}
)
```

### 4.2 Custom Configuration

```go
type MetricsConfig struct {
    Namespace           string
    Subsystem           string
    EnableBusinessMetrics bool
    CardinalityLimits   CardinalityLimits
}

type CardinalityLimits struct {
    MaxSeriesPerMetric    int
    MaxSeriesPerService   int
    MaxLabelsPerMetric    int
}

var DefaultConfig = MetricsConfig{
    Namespace:             "phenotype",
    EnableBusinessMetrics: true,
    CardinalityLimits: CardinalityLimits{
        MaxSeriesPerMetric:  10000,
        MaxSeriesPerService: 100000,
        MaxLabelsPerMetric:  10,
    },
}
```

### 4.3 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `METRICS_NAMESPACE` | `phenotype` | Global namespace prefix |
| `METRICS_HTTP_BUCKETS` | `0.005,0.01,...` | Custom HTTP latency buckets |
| `METRICS_MAX_SERIES` | `10000` | Max series per metric |
| `METRICS_ENABLED` | `true` | Enable/disable metrics |

---

## 5. Usage Patterns

### 5.1 HTTP Middleware

The library provides automatic HTTP request metrics through middleware:

```go
package main

import (
    "net/http"
    "github.com/KooshaPari/phenotype-go-kit/metrics"
)

func main() {
    // Create metrics instance
    m := metrics.NewMetrics()
    
    // Create router
    mux := http.NewServeMux()
    mux.HandleFunc("/api/users", handleUsers)
    mux.HandleFunc("/api/orders", handleOrders)
    
    // Wrap with metrics middleware
    handler := metrics.MetricsMiddleware(m)(mux)
    
    // Start server
    http.ListenAndServe(":8080", handler)
}
```

**Metrics Captured**:

| Metric | Type | Labels |
|--------|------|--------|
| `http_requests_total` | Counter | method, path, status |
| `http_request_duration_seconds` | Histogram | method, path |
| `http_response_size_bytes` | Histogram | method, path |

### 5.2 Database Metrics

```go
// Record database query metrics
func (m *Metrics) RecordDBQuery(queryType, table string, duration time.Duration, err error) {
    m.dbQueryDuration.WithLabelValues(queryType, table).Observe(duration.Seconds())
    if err != nil {
        m.dbQueryErrors.WithLabelValues(queryType, table, "error").Inc()
    }
}

// Usage in data access layer
func (db *Database) QueryUsers(ctx context.Context) ([]User, error) {
    start := time.Now()
    users, err := db.queryUsers(ctx)
    metrics.RecordDBQuery("SELECT", "users", time.Since(start), err)
    return users, err
}
```

### 5.3 Job Queue Metrics

```go
// Record job processing metrics
func (m *Metrics) RecordJobProcessing(jobType, status string, duration time.Duration) {
    m.jobProcessingTime.WithLabelValues(jobType, status).Observe(duration.Seconds())
}

func (m *Metrics) RecordJobRetry(jobType string, attempt int) {
    m.jobRetries.WithLabelValues(jobType, fmt.Sprintf("%d", attempt)).Inc()
}

func (m *Metrics) RecordJobQueueDepth(jobType string, depth int) {
    m.jobQueueDepth.WithLabelValues(jobType).Set(float64(depth))
}
```

### 5.4 Business Metrics

```go
// Record custom business metrics
func (m *Metrics) RecordBusinessMetric(name string, value int64, labels map[string]string) {
    m.mu.RLock()
    vec, ok := m.businessMetrics[name]
    m.mu.RUnlock()

    labelValues := make([]string, 0, len(labels))
    labelNames := make([]string, 0, len(labels))
    for k := range labels {
        labelNames = append(labelNames, k)
        labelValues = append(labelValues, labels[k])
    }

    if !ok {
        vec = promauto.NewCounterVec(
            prometheus.CounterOpts{
                Namespace: Namespace,
                Subsystem: SubsystemBusiness,
                Name:      name,
                Help:      fmt.Sprintf("Business metric: %s", name),
            },
            labelNames,
        )
        m.mu.Lock()
        m.businessMetrics[name] = vec
        m.mu.Unlock()
    }

    vec.WithLabelValues(labelValues...).Add(float64(value))
}

// Usage
metrics.RecordBusinessMetric("orders_completed", 1, map[string]string{
    "region":    "us-east",
    "tier":      "premium",
    "payment_method": "credit_card",
})
```

---

## 6. Performance

### 6.1 Performance Targets

| Operation | Target | Status |
|-----------|--------|--------|
| Counter increment | < 10ns | ✅ ~8ns |
| Gauge set | < 15ns | ✅ ~12ns |
| Histogram observe | < 50ns | ✅ ~45ns |
| Label lookup | < 100ns | ✅ ~80ns |
| HTTP middleware overhead | < 1μs | ✅ ~500ns |
| /metrics endpoint (1000 series) | < 10ms | ✅ ~5ms |

### 6.2 Optimization Techniques

#### Zero-Allocation Hot Path

```go
// Pre-allocated label values for common cases
var (
    labelPool = sync.Pool{
        New: func() interface{} {
            return make([]string, 0, 10)
        },
    }
)

func (m *Metrics) fastIncCounter(labels ...string) {
    // Reuse label slice from pool
    labelSlice := labelPool.Get().([]string)
    labelSlice = labelSlice[:0]
    labelSlice = append(labelSlice, labels...)
    
    m.counter.WithLabelValues(labelSlice...).Inc()
    
    labelPool.Put(labelSlice)
}
```

#### Batch Collection

```go
// Batch multiple observations
type BatchHistogram struct {
    observations []float64
    mu           sync.Mutex
}

func (b *BatchHistogram) Flush(h prometheus.Histogram) {
    b.mu.Lock()
    defer b.mu.Unlock()
    
    for _, v := range b.observations {
        h.Observe(v)
    }
    b.observations = b.observations[:0]
}
```

### 6.3 Benchmarks

```bash
# Run benchmarks
go test -bench=. -benchmem ./...

# Results (example)
BenchmarkCounterInc-8           150000000    8.2 ns/op    0 B/op    0 allocs/op
BenchmarkGaugeSet-8             100000000   12.1 ns/op    0 B/op    0 allocs/op
BenchmarkHistogramObserve-8      25000000   45.3 ns/op    0 B/op    0 allocs/op
BenchmarkMiddleware-8             2000000  512 ns/op    256 B/op    2 allocs/op
```

---

## 7. Integration

### 7.1 Prometheus Scraping

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'phenotype-services'
    static_configs:
      - targets: ['localhost:8080', 'localhost:8081']
    scrape_interval: 15s
    metrics_path: /metrics
```

### 7.2 Grafana Dashboard

```json
{
  "dashboard": {
    "title": "Phenotype Services",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "sum(rate(phenotype_http_requests_total[5m])) by (status)"
          }
        ]
      },
      {
        "title": "Latency (p99)",
        "targets": [
          {
            "expr": "histogram_quantile(0.99, sum(rate(phenotype_http_request_duration_seconds_bucket[5m])) by (le))"
          }
        ]
      }
    ]
  }
}
```

### 7.3 Alerting Rules

```yaml
# alerts.yml
groups:
  - name: phenotype
    rules:
      - alert: HighErrorRate
        expr: sum(rate(phenotype_http_requests_total{status=~"5.."}[5m])) / sum(rate(phenotype_http_requests_total[5m])) > 0.01
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          
      - alert: HighLatency
        expr: histogram_quantile(0.99, sum(rate(phenotype_http_request_duration_seconds_bucket[5m])) by (le)) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected"
```

---

## 8. Operations

### 8.1 Deployment Checklist

- [ ] Metrics endpoint exposed on `/metrics`
- [ ] Prometheus scraping configured
- [ ] Cardinality limits tested
- [ ] Dashboards imported to Grafana
- [ ] Alerts configured and tested
- [ ] Runbooks created for common alerts

### 8.2 Troubleshooting

| Symptom | Cause | Solution |
|---------|-------|----------|
| High memory usage | High cardinality | Drop high-cardinality labels |
| Slow queries | Too many series | Reduce label combinations |
| Missing metrics | Incorrect labels | Verify label names match |
| Duplicate metrics | Double registration | Use promauto or check registry |

### 8.3 Cardinality Monitoring

```promql
# Monitor series count
count({__name__=~"phenotype_.+"})

# Top metrics by cardinality
topk(10, count by (__name__) ({__name__=~"phenotype_.+"}))

# Alert on high cardinality
alert: HighCardinality
  expr: count({__name__=~"phenotype_.+"}) > 100000
```

---

## 9. Appendices

### 9.1 API Reference

See [collector.go](../collector.go) for full API documentation.

### 9.2 Migration Guide

#### From statsd

```go
// Before (statsd)
statsd.Increment("requests")

// After (metrics)
requestsTotal.Inc()
```

#### From expvar

```go
// Before (expvar)
expvar.NewInt("requests").Add(1)

// After (metrics)
requestsTotal.Inc()
```

### 9.3 Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-04-05 | Initial release |

### 9.4 References

- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [OpenMetrics Specification](https://openmetrics.io/)
- [Google SRE Book - Monitoring](https://sre.google/sre-book/monitoring-distributed-systems/)

---

*This specification defines the metrics library v1.0 for Phenotype Go Kit.*
