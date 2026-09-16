# Retry Pattern

## Overview

The Retry pattern enables transient fault handling by automatically retrying failed operations with configurable strategies.

## When to Use

- **Transient failures**: Network timeouts, temporary unavailability
- **Idempotent operations**: Safe to retry (GET, PUT with same data)
- **External dependencies**: Third-party APIs, databases, message queues
- **Non-deterministic errors**: Race conditions, temporary locks

## When NOT to Use

- **Non-idempotent operations**: POST that creates resources, charging payments
- **Permanent failures**: 404 Not Found, authentication errors
- **Resource exhaustion**: Already under high load
- **Long-running operations**: Operations > timeout window

## Retry Strategies

### 1. Fixed Backoff

```
Attempt 1: Immediate
Attempt 2: Wait 2s
Attempt 3: Wait 2s
Attempt 4: Wait 2s
```

### 2. Linear Backoff

```
Attempt 1: Immediate
Attempt 2: Wait 1s
Attempt 3: Wait 2s
Attempt 4: Wait 3s
```

### 3. Exponential Backoff (Recommended)

```
Attempt 1: Immediate
Attempt 2: Wait 1s  (2^0)
Attempt 3: Wait 2s  (2^1)
Attempt 4: Wait 4s  (2^2)
Attempt 5: Wait 8s  (2^3)
```

### 4. Exponential with Jitter

```
Attempt 1: Immediate
Attempt 2: Wait 0.8s - 1.2s (randomized)
Attempt 3: Wait 1.6s - 2.4s (randomized)
Attempt 4: Wait 3.2s - 4.8s (randomized)
```

## Phenotype Implementation

### Rust

