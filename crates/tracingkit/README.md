# tracingkit - Distributed Tracing Framework

Distributed tracing with OpenTelemetry support and zero-cost abstraction.

## Features

- **OpenTelemetry Integration**: W3C Trace Context, B3 propagation
- **Zero-cost Spans**: Span creation is efficient even when disabled
- **Multiple Exporters**: OTLP, Jaeger, Zipkin, Console
- **Sampling**: Head-based and tail-based sampling
- **Context Propagation**: Automatic trace context propagation

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      HEXAGONAL ARCHITECTURE                  │
├─────────────────────────────────────────────────────────────┤
│  Domain Layer                                                │
│  ├── Span (entity)                                          │
│  ├── Trace (entity)                                        │
│  ├── SpanContext (value object)                             │
│  └── Tracer trait (port)                                    │
├─────────────────────────────────────────────────────────────┤
│  Application Layer                                           │
│  ├── TracerProvider (use case)                             │
│  └── SpanProcessor (use case)                               │
├─────────────────────────────────────────────────────────────┤
│  Adapters                                                    │
│  ├── OTLPExporter, JaegerExporter, ZipkinExporter          │
│  └── W3CContextPropagator, B3Propagator                    │
└─────────────────────────────────────────────────────────────┘
```

## Usage

```rust
use tracingkit::{Tracer, Span};

let tracer = Tracer::builder()
    .with_exporter(OtlpExporter::default())
    .build()?;

let span = tracer.span("operation_name");
span.set_attribute("key", "value");
span.end();
```

## License

MIT OR Apache-2.0
