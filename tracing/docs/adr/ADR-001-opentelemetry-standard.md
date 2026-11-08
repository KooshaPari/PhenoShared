# ADR-001: OpenTelemetry as Tracing Standard

**Date**: 2026-04-05  
**Status**: Accepted  
**Deciders**: Phenotype Engineering Team

## Context

The tracing library needs to select a standard for distributed tracing that provides vendor neutrality and broad ecosystem support.

## Decision Drivers

- **Vendor neutrality**: Avoid lock-in
- **Ecosystem**: Wide adoption and tooling
- **Standards**: W3C trace context support
- **Future-proof**: CNCF project stability
- **Integration**: Works with existing systems

## Options Considered

### Option A: OpenTelemetry (Selected)

**Pros**:
- CNCF project with broad support
- W3C standard compatible
- Unifies traces, metrics, logs
- Vendor-neutral OTLP protocol
- Active development

**Cons**:
- Complex configuration
- Migration effort from older systems

### Option B: Jaeger Client

**Pros**:
- Native Jaeger integration
- Simpler setup
- Good Go support

**Cons**:
- Jaeger-specific
- Maintenance mode (deprecated)
- Limited future

### Option C: Zipkin

**Pros**:
- Simple and battle-tested
- Easy to understand

**Cons**:
- Limited ecosystem
- B3 propagation only
- Feature stagnation

## Decision

**Adopt OpenTelemetry as the tracing standard.**

## Configuration

```go
type Config struct {
    ServiceName    string  // Required
    ServiceVersion string  // Optional
    Environment    string  // development, staging, production
    Endpoint       string  // OTLP collector endpoint
    SamplingRate   float64 // 0.0 to 1.0
}
```

## Consequences

### Positive
- Future-proof standard
- Broad vendor support
- Rich instrumentation libraries
- Unified observability

### Negative
- Learning curve
- Complex configuration
- Dependency on OTel ecosystem

## References

- https://opentelemetry.io
- https://www.w3.org/TR/trace-context/

---

*OpenTelemetry is the standard for all Phenotype observability.*
