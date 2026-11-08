# ADR-003: Label Cardinality Management

**Date**: 2026-04-05  
**Status**: Accepted  
**Deciders**: Phenotype Engineering Team

## Context

Label cardinality (the number of unique time series) directly impacts:

1. **Memory usage**: Each series consumes RAM in Prometheus
2. **Query performance**: High cardinality = slow queries
3. **Storage costs**: More series = more storage
4. **Network overhead**: More data to scrape

We need a strategy to manage cardinality while maintaining useful metrics.

## Decision Drivers

- **Cost**: Minimize infrastructure costs
- **Performance**: Maintain fast queries
- **Utility**: Keep metrics useful for debugging
- **Safety**: Prevent cardinality explosions

## Options Considered

### Option A: Hard Cardinality Limits (Selected)

Enforce cardinality limits at multiple levels:

```
Per-metric series limit: 10,000
Per-service series limit: 100,000
Global series limit: 1,000,000
```

With automatic dropping of high-cardinality labels:

```go
// Drop high-cardinality labels
labels := prometheus.Labels{
    "user_id":    "DROP",     // Too high cardinality
    "user_tier":  "premium",  // OK: low cardinality
    "request_id": "DROP",    // Unique per request
    "status":     "200",      // OK: bounded values
}
```

**Pros**:
- Predictable resource usage
- Automatic protection
- Clear boundaries for developers

**Cons**:
- May drop useful data
- Requires monitoring of dropped metrics

### Option B: Cardinality-Based Sampling

Sample high-cardinality metrics at reduced rate:

```
Cardinality < 100: 100% sample
Cardinality < 1,000: 10% sample
Cardinality < 10,000: 1% sample
Cardinality > 10,000: 0.1% sample
```

**Pros**:
- Retains some high-cardinality data
- Statistical representation

**Cons**:
- Complex to implement correctly
- Statistical analysis required
- May miss rare events

### Option C: No Limits (Trust Developers)

Rely on code review and education.

**Pros**:
- Maximum flexibility
- Simple implementation

**Cons**:
- Risk of production incidents
- Reactive rather than proactive
- Hard to enforce consistently

## Decision

**Implement hard cardinality limits with automatic label dropping and developer alerting.**

Implementation:

```go
// CardinalityGuard monitors and enforces limits
type CardinalityGuard struct {
    metricLimits   map[string]int
    serviceLimit   int
    droppedMetrics prometheus.Counter
}

func (g *CardinalityGuard) SanitizeLabels(metric string, labels map[string]string) map[string]string {
    if g.estimateCardinality(metric, labels) > g.metricLimits[metric] {
        // Drop high-cardinality labels
        for key := range labels {
            if g.isHighCardinality(key, labels[key]) {
                delete(labels, key)
                g.droppedMetrics.Inc()
            }
        }
    }
    return labels
}
```

## Consequences

### Positive
- Protected from cardinality explosions
- Predictable infrastructure costs
- Automatic enforcement

### Negative
- May lose debugging data
- Requires tuning of limits
- Need monitoring for drops

## Best Practices

### DO
```go
// Use low-cardinality labels
http_requests_total{status="200", path="/api/users"}
http_requests_total{status="500", path="/api/users"}
```

### DON'T
```go
// Avoid high-cardinality labels
http_requests_total{user_id="12345"}        // BAD
http_requests_total{request_id="abc123"}    // BAD
http_requests_total{timestamp="1234567890"} // BAD
```

## Monitoring

Alert when:
- Series count > 80% of limit
- Dropped metrics > 0
- New high-cardinality labels detected

## References

- https://www.robustperception.io/cardinality-is-key/
- https://prometheus.io/docs/practices/instrumentation/#do-not-overuse-labels

---

*Cardinality limits are enforced at scrape time by default.*
