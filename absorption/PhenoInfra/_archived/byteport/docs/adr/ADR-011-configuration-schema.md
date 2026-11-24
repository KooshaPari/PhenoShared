# ADR-011: Configuration Schema Design

**Document ID:** BYTEPORT_ADR_011  
**Status:** Accepted  
**Last Updated:** 2026-04-04  
**Author:** BytePort Architecture Team

---

## Context

BytePort supports diverse deployment scenarios from embedded devices to cloud servers. We need a flexible configuration system that:
1. Supports multiple configuration sources (file, env, CLI)
2. Validates configuration at startup
3. Provides sensible defaults
4. Supports environment-specific overrides

## Decision

We adopt a **hierarchical configuration with layered sources**:

```
Configuration Sources (highest to lowest priority):
+-----------------------------------------------------------------------------+
|                                                                             |
|  1. Environment Variables (BYTEPORT_* prefix)                               |
|  2. CLI Arguments                                                            |
|  3. Configuration File (byteport.toml)                                      |
|  4. Default Values                                                          |
|                                                                             |
+-----------------------------------------------------------------------------+
```

## Configuration Structure

```rust
#[derive(Debug, Clone, serde::Deserialize)]
pub struct BytePortConfig {
    pub client: Option<ClientConfig>,
    pub server: Option<ServerConfig>,
    pub schema_registry: SchemaRegistryConfig,
    pub encoders: EncoderConfig,
    pub compression: CompressionConfig,
    pub transport: TransportConfig,
    pub load_balancer: Option<LoadBalancerConfig>,
    pub security: SecurityConfig,
    pub observability: ObservabilityConfig,
}

#[derive(Debug, Clone, serde::Deserialize)]
pub struct ClientConfig {
    pub server_address: SocketAddr,
    pub transport: TransportId,
    pub default_encoder: EncoderId,
    pub compression: Option<CompressionId>,
    pub connect_timeout: Duration,
    pub request_timeout: Duration,
    pub max_retries: u32,
    pub retry_backoff: Duration,
}

#[derive(Debug, Clone, serde::Deserialize)]
pub struct ServerConfig {
    pub listen_address: SocketAddr,
    pub transport: TransportId,
    pub max_connections: usize,
    pub request_timeout: Duration,
    pub max_frame_size: usize,
}
```

## TOML Configuration Example

```toml
[server]
listen_address = "0.0.0.0:8080"
transport = "tcp"
max_connections = 10000
request_timeout = "30s"
max_frame_size = 16777216

[client]
server_address = "127.0.0.1:8080"
transport = "tcp"
default_encoder = "protobuf"
compression = "lz4"
connect_timeout = "5s"
request_timeout = "30s"
max_retries = 3
retry_backoff = "100ms"

[schema_registry]
schema_path = "./schemas"
auto_reload = true
default_compatibility = "backward"
remote_url = "https://registry.example.com"
sync_interval = "60s"

[encoders]
default_encoder = "protobuf"
zero_copy_threshold = 10240

[encoders.protobuf]
max_message_size = 1048576

[encoders.flatbuffers]
skip_validate_root = false

[compression]
enabled = true
default_algorithm = "lz4"
min_size = 1024

[compression.levels]
lz4_level = 0
zstd_level = 3
brotli_level = 4

[transport.tcp]
nodelay = true
keepalive = "30s"
send_buffer_size = 65536
recv_buffer_size = 65536

[transport.quic]
max_concurrent_bidi_streams = 100
receive_window = 1048576

[transport.connection_pool]
max_connections_per_host = 10
max_idle_duration = "60s"
health_check_interval = "10s"

[load_balancer]
algorithm = "least_connections"

[load_balancer.health_check]
enabled = true
interval = "10s"
timeout = "5s"
unhealthy_threshold = 3
healthy_threshold = 2

[security.tls]
enabled = true
cert_path = "./certs/server.crt"
key_path = "./certs/server.key"
ca_cert_path = "./certs/ca.crt"

[security.replay_protection]
enabled = true
window_size = 1000
max_age = "300s"

[observability.metrics]
enabled = true
exporter = "prometheus"
endpoint = "0.0.0.0:9090"

[observability.tracing]
enabled = true
exporter = "otlp"
endpoint = "http://localhost:4317"
sample_rate = 0.1

[observability.logging]
level = "info"
format = "json"
```

## Environment Variable Mapping

```rust
pub struct EnvConfigSource;

impl EnvConfigSource {
    pub fn load() -> Result<HashMap<String, String>, EnvError> {
        // Map environment variables to config keys
        // BYTEPORT_CLIENT_SERVER_ADDRESS -> client.server_address
        // BYTEPORT_SERVER_TRANSPORT -> server.transport
        // etc.
    }
}

#[cfg(test)]
mod tests {
    fn test_env_mapping() {
        std::env::set_var("BYTEPORT_CLIENT_SERVER_ADDRESS", "127.0.0.1:9000");
        std::env::set_var("BYTEPORT_LOG_LEVEL", "debug");
        
        let env_config = EnvConfigSource::load().unwrap();
        
        assert_eq!(env_config.get("client.server_address"), Some("127.0.0.1:9000"));
        assert_eq!(env_config.get("observability.logging.level"), Some("debug"));
    }
}
```

## Configuration Validation

```rust
pub struct ConfigValidator;

impl ConfigValidator {
    pub fn validate(config: &BytePortConfig) -> Result<(), ConfigError> {
        self.validate_server_config(config.server.as_ref())?;
        self.validate_client_config(config.client.as_ref())?;
        self.validate_transport_config(&config.transport)?;
        self.validate_security_config(&config.security)?;
        Ok(())
    }
    
    fn validate_server_config(&self, config: Option<&ServerConfig>) -> Result<(), ConfigError> {
        if let Some(cfg) = config {
            if cfg.max_connections == 0 {
                return Err(ConfigError::InvalidValue { 
                    field: "server.max_connections".to_string(),
                    reason: "must be > 0".to_string(),
                });
            }
            if cfg.max_frame_size > 100_000_000 {
                return Err(ConfigError::InvalidValue {
                    field: "server.max_frame_size".to_string(),
                    reason: "exceeds maximum (100MB)".to_string(),
                });
            }
        }
        Ok(())
    }
}
```

## Consequences

**Positive:**
- TOML format is human-readable and widely supported
- Environment variable support enables container deployments
- Hierarchical structure matches mental model
- Validation catches errors early

**Negative:**
- Complex nested structure can be verbose
- Type coercion from strings requires careful handling
- Default value management across layers

---

*End of ADR-011*
