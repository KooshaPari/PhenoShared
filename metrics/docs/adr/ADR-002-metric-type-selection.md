# ADR-002: Metric Type Selection Strategy

**Date**: 2026-04-05  
**Status**: Accepted  
**Deciders**: Phenotype Engineering Team

## Context

The metrics library must provide guidance on selecting appropriate metric types for different use cases. Incorrect type selection leads to:

1. Loss of information (using Counter for gauges)
2. Aggregation issues (using Summary instead of Histogram)
3. Query complexity (inconsistent naming)
4. Alerting challenges (wrong rate calculations)

## Decision Drivers

- **Correctness**: Metrics must accurately represent the measured phenomenon
- **Aggregability**: Metrics should combine meaningfully across instances
- **Queryability**: Easy to write PromQL queries
- **Alertability**: Support meaningful alerts
- **Performance**: Minimize overhead

## Options Considered

### Option A: Flexible Type Selection (Selected)

Define clear rules for type selection based on measurement characteristics:

| Measurement | Type | Example |
|-------------|------|---------|
| Always increasing | Counter | requests_total, bytes_sent |
| Current value | Gauge | queue_depth, temperature |
| Distribution | Histogram | request_duration, payload_size |
| Pre-calculated quantiles | Summary | legacy latency metrics |

**Pros**:
- Clear guidance for developers
- Optimal metric representation
- Easy aggregation and querying
- Standard Prometheus patterns

**Cons**:
- Requires training for developers
- Some edge cases need judgment

### Option B: Histogram-Only Strategy

Use Histograms for everything (with single bucket for counters/gauges).

**Pros**:
- Simplified decision making
- Single implementation path

**Cons**:
- Counter semantics lost
- Gauge values confusing in histogram
- Wasteful for simple metrics
- Poor query ergonomics

### Option C: Automatic Type Detection

Infer metric type from usage patterns.

**Pros**:
- Developer-friendly
- No decision required

**Cons**:
- Brittle heuristics
- May choose wrong type
- Hard to debug

## Decision

**Adopt flexible type selection with clear documentation and linting rules.**

Provide:
1. Decision flowchart for type selection
2. Code review checklist
3. Automated linting (prometheus-metrics-linter)
4. Documentation with examples

## Consequences

### Positive
- Accurate metric representation
- Easy to aggregate and query
- Follows Prometheus best practices
- Enables meaningful alerting

### Negative
- Requires team education
- Need for linting/tooling
- Some subjective edge cases

## Implementation

```go
// Counter - always increasing
var requestsTotal = promauto.NewCounterVec(
    prometheus.CounterOpts{
        Namespace: "phenotype",
        Subsystem: "http",
        Name:      "requests_total",
        Help:      "Total HTTP requests",
    },
    []string{"method", "path", "status"},
)

// Gauge - can go up or down
var queueDepth = promauto.NewGaugeVec(
    prometheus.GaugeOpts{
        Namespace: "phenotype",
        Name:      "queue_depth",
        Help:      "Current queue depth",
    },
    []string{"queue_name"},
)

// Histogram - distributions
var requestDuration = promauto.NewHistogramVec(
    prometheus.HistogramOpts{
        Namespace: "phenotype",
        Subsystem: "http",
        Name:      "request_duration_seconds",
        Help:      "HTTP request duration",
        Buckets:   []float64{.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10},
    },
    []string{"method", "path"},
)
```

## References

- https://prometheus.io/docs/practices/instrumentation/
- https://prometheus.io/docs/practices/histograms/

---

*This ADR applies to all services using the metrics library.*