```rust
use std::time::Duration;
use std::future::Future;
use rand::Rng;
use serde::{Deserialize, Serialize};
use tracing::{info, warn, error};

/// Types of retryable errors
pub trait RetryableError {
    fn is_retryable(&self) -> bool;
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub enum RetryStrategy {
    /// Fixed delay between retries
    Fixed { delay_ms: u64 },
    /// Linear increase: delay * attempt
    Linear { base_delay_ms: u64 },
    /// Exponential: base * 2^attempt
    Exponential { base_delay_ms: u64, max_delay_ms: u64 },
    /// Exponential with randomization
    ExponentialWithJitter { base_delay_ms: u64, max_delay_ms: u64 },
}

impl Default for RetryStrategy {
    fn default() -> Self {
        RetryStrategy::ExponentialWithJitter {
            base_delay_ms: 100,
            max_delay_ms: 10_000, // 10 seconds
        }
    }
}

#[derive(Debug, Clone)]
pub struct RetryConfig {
    /// Maximum number of attempts
    pub max_attempts: u32,
    /// Retry strategy
    pub strategy: RetryStrategy,
    /// Predicate to determine if error is retryable
    pub retry_if: fn(&dyn std::fmt::Debug) -> bool,
    /// Callback on each retry
    pub on_retry: Option<fn(u32, Duration, &dyn std::fmt::Debug)>,
}

impl Default for RetryConfig {
    fn default() -> Self {
        Self {
            max_attempts: 3,
            strategy: RetryStrategy::default(),
            retry_if: |_| true, // Default: retry all errors
            on_retry: None,
        }
    }
}

pub struct Retry;

impl Retry {
    /// Execute operation with retry logic
    pub async fn execute<F, Fut, T, E>(
        config: &RetryConfig,
        operation: F,
    ) -> Result<T, RetryError<E>>
    where
        F: Fn() -> Fut,
        Fut: Future<Output = Result<T, E>>,
        E: std::fmt::Debug,
    {
        let mut last_error = None;
        
        for attempt in 0..config.max_attempts {
            match operation().await {
                Ok(result) => {
                    if attempt > 0 {
                        info!(
                            attempt = attempt + 1,
                            "Operation succeeded after retries"
                        );
                    }
                    return Ok(result);
                }
                Err(err) => {
                    let is_retryable = (config.retry_if)(&err);
                    
                    if !is_retryable || attempt == config.max_attempts - 1 {
                        return Err(RetryError::Failed {
                            attempts: attempt + 1,
                            last_error: err,
                        });
                    }
                    
                    let delay = calculate_delay(&config.strategy, attempt);
                    
                    if let Some(callback) = config.on_retry {
                        callback(attempt + 1, delay, &err);
                    }
                    
                    warn!(
                        attempt = attempt + 1,
                        max_attempts = config.max_attempts,
                        delay_ms = delay.as_millis() as u64,
                        error = ?err,
                        "Operation failed, retrying"
                    );
                    
                    tokio::time::sleep(delay).await;
                    last_error = Some(err);
                }
            }
        }
        
        unreachable!()
    }
    
    /// Execute with context-specific retry config
    pub async fn execute_with_context<F, Fut, T, E>(
        context: RetryContext,
        operation: F,
    ) -> Result<T, RetryError<E>>
    where
        F: Fn() -> Fut,
        Fut: Future<Output = Result<T, E>>,
        E: std::fmt::Debug,
    {
        Self::execute(&context.into_config(), operation).await
    }
}

fn calculate_delay(strategy: &RetryStrategy, attempt: u32) -> Duration {
    let delay_ms = match strategy {
        RetryStrategy::Fixed { delay_ms } => *delay_ms,
        
        RetryStrategy::Linear { base_delay_ms } => {
            base_delay_ms * (attempt as u64 + 1)
        }
        
        RetryStrategy::Exponential { base_delay_ms, max_delay_ms } => {
            let delay = base_delay_ms * 2_u64.pow(attempt);
            delay.min(*max_delay_ms)
        }
        
        RetryStrategy::ExponentialWithJitter { base_delay_ms, max_delay_ms } => {
            let base = base_delay_ms * 2_u64.pow(attempt);
            let base = base.min(*max_delay_ms);
            
            // Add ±25% jitter
            let jitter = (base as f64 * 0.25) as u64;
            let min_delay = base.saturating_sub(jitter);
            let max_delay = base + jitter;
            
            rand::thread_rng().gen_range(min_delay..=max_delay)
        }
    };
    
    Duration::from_millis(delay_ms)
}

#[derive(Debug)]
pub enum RetryError<E> {
    Failed {
        attempts: u32,
        last_error: E,
    },
    Cancelled,
}

impl<E: std::fmt::Display> std::fmt::Display for RetryError<E> {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            RetryError::Failed { attempts, last_error } => {
                write!(f, "Failed after {} attempts: {}", attempts, last_error)
            }
            RetryError::Cancelled => write!(f, "Operation cancelled"),
        }
    }
}

/// Predefined contexts for common scenarios
pub enum RetryContext {
    /// API calls to external services
    ExternalAPI,
    /// Database operations
    Database,
    /// Message queue operations
    MessageQueue,
    /// Idempotent service calls
    IdempotentService,
    /// Critical operations (more retries)
    Critical,
}

impl RetryContext {
    fn into_config(self) -> RetryConfig {
        match self {
            RetryContext::ExternalAPI => RetryConfig {
                max_attempts: 3,
                strategy: RetryStrategy::ExponentialWithJitter {
                    base_delay_ms: 200,
                    max_delay_ms: 5_000,
                },
                ..Default::default()
            },
            
            RetryContext::Database => RetryConfig {
                max_attempts: 5,
                strategy: RetryStrategy::ExponentialWithJitter {
                    base_delay_ms: 100,
                    max_delay_ms: 3_000,
                },
                retry_if: |e| {
                    let error_str = format!("{:?}", e);
                    // Retry on connection errors, not on constraint violations
                    error_str.contains("connection")
                        || error_str.contains("timeout")
                        || error_str.contains("temporarily unavailable")
                },
                ..Default::default()
            },
            
            RetryContext::MessageQueue => RetryConfig {
                max_attempts: 10,
                strategy: RetryStrategy::ExponentialWithJitter {
                    base_delay_ms: 100,
                    max_delay_ms: 30_000,
                },
                ..Default::default()
            },
            
            RetryContext::IdempotentService => RetryConfig {
                max_attempts: 3,
                strategy: RetryStrategy::Fixed { delay_ms: 500 },
                ..Default::default()
            },
            
            RetryContext::Critical => RetryConfig {
                max_attempts: 10,
                strategy: RetryStrategy::ExponentialWithJitter {
                    base_delay_ms: 500,
                    max_delay_ms: 60_000,
                },
                on_retry: Some(|attempt, delay, error| {
                    phenotype_alerting::send_alert(
                        format!("Critical operation retry #{}", attempt),
                        format!("Error: {:?}, next retry in {:?}", error, delay),
                    );
                }),
                ..Default::default()
            },
        }
    }
}
```

