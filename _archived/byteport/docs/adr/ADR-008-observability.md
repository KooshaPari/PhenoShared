# ADR-008: Observability Framework

**Document ID:** BYTEPORT_ADR_008  
**Status:** Accepted  
**Last Updated:** 2026-04-04  
**Author:** BytePort Architecture Team

---

## Context

BytePort must provide comprehensive observability for production deployments:
- **Metrics**: Quantitative measurements for capacity planning and alerting
- **Tracing**: Request-level visibility for debugging distributed systems
- **Logging**: Structured event records for audit and troubleshooting

We need an observability system that integrates with standard tools (Prometheus, Jaeger, OpenTelemetry) while being lightweight enough for embedded use cases.

## Decision

We adopt **OpenTelemetry as the primary observability backbone** with structured logging via the `tracing` crate:

```
+------------------+     +------------------+     +------------------+
|  BytePort Code   | --> |  OpenTelemetry  | --> |  OTLP Exporter   |
|                  |     |  SDK             |     |                  |
+------------------+     +------------------+     +------------------+
         |                                                |
         v                                                v
+------------------+     +------------------+     +------------------+
|  tracing crate   | --> |  Structured      | --> |  Log Aggregator |
|  (logging)       |     |  Logs            |     |                  |
+------------------+     +------------------+     +------------------+
```

## Metrics Definition

### Serialization Metrics

| Metric | Type | Unit | Description |
|--------|------|------|-------------|
| `byteport.serialize.duration` | Histogram | seconds | Time to serialize |
| `byteport.serialize.bytes` | Histogram | bytes | Serialized size |
| `byteport.deserialize.duration` | Histogram | seconds | Time to deserialize |
| `byteport.deserialize.bytes` | Histogram | bytes | Deserialized size |
| `byteport.serialize.errors` | Counter | 1 | Serialization errors |

### Transport Metrics

| Metric | Type | Unit | Description |
|--------|------|------|-------------|
| `byteport.connection.count` | UpDownCounter | 1 | Active connections |
| `byteport.connection.created` | Counter | 1 | New connections |
| `byteport.connection.closed` | Counter | 1 | Closed connections |
| `byteport.transport.latency` | Histogram | seconds | Transport round-trip |
| `byteport.transport.errors` | Counter | 1 | Transport errors |

### Compression Metrics

| Metric | Type | Unit | Description |
|--------|------|------|-------------|
| `byteport.compression.ratio` | Histogram | ratio | Compression ratio |
| `byteport.compression.bytes.original` | Counter | bytes | Uncompressed bytes |
| `byteport.compression.bytes.compressed` | Counter | bytes | Compressed bytes |
| `byteport.compression.duration` | Histogram | seconds | Compression time |

### Schema Metrics

| Metric | Type | Unit | Description |
|--------|------|------|-------------|
| `byteport.schema.validations` | Counter | 1 | Schema validations |
| `byteport.schema.validation_errors` | Counter | 1 | Validation failures |
| `byteport.schema.lookups` | Counter | 1 | Registry lookups |
| `byteport.schema.cache.hits` | Counter | 1 | Cache hits |
| `byteport.schema.cache.misses` | Counter | 1 | Cache misses |

## Implementation

```rust
pub struct BytePortMetrics {
    meter: Meter,
    // Serialization
    serialize_duration: Histogram<f64>,
    serialize_bytes: Histogram<u64>,
    serialize_errors: Counter<u64>,
    // Transport
    connection_count: UpDownCounter<i64>,
    connection_created: Counter<u64>,
    transport_latency: Histogram<f64>,
    transport_errors: Counter<u64>,
    // Compression
    compression_ratio: Histogram<f64>,
    compression_original: Counter<u64>,
    compression_compressed: Counter<u64>,
    compression_duration: Histogram<f64>,
    // Schema
    schema_validations: Counter<u64>,
    schema_validation_errors: Counter<u64>,
    schema_lookups: Counter<u64>,
    schema_cache_hits: Counter<u64>,
    schema_cache_misses: Counter<u64>,
}

impl BytePortMetrics {
    pub fn new() -> Self {
        let meter = opentelemetry::global::meter("byteport");
        
        Self {
            serialize_duration: meter.f64_histogram("serialize.duration")
                .with_unit(Unit::new("seconds"))
                .with_description("Time to serialize a message")
                .init(),
            serialize_bytes: meter.u64_histogram("serialize.bytes")
                .with_unit(Unit::new("bytes"))
                .with_description("Size of serialized payload")
                .init(),
            serialize_errors: meter.u64_counter("serialize.errors")
                .with_description("Serialization errors")
                .init(),
            // ... initialize other metrics
        }
    }
    
    pub fn record_serialize(&self, duration: Duration, bytes: usize) {
        self.serialize_duration.record(duration.as_secs_f64(), &[]);
        self.serialize_bytes.record(bytes as u64, &[]);
    }
    
    pub fn record_error(&self, error_type: &str) {
        self.serialize_errors.add(1, &[KeyValue::new("error.type", error_type)]);
    }
}
```

