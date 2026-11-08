# ADR-001: Prometheus Client Library Selection

**Date**: 2026-04-05  
**Status**: Accepted  
**Deciders**: Phenotype Engineering Team

## Context

The metrics library needs to select a client library for instrumenting Go applications. We require a solution that provides:

1. Native Prometheus exposition format support
2. Low overhead instrumentation
3. Rich metric types (Counter, Gauge, Histogram, Summary)
4. Label support for multi-dimensional data
5. Active maintenance and community support

## Decision Drivers

- **Performance**: Minimal overhead on application performance
- **Compatibility**: Native Prometheus ecosystem integration
- **Features**: Histogram buckets, custom collectors, registry management
- **Maintainability**: Active development, good documentation
- **Ecosystem**: Integration with Grafana, Alertmanager, Thanos

## Options Considered

### Option A: prometheus/client_golang (Selected)

**Pros**:
- Official Prometheus client library
- Zero-allocation hot path for common operations
- Full feature set including custom collectors
- Battle-tested at scale (used by Kubernetes, Docker)
- Excellent documentation and examples
- Active development (weekly releases)
- Native OpenMetrics support

**Cons**:
- Prometheus-specific (no direct OTel support)
- Learning curve for advanced features
- Requires understanding of metric types

### Option B: OpenTelemetry Go Metrics

**Pros**:
- Unified metrics and traces
- Vendor-neutral
- OTLP export for modern backends
- Future-proof (industry direction)

**Cons**:
- Higher overhead than prometheus/client
- Less mature than Prometheus client
- Migration complexity from existing Prometheus setups
- Smaller ecosystem of exporters

### Option C: Custom Implementation

**Pros**:
- Full control over implementation
- Optimized for specific use cases
- No external dependencies

**Cons**:
- Maintenance burden
- Risk of bugs in critical path
- No community support
- Reinventing the wheel

## Decision

**Adopt prometheus/client_golang as the primary metrics client library.**

The library provides the best balance of performance, features, and ecosystem support for our current needs. We will evaluate OpenTelemetry migration path for future consideration.

## Consequences

### Positive
- Mature, battle-tested library
- Excellent performance characteristics
- Full Prometheus ecosystem compatibility
- Rich documentation and community

### Negative
- Tight coupling to Prometheus ecosystem
- Future migration to OTel will require effort
- Need to maintain compatibility wrappers if switching

## References

- https://github.com/prometheus/client_golang
- https://prometheus.io/docs/guides/go-application/

---

*This ADR will be reviewed annually for OTel migration consideration.*