### Usage Examples

```rust
use phenotype_retry::{Retry, RetryConfig, RetryStrategy, RetryContext};

// Basic retry with defaults
let result = Retry::execute(&RetryConfig::default(), || async {
    external_api.fetch_data().await
}).await;

// Custom exponential backoff
let config = RetryConfig {
    max_attempts: 5,
    strategy: RetryStrategy::Exponential {
        base_delay_ms: 100,
        max_delay_ms: 10_000,
    },
    retry_if: |e| {
        // Only retry on specific errors
        matches!(e, ApiError::Timeout | ApiError::RateLimited)
    },
    ..Default::default()
};

let user = Retry::execute(&config, || async {
    user_service.get_user(id).await
}).await?;

// Using predefined contexts
let payment = Retry::execute_with_context(
    RetryContext::Critical,
    || async { payment_gateway.charge(payment_request).await }
).await?;

// Database operation
let rows = Retry::execute_with_context(
    RetryContext::Database,
    || async { db.query("SELECT * FROM users").await }
).await?;
```

### Python Implementation

```python
import asyncio
import time
import random
from typing import Callable, TypeVar, Optional
from dataclasses import dataclass
from enum import Enum
from functools import wraps

T = TypeVar('T')

class RetryStrategy(Enum):
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    EXPONENTIAL_JITTER = "exponential_jitter"

@dataclass
class RetryConfig:
    max_attempts: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_JITTER
    base_delay_ms: float = 100
    max_delay_ms: float = 10_000
    retry_if: Optional[Callable[[Exception], bool]] = None

class RetryError(Exception):
    def __init__(self, message: str, attempts: int, last_error: Exception):
        super().__init__(message)
        self.attempts = attempts
        self.last_error = last_error

class Retry:
    """Retry utility with configurable strategies."""
    
    @staticmethod
    def calculate_delay(
        strategy: RetryStrategy,
        attempt: int,
        base_delay_ms: float,
        max_delay_ms: float
    ) -> float:
        """Calculate delay in seconds."""
        if strategy == RetryStrategy.FIXED:
            return base_delay_ms / 1000
        
        elif strategy == RetryStrategy.LINEAR:
            return (base_delay_ms * (attempt + 1)) / 1000
        
        elif strategy == RetryStrategy.EXPONENTIAL:
            delay = base_delay_ms * (2 ** attempt)
            return min(delay, max_delay_ms) / 1000
        
        elif strategy == RetryStrategy.EXPONENTIAL_JITTER:
            base = base_delay_ms * (2 ** attempt)
            base = min(base, max_delay_ms)
            jitter = base * 0.25
            delay = random.uniform(base - jitter, base + jitter)
            return delay / 1000
    
    @staticmethod
    async def execute(
        operation: Callable[..., T],
        config: RetryConfig = None,
        *args,
        **kwargs
    ) -> T:
        """Execute operation with retry logic."""
        config = config or RetryConfig()
        last_error = None
        
        for attempt in range(config.max_attempts):
            try:
                result = await operation(*args, **kwargs)
                
                if attempt > 0:
                    print(f"✓ Operation succeeded after {attempt + 1} attempts")
                
                return result
                
            except Exception as e:
                last_error = e
                
                # Check if we should retry
                should_retry = True
                if config.retry_if:
                    should_retry = config.retry_if(e)
                
                if not should_retry or attempt == config.max_attempts - 1:
                    raise RetryError(
                        f"Failed after {attempt + 1} attempts: {e}",
                        attempt + 1,
                        e
                    ) from e
                
                # Calculate and wait
                delay = Retry.calculate_delay(
                    config.strategy,
                    attempt,
                    config.base_delay_ms,
                    config.max_delay_ms
                )
                
                print(f"⚠ Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s...")
                await asyncio.sleep(delay)
        
        raise RetryError(
            f"Failed after {config.max_attempts} attempts",
            config.max_attempts,
            last_error
        )
    
    @staticmethod
    def with_retry(config: RetryConfig = None):
        """Decorator for retry functionality."""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                return await Retry.execute(func, config, *args, **kwargs)
            return wrapper
        return decorator

# Predefined configs
class RetryPolicies:
    """Common retry policies."""
    
    API_CALLS = RetryConfig(
        max_attempts=3,
        strategy=RetryStrategy.EXPONENTIAL_JITTER,
        base_delay_ms=200,
        max_delay_ms=5_000
    )
    
    DATABASE = RetryConfig(
        max_attempts=5,
        strategy=RetryStrategy.EXPONENTIAL_JITTER,
        base_delay_ms=100,
        max_delay_ms=3_000,
        retry_if=lambda e: "connection" in str(e).lower() or "timeout" in str(e).lower()
    )
    
    IDEMPOTENT = RetryConfig(
        max_attempts=3,
        strategy=RetryStrategy.FIXED,
        base_delay_ms=500
    )
    
    CRITICAL = RetryConfig(
        max_attempts=10,
        strategy=RetryStrategy.EXPONENTIAL_JITTER,
        base_delay_ms=500,
        max_delay_ms=60_000
    )
```

