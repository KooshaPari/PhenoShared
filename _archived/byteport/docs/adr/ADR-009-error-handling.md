# ADR-009: Error Handling Strategy

**Document ID:** BYTEPORT_ADR_009  
**Status:** Accepted  
**Last Updated:** 2026-04-04  
**Author:** BytePort Architecture Team

---

## Context

BytePort must handle errors gracefully across multiple layers (encoding, compression, transport, schema) while providing actionable error information to users and enabling automatic recovery where possible.

## Decision

We adopt a **hierarchical error model with recovery strategies**:

```rust
#[derive(Debug, thiserror::Error)]
pub enum BytePortError {
    #[error("Frame error: {0}")]
    Frame(#[from] FrameError),
    
    #[error("Encode error: {0}")]
    Encode(#[from] EncodeError),
    
    #[error("Decode error: {0}")]
    Decode(#[from] DecodeError),
    
    #[error("Transport error: {0}")]
    Transport(#[from] TransportError),
    
    #[error("Compression error: {0}")]
    Compression(#[from] CompressionError),
    
    #[error("Schema error: {0}")]
    Schema(#[from] SchemaError),
    
    #[error("Security error: {0}")]
    Security(#[from] SecurityError),
    
    #[error("Configuration error: {0}")]
    Config(#[from] ConfigError),
}

pub trait Retryable {
    fn is_retryable(&self) -> bool;
    fn retry_delay(&self, attempt: u32) -> Duration;
}

impl Retryable for BytePortError {
    fn is_retryable(&self) -> bool {
        match self {
            BytePortError::Transport(e) => e.is_retryable(),
            BytePortError::Schema(SchemaError::NotFound { .. }) => true,
            _ => false,
        }
    }
    
    fn retry_delay(&self, attempt: u32) -> Duration {
        let base = match self {
            BytePortError::Transport(TransportError::ConnectionTimeout) => 
                Duration::from_millis(100),
            BytePortError::Transport(TransportError::ConnectionRefused(_)) => 
                Duration::from_millis(500),
            _ => Duration::from_millis(100),
        };
        
        // Exponential backoff with jitter
        let exponential = base * 2u32.pow(attempt.min(6));
        let jitter = Duration::from_millis(rand::random::<u64>() % 50);
        (exponential + jitter).min(Duration::from_secs(30))
    }
}
```

## Error Recovery Matrix

| Error Type | Strategy | Retry? | Fallback |
|------------|----------|--------|----------|
| Connection Refused | Exponential backoff | Yes | Next node |
| Connection Timeout | Exponential backoff | Yes | Next node |
| Checksum Mismatch | Log + drop | No | Request retransmit |
| Invalid Magic | Log + close | No | None |
| Decode Error | Return error | No | None |
| Schema Not Found | Fetch from registry | Yes | Return error |
| Rate Limit | Backoff | Yes | Queue |
| TLS Handshake Fail | Retry with fallback | Yes | Disable TLS* |
| MAC Verification Fail | Alert + drop | No | Close |
| Replay Detected | Alert + drop | No | Close |

## Implementation

```rust
pub async fn with_retry<T, E, F, Fut>(
    config: &RetryConfig,
    operation: F,
) -> Result<T, E>
where
    F: Fn() -> Fut,
    Fut: Future<Output = Result<T, E>>,
    E: Retryable + Debug,
{
    let mut attempt = 0u32;
    let mut last_error = None;
    
    loop {
        match operation().await {
            Ok(value) => return Ok(value),
            Err(e) if e.is_retryable() && attempt < config.max_retries => {
                attempt += 1;
                let delay = e.retry_delay(attempt);
                tracing::warn!(
                    attempt = attempt,
                    delay_ms = delay.as_millis(),
                    error = ?e,
                    "Operation failed, retrying"
                );
                tokio::time::sleep(delay).await;
                last_error = Some(e);
            }
            Err(e) => {
                tracing::error!(
                    attempts = attempt,
                    error = ?e,
                    "Operation failed after retries"
                );
                return Err(e);
            }
        }
    }
}

pub struct RetryConfig {
    pub max_retries: u32,
    pub initial_backoff: Duration,
    pub max_backoff: Duration,
    pub backoff_multiplier: f64,
    pub jitter: bool,
}

impl RetryConfig {
    pub fn backoff(&self, attempt: u32) -> Duration {
        let mut backoff = self.initial_backoff * 
            (self.backoff_multiplier.powi(attempt as i32) as u32);
        backoff = backoff.min(self.max_backoff);
        
        if self.jitter {
            let jitter_ms = (rand::random::<f64>() * 0.3 * backoff.as_millis() as f64) as u64;
            backoff += Duration::from_millis(jitter_ms);
        }
        
        backoff
    }
}
```

## Error Context Propagation

```rust
#[derive(Debug)]
pub struct ErrorContext {
    pub schema_id: Option<SchemaId>,
    pub encoder_id: Option<EncoderId>,
    pub transport_id: Option<TransportId>,
    pub frame_size: Option<usize>,
    pub peer_address: Option<SocketAddr>,
    pub timestamp: SystemTime,
}

impl ErrorContext {
    pub fn attach_to_error<T: Into<BytePortError>>(&self, error: T) -> BytePortError {
        let err = error.into();
        tracing::error!(
            error = %err,
            schema_id = ?self.schema_id,
            encoder_id = ?self.encoder_id,
            transport_id = ?self.transport_id,
            frame_size = ?self.frame_size,
            peer = ?self.peer_address,
            "Error with context"
        );
        err
    }
}
```

## Consequences

**Positive:**
- Hierarchical errors enable precise error handling
- Retryable trait enables automatic recovery
- Error context aids debugging
- Clear separation between recoverable and fatal errors

**Negative:**
- Error type explosion across layers
- Retry logic adds complexity
- Backoff calculations require tuning

---

*End of ADR-009*
