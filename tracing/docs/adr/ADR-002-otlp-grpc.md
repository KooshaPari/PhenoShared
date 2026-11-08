# ADR-002: OTLP gRPC Export

**Date**: 2026-04-05  
**Status**: Accepted  
**Deciders**: Phenotype Engineering Team

## Context

OpenTelemetry supports multiple export protocols. We need to select the primary export mechanism for trace data.

## Decision Drivers

- **Performance**: Efficient transmission
- **Reliability**: Delivery guarantees
- **Compatibility**: Collector support
- **Security**: TLS and authentication

## Options Considered

### Option A: OTLP/gRPC (Selected)

**Pros**:
- Binary protobuf (efficient)
- HTTP/2 multiplexing
- Streaming support
- Built-in compression
- Industry standard

**Cons**:
- Firewall may block gRPC
- More complex than HTTP

### Option B: OTLP/HTTP

**Pros**:
- Firewall friendly
- Simple to debug
- Standard port 80/443

**Cons**:
- Less efficient than gRPC
- No streaming

### Option C: Jaeger Thrift

**Pros**:
- Direct Jaeger ingestion
- Compact format

**Cons**:
- Legacy protocol
- Limited support

## Decision

**Use OTLP/gRPC as the primary export protocol with HTTP fallback.**

## Configuration

```go
traceExporter, err := otlptracegrpc.New(ctx,
    otlptracegrpc.WithEndpoint("collector:4317"),
    otlptracegrpc.WithInsecure(), // Or TLS for production
)
```

## Consequences

### Positive
- Optimal performance
- Feature-rich protocol
- Future-proof

### Negative
- May need HTTP fallback in restricted environments
- gRPC dependencies

---

*OTLP/gRPC is the default export protocol for Phenotype.*