### Usage Examples

```python
from phenotype_retry import Retry, RetryPolicies, RetryError

# Basic retry
async def fetch_user(user_id: str) -> User:
    return await Retry.execute(
        lambda: api.get_user(user_id),
        RetryPolicies.API_CALLS
    )

# Database retry
async def save_order(order: Order) -> None:
    return await Retry.execute(
        lambda: db.insert_order(order),
        RetryPolicies.DATABASE
    )

# Decorator
@Retry.with_retry(RetryPolicies.CRITICAL)
async def process_payment(payment: PaymentRequest) -> PaymentResult:
    return await payment_gateway.charge(payment)

# Custom retry logic
async def custom_operation():
    config = RetryConfig(
        max_attempts=5,
        strategy=RetryStrategy.EXPONENTIAL,
        base_delay_ms=100,
        max_delay_ms=10_000,
        retry_if=lambda e: isinstance(e, (TimeoutError, ConnectionError))
    )
    
    return await Retry.execute(operation, config)
```

## Testing Retry Logic

```rust
#[tokio::test]
async fn test_retry_succeeds_on_first_attempt() {
    let attempts = Arc::new(AtomicU32::new(0));
    let attempts_clone = attempts.clone();
    
    let result: Result<i32, &str> = Retry::execute(
        &RetryConfig::default(),
        || async move {
            attempts_clone.fetch_add(1, Ordering::SeqCst);
            Ok(42)
        }
    ).await;
    
    assert_eq!(result.unwrap(), 42);
    assert_eq!(attempts.load(Ordering::SeqCst), 1);
}

#[tokio::test]
async fn test_retry_exhaustion() {
    let attempts = Arc::new(AtomicU32::new(0));
    let attempts_clone = attempts.clone();
    
    let result: Result<i32, &str> = Retry::execute(
        &RetryConfig {
            max_attempts: 3,
            strategy: RetryStrategy::Fixed { delay_ms: 10 },
            ..Default::default()
        },
        || async move {
            attempts_clone.fetch_add(1, Ordering::SeqCst);
            Err("always fails")
        }
    ).await;
    
    assert!(result.is_err());
    assert_eq!(attempts.load(Ordering::SeqCst), 3);
}

#[tokio::test]
async fn test_retry_eventual_success() {
    let attempts = Arc::new(AtomicU32::new(0));
    let attempts_clone = attempts.clone();
    
    let result: Result<i32, &str> = Retry::execute(
        &RetryConfig {
            max_attempts: 5,
            strategy: RetryStrategy::Fixed { delay_ms: 10 },
            ..Default::default()
        },
        || async move {
            let count = attempts_clone.fetch_add(1, Ordering::SeqCst) + 1;
            if count < 3 {
                Err("not yet")
            } else {
                Ok(42)
            }
        }
    ).await;
    
    assert_eq!(result.unwrap(), 42);
    assert_eq!(attempts.load(Ordering::SeqCst), 3);
}
```

## Integration with Circuit Breaker

```rust
pub async fn resilient_call<T>(
    circuit_breaker: &CircuitBreaker,
    retry_config: &RetryConfig,
    operation: impl Fn() -> impl Future<Output = Result<T, ServiceError>>,
) -> Result<T, ResilientError> {
    circuit_breaker
        .call(|| Retry::execute(retry_config, &operation))
        .await
        .map_err(|e| match e {
            CircuitBreakerError::Open => ResilientError::ServiceUnavailable,
            CircuitBreakerError::Inner(RetryError::Failed { attempts, last_error }) => {
                ResilientError::RetryExhausted { attempts, last_error }
            }
            _ => ResilientError::Unknown,
        })
}
```