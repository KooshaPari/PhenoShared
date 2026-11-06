use std::fmt;
use std::time::Duration;

/// Base error type for all httpora-core operations.
#[derive(Debug)]
pub enum HttptoraError {
    /// Request was rejected by the rate limiter.
    RateLimited { retry_after: Duration },

    /// Circuit breaker is open; request was not sent.
    CircuitOpen,

    /// All retry attempts were exhausted.
    RetryExhausted { attempts: usize, reason: String },

    /// Request/response parsing failed.
    ParseError { detail: String },

    /// A shared-state mutex was poisoned (a thread panicked while holding the lock).
    Poisoned { detail: String },
}

impl fmt::Display for HttptoraError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            HttptoraError::RateLimited { retry_after } => {
                write!(f, "rate limited; retry after {retry_after:?}")
            }
            HttptoraError::CircuitOpen => {
                write!(f, "circuit breaker is open")
            }
            HttptoraError::RetryExhausted { attempts, reason } => {
                write!(f, "exhausted {attempts} retries; last error: {reason}")
            }
            HttptoraError::ParseError { detail } => {
                write!(f, "parse error: {detail}")
            }
            HttptoraError::Poisoned { detail } => {
                write!(f, "mutex poisoned: {detail}")
            }
        }
    }
}

impl std::error::Error for HttptoraError {}