## Tracing

```rust
pub struct BytePortTracer {
    tracer: Tracer,
}

impl BytePortTracer {
    pub fn new() -> Self {
        let tracer = opentelemetry::global::tracer("byteport");
        Self { tracer }
    }
    
    pub fn start_request_span(&self, schema_id: SchemaId, encoder_id: EncoderId) -> Span {
        self.tracer
            .span_builder("byteport.request")
            .with_attribute(KeyValue::new("byteport.schema_id", schema_id as i64))
            .with_attribute(KeyValue::new("byteport.encoder_id", encoder_id as i64))
            .start(&self.tracer)
    }
    
    pub fn start_encode_span(&self, encoder_id: EncoderId) -> Span {
        self.tracer
            .span_builder("byteport.encode")
            .with_attribute(KeyValue::new("byteport.encoder_id", encoder_id as i64))
            .start(&self.tracer)
    }
    
    pub fn start_decode_span(&self, encoder_id: EncoderId) -> Span {
        self.tracer
            .span_builder("byteport.decode")
            .with_attribute(KeyValue::new("byteport.encoder_id", encoder_id as i64))
            .start(&self.tracer)
    }
    
    pub fn start_transport_span(&self, transport_id: TransportId, operation: &str) -> Span {
        self.tracer
            .span_builder(format!("byteport.transport.{}", operation))
            .with_attribute(KeyValue::new("byteport.transport_id", transport_id as i64))
            .start(&self.tracer)
    }
}
```

## Structured Logging

```rust
use tracing::{info, warn, error, debug};

pub fn init_logging(config: &LoggingConfig) {
    let level = match config.level {
        LogLevel::Trace => tracing::Level::TRACE,
        LogLevel::Debug => tracing::Level::DEBUG,
        LogLevel::Info => tracing::Level::INFO,
        LogLevel::Warn => tracing::Level::WARN,
        LogLevel::Error => tracing::Level::ERROR,
    };
    
    let subscriber = tracing_subscriber::fmt()
        .with_max_level(level)
        .with_target(false)
        .with_thread_ids(true)
        .with_file(true)
        .with_line_number(true);
    
    match config.format {
        LogFormat::Json => {
            subscriber.json().init();
        }
        LogFormat::Text => {
            subscriber.init();
        }
    }
}

// Usage examples
info!(
    schema_id = %message.schema_id(),
    encoder = %encoder.id(),
    size = payload.len(),
    "Message encoded"
);

warn!(
    node_id = %node.id,
    latency_ms = latency.as_millis(),
    "Node latency degraded"
);

error!(
    error = %error,
    schema_id = %schema_id,
    "Deserialization failed"
);
```

## Export Configuration

```rust
#[derive(Debug, Clone)]
pub struct ObservabilityConfig {
    pub metrics: MetricsConfig,
    pub tracing: TracingConfig,
    pub logging: LoggingConfig,
}

#[derive(Debug, Clone)]
pub struct MetricsConfig {
    pub enabled: bool,
    pub exporter: MetricsExporter,
    pub endpoint: Option<String>,
    pub interval: Duration,
}

#[derive(Debug, Clone)]
pub enum MetricsExporter {
    Prometheus,
    Otlp,
    Statsd,
}

impl MetricsConfig {
    pub fn install(&self) -> Result<(), ObservabilityError> {
        match self.exporter {
            MetricsExporter::Prometheus => {
                prometheus::register(&self.metrics)?;
            }
            MetricsExporter::Otlp => {
                let exporter = otlp_exporter(&self.endpoint)?;
                exporter.install()?;
            }
            MetricsExporter::Statsd => {
                // statsd exporter
            }
        }
        Ok(())
    }
}
```

## Consequences

**Positive:**
- OpenTelemetry provides vendor-neutral observability
- Structured logging enables powerful log aggregation
- Comprehensive metrics for capacity planning
- Distributed tracing for debugging

**Negative:**
- Observability overhead (~2-5% CPU)
- Configuration complexity
- Dependencies on observability infrastructure

---

*End of ADR-008*
