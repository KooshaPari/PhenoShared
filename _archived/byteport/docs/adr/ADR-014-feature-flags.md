# ADR-014: Feature Flags and Extensibility

**Document ID:** BYTEPORT_ADR_014  
**Status:** Accepted  
**Last Updated:** 2026-04-04  
**Author:** BytePort Architecture Team

---

## Context

BytePort supports diverse use cases from embedded systems with minimal resources to cloud servers with full feature requirements. We need a feature flag system that:
1. Enables compile-time optimization by excluding unused code
2. Provides clear, orthogonal feature groupings
3. Manages dependency complexity
4. Maintains API stability across feature combinations

## Decision

We implement a **modular feature flag system**:

```toml
# byteport/Cargo.toml

[features]
default = ["tcp", "protobuf", "msgpack", "lz4"]

# Transports (mutually exclusive groups)
tcp = ["tokio/net"]
quic = ["quinn", "rustls"]
udp = ["tokio/net"]
unix = ["tokio/net"]
shm = ["shared_memory"]
rdma = ["rdma-sys"]

# Encoders
protobuf = ["prost"]
msgpack = ["rmp-serde"]
flatbuffers = ["flatbuffers"]
capnp = ["capnp"]
cbor = ["ciborium"]

# Compression
lz4 = ["lz4_flex"]
zstd = ["zstd"]
snappy = ["snap"]
brotli = ["brotli"]

# Security
tls = ["rustls", "tokio-rustls"]
mtls = ["tls"]

# Observability
otel = ["opentelemetry", "opentelemetry_sdk", "opentelemetry_otlp"]
tracing = ["tracing-subscriber", "tracing"]

# Schema
schema_registry = ["serde"]

# Performance
nightly = ["portable_atomic"]
```

## Feature Groupings

| Group | Features | Default | Description |
|-------|----------|---------|-------------|
| **Core** | tcp, protobuf, lz4 | Yes | Minimum viable product |
| **Full** | All transports, all encoders | No | Maximum functionality |
| **Embedded** | no_std, cbor | No | Memory-constrained devices |
| **Performance** | flatbuffers, capnp, zstd | No | Maximum performance |
| **Security** | tls, mtls, otel | No | Enterprise security |
| **Web** | websocket | No | Browser/WebAssembly |

## Feature Definitions

### Transport Features

```rust
#[cfg(feature = "tcp")]
mod tcp_transport {
    use tokio::net::TcpStream;
    
    pub struct TcpTransport;
    // TCP implementation
}

#[cfg(feature = "quic")]
mod quic_transport {
    use quinn::Endpoint;
    
    pub struct QuicTransport;
    // QUIC implementation
}

#[cfg(feature = "unix")]
mod unix_transport {
    use tokio::net::UnixStream;
    
    pub struct UnixTransport;
    // Unix socket implementation
}
```

### Encoder Features

```rust
#[cfg(feature = "protobuf")]
mod protobuf_encoder {
    use prost::Message;
    
    pub struct ProtobufEncoder;
    
    impl Encoder for ProtobufEncoder {
        fn encode(&self, message: &dyn Message) -> Result<Bytes, EncodeError> {
            let mut buf = Vec::with_capacity(message.encoded_len());
            message.encode(&mut buf).map_err(EncodeError::Protobuf)?;
            Ok(Bytes::from(buf))
        }
    }
}

#[cfg(feature = "flatbuffers")]
mod flatbuffers_encoder {
    pub struct FlatBuffersEncoder;
    
    impl Encoder for FlatBuffersEncoder {
        fn encode(&self, message: &dyn FlatBufferMessage) -> Result<Bytes, EncodeError> {
            // Zero-copy capable implementation
        }
        
        fn supports_zero_copy(&self) -> bool { true }
    }
}
```

### Conditional Compilation Patterns

```rust
// Registry with available encoders
pub struct EncoderRegistry {
    encoders: Vec<EncoderId>,
}

impl EncoderRegistry {
    pub fn available_encoders() -> Vec<EncoderId> {
        let mut encoders = Vec::new();
        
        #[cfg(feature = "protobuf")]
        encoders.push(EncoderId::Protobuf);
        
        #[cfg(feature = "msgpack")]
        encoders.push(EncoderId::MessagePack);
        
        #[cfg(feature = "flatbuffers")]
        encoders.push(EncoderId::FlatBuffers);
        
        #[cfg(feature = "capnp")]
        encoders.push(EncoderId::CapnProto);
        
        #[cfg(feature = "cbor")]
        encoders.push(EncoderId::Cbor);
        
        encoders
    }
}
```

## Dependency Management

```toml
# Optimized dependency tree

[dependencies]
tokio = { version = "1", features = ["rt-multi-thread", "net"], optional = true }
bytes = { version = "1", features = ["serde"] }

# Encoder dependencies
prost = { version = "0.12", optional = true }
rmp-serde = { version = "1", optional = true }
flatbuffers = { version = "24", optional = true }
capnp = { version = "0.20", optional = true }
ciborium = { version = "0.2", optional = true }

# Compression dependencies
lz4_flex = { version = "0.11", optional = true, features = ["safe"] }
zstd = { version = "0.13", optional = true }
snap = { version = "1", optional = true }
brotli = { version = "5", optional = true }

# Transport dependencies
quinn = { version = "0.11", optional = true }
rustls = { version = "0.23", optional = true }

[dev-dependencies]
criterion = { version = "0.5", features = ["html_reports"] }
```

## Consequences

**Positive:**
- Minimal binary size for embedded use cases
- Clear dependency boundaries
- Compile-time optimization
- Orthogonal feature combinations

**Negative:**
- Testing all feature combinations is impractical
- Documentation must clarify feature interactions
- Some features require mutual dependencies

---

*End of ADR-014*
