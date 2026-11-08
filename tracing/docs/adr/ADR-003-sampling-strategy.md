# ADR-003: Parent-Based Sampling

**Date**: 2026-04-05  
**Status**: Accepted  
**Deciders**: Phenotype Engineering Team

## Context

Tracing all requests can be expensive. Sampling reduces data volume while maintaining representative traces.

## Decision Drivers

- **Cost**: Storage and processing expenses
- **Representativeness**: Sampled traces should be representative
- **Error visibility**: Always capture errors
- **Distributed consistency**: Same decision across services

## Options Considered

### Option A: Parent-Based + Rate (Selected)

```go
sampler := sdktrace.ParentBased(
    sdktrace.TraceIDRatioBased(0.1), // 10% sample
)
```

**Pros**:
- Respects parent decision
- Consistent sampling across trace
- Configurable rate
- Standard approach

**Cons**:
- May miss error traces
- Rate fixed per trace

### Option B: AlwaysOn

Sample everything.

**Pros**:
- Complete visibility
- Simple

**Cons**:
- Expensive at scale
- Overwhelming data

### Option C: AlwaysOff

Sample nothing (disable tracing).

**Pros**:
- Zero overhead

**Cons**:
- No visibility

### Option D: Tail-Based Sampling

Sample after trace completion based on content.

**Pros**:
- Keep interesting traces
- Error/SLA-based

**Cons**:
- Requires collector support
- Memory overhead
- Complex

## Decision

**Use parent-based sampling with 10% default rate, plus error-span capture.**

## Implementation

```go
// Default: 10% sampling
sampler := sdktrace.ParentBased(
    sdktrace.TraceIDRatioBased(0.1),
)

// Errors always sampled
if span.IsRecording() && err != nil {
    span.RecordError(err)
    // Force sample for errors
}
```

## Consequences

### Positive
- Cost-effective
- Representative samples
- Consistent across services

### Negative
- May miss slow traces without errors
- Rate needs tuning per service

---

*Sampling configuration is service-dependent and reviewed quarterly.*
