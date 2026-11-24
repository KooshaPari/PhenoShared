# Circuit Breaker Pattern

## Overview

The Circuit Breaker pattern prevents cascading failures in distributed systems by monitoring failure rates and automatically failing fast when a service is unhealthy.

## When to Use

- **External API calls**: Third-party services that may fail
- **Database connections**: Connection pool exhaustion scenarios
- **Microservice communication**: Service-to-service calls
- **Resource-intensive operations**: Operations that can hang

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                    Circuit Breaker States                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────┐      Failure threshold      ┌─────────┐  │
│   │   CLOSED    │ ─────────────────────────▶ │  OPEN   │  │
│   │             │      exceeded               │         │  │
│   │  ✅ Normal  │                            │  ❌ Fail │  │
│   │  Operation  │                            │  Fast   │  │
│   └──────┬──────┘                            └────┬────┘  │
│          │                                         │       │
│          │ Success                                   │       │
│          │ (while open)                              │       │
│          │                                           │       │
│          ▼                                           │       │
│   ┌─────────────┐      Timeout/Half-open      ┌────┘       │
│   │  HALF-OPEN  │ ─────────────────────────▶   │            │
│   │             │      test succeeds          │            │
│   │  🧪 Testing │                            │            │
│   │             │                            │            │
│   └─────────────┘                            │            │
│                                              ▼            │
│   ◄──────────────────────────────────────────────────────  │
│   Success: Close circuit                                   │
│   Failure: Re-open circuit                                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Phenotype Implementation

### Rust

```rust
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::RwLock;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub enum CircuitState {
    Closed,      // Normal operation
    Open,        // Failing fast
    HalfOpen,    // Testing if service recovered
}

#[derive(Debug, Clone)]
pub struct CircuitBreakerConfig {
    /// Number of failures before opening circuit
    pub failure_threshold: u32,
    /// Duration to stay open before testing (half-open)
    pub reset_timeout: Duration,
    /// Successes required in half-open to close
    pub success_threshold: u32,
    /// Window for counting failures
    pub failure_window: Duration,
}

impl Default for CircuitBreakerConfig {
    fn default() -> Self {
        Self {
            failure_threshold: 5,
            reset_timeout: Duration::from_secs(30),
            success_threshold: 3,
            failure_window: Duration::from_secs(60),
        }
    }
}

pub struct CircuitBreaker {
    name: String,
    config: CircuitBreakerConfig,
    state: Arc<RwLock<CircuitBreakerState>>,
    metrics: Arc<RwLock<CircuitMetrics>>,
}

struct CircuitBreakerState {
    current: CircuitState,
    last_failure: Option<Instant>,
    half_open_attempts: u32,
}

struct CircuitMetrics {
    failures: Vec<Instant>,
    successes: Vec<Instant>,
}

impl CircuitBreaker {
    pub fn new(name: impl Into<String>, config: CircuitBreakerConfig) -> Self {
        Self {
            name: name.into(),
            config,
            state: Arc::new(RwLock::new(CircuitBreakerState {
                current: CircuitState::Closed,
                last_failure: None,
                half_open_attempts: 0,
            })),
            metrics: Arc::new(RwLock::new(CircuitMetrics {
                failures: Vec::new(),
                successes: Vec::new(),
            })),
        }
    }
    
    /// Execute operation with circuit breaker protection
    pub async fn call<F, Fut, T, E>(
        &self,
        operation: F,
    ) -> Result<T, CircuitBreakerError<E>>
    where
        F: FnOnce() -> Fut,
        Fut: std::future::Future<Output = Result<T, E>>,
        E: std::fmt::Debug,
    {
        // Check if we should allow the call
        self.check_state().await?;
        
        // Execute the operation
        match operation().await {
            Ok(result) => {
                self.on_success().await;
                Ok(result)
            }
            Err(err) => {
                self.on_failure().await;
                Err(CircuitBreakerError::Inner(err))
            }
        }
    }
    
    async fn check_state(&self) -> Result<(), CircuitBreakerError<()>> {
        let mut state = self.state.write().await;
        let now = Instant::now();
        
        match state.current {
            CircuitState::Closed => {
                // Normal operation, allow
                Ok(())
            }
            CircuitState::Open => {
                // Check if we should try half-open
                if let Some(last_failure) = state.last_failure {
                    if now.duration_since(last_failure) >= self.config.reset_timeout {
                        state.current = CircuitState::HalfOpen;
                        state.half_open_attempts = 0;
                        tracing::info!(
                            circuit = %self.name,
                            "Circuit entering half-open state"
                        );
                        Ok(())
                    } else {
                        Err(CircuitBreakerError::Open)
                    }
                } else {
                    Err(CircuitBreakerError::Open)
                }
            }
            CircuitState::HalfOpen => {
                // Allow limited attempts in half-open
                if state.half_open_attempts < self.config.success_threshold {
                    state.half_open_attempts += 1;
                    Ok(())
                } else {
                    Err(CircuitBreakerError::Open)
                }
            }
        }
    }
    
    async fn on_success(&self) {
        let mut state = self.state.write().await;
        let mut metrics = self.metrics.write().await;
        
        metrics.successes.push(Instant::now());
        
        match state.current {
            CircuitState::HalfOpen => {
                // If we have enough successes, close the circuit
                if state.half_open_attempts >= self.config.success_threshold {
                    state.current = CircuitState::Closed;
                    state.half_open_attempts = 0;
                    state.last_failure = None;
                    
                    // Clear failure history
                    metrics.failures.clear();
                    
                    tracing::info!(
                        circuit = %self.name,
                        "Circuit breaker closed after successful recovery"
                    );
                    
                    // Emit event for monitoring
                    phenotype_telemetry::emit_event(
                        "circuit_breaker.closed",
                        phenotype_telemetry::EventLevel::Info,
                        [("circuit_name", self.name.clone())],
                    ).await;
                }
            }
            CircuitState::Closed => {
                // Clean old metrics
                self.clean_old_metrics(&mut metrics).await;
            }
            _ => {}
        }
    }
    
    async fn on_failure(&self) {
        let mut state = self.state.write().await;
        let mut metrics = self.metrics.write().await;
        let now = Instant::now();
        
        metrics.failures.push(now);
        state.last_failure = Some(now);
        
        match state.current {
            CircuitState::Closed => {
                // Clean old metrics and check threshold
                self.clean_old_metrics(&mut metrics).await;
                
                let recent_failures = metrics
                    .failures
                    .iter()
                    .filter(|t| now.duration_since(**t) <= self.config.failure_window)
                    .count() as u32;
                
                if recent_failures >= self.config.failure_threshold {
                    state.current = CircuitState::Open;
                    
                    tracing::warn!(
                        circuit = %self.name,
                        failures = recent_failures,
                        threshold = self.config.failure_threshold,
                        "Circuit breaker opened due to failure threshold"
                    );
                    
                    phenotype_telemetry::emit_event(
                        "circuit_breaker.opened",
                        phenotype_telemetry::EventLevel::Warning,
                        [
                            ("circuit_name", self.name.clone()),
                            ("failure_count", recent_failures.to_string()),
                        ],
                    ).await;
                }
            }
            CircuitState::HalfOpen => {
                // Return to open state
                state.current = CircuitState::Open;
                state.half_open_attempts = 0;
                
                tracing::warn!(
                    circuit = %self.name,
                    "Circuit breaker re-opened after failure in half-open"
                );
            }
            _ => {}
        }
    }
    
    async fn clean_old_metrics(&self, metrics: &mut CircuitMetrics) {
        let cutoff = Instant::now() - self.config.failure_window;
        metrics.failures.retain(|t| *t > cutoff);
        metrics.successes.retain(|t| *t > cutoff);
    }
    
    /// Get current state for monitoring
    pub async fn get_state(&self) -> CircuitStateInfo {
        let state = self.state.read().await;
        let metrics = self.metrics.read().await;
        
        CircuitStateInfo {
            name: self.name.clone(),
            state: state.current,
            last_failure: state.last_failure,
            failure_count: metrics.failures.len() as u32,
            success_count: metrics.successes.len() as u32,
        }
    }
}

#[derive(Debug)]
pub struct CircuitStateInfo {
    pub name: String,
    pub state: CircuitState,
    pub last_failure: Option<Instant>,
    pub failure_count: u32,
    pub success_count: u32,
}

#[derive(Debug)]
pub enum CircuitBreakerError<E> {
    Open,
    Inner(E),
}

impl<E: std::fmt::Display> std::fmt::Display for CircuitBreakerError<E> {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            CircuitBreakerError::Open => write!(f, "Circuit breaker is open"),
            CircuitBreakerError::Inner(e) => write!(f, "Inner error: {}", e),
        }
    }
}
```

### Usage Example

```rust
use phenotype_circuit_breaker::CircuitBreaker;

// Create circuit breaker for external API
let payment_api_breaker = CircuitBreaker::new(
    "payment_api",
    CircuitBreakerConfig {
        failure_threshold: 3,           // Open after 3 failures
        reset_timeout: Duration::from_secs(60),  // Try again after 1 minute
        success_threshold: 2,           // Need 2 successes to close
        failure_window: Duration::from_secs(30),
    }
);

// Use in service
pub async fn process_payment(
    &self,
    payment: PaymentRequest,
) -> Result<PaymentResult, PaymentError> {
    self.payment_breaker
        .call(|| self.payment_gateway.charge(payment))
        .await
        .map_err(|e| match e {
            CircuitBreakerError::Open => PaymentError::ServiceUnavailable,
            CircuitBreakerError::Inner(err) => err.into(),
        })?
}

// With fallback
pub async fn get_user_data(
    &self,
    user_id: &str,
) -> Result<UserData, ServiceError> {
    match self.user_service_breaker.call(|| self.user_api.get(user_id)).await {
        Ok(data) => Ok(data),
        Err(CircuitBreakerError::Open) => {
            // Fallback to cache
            tracing::warn!("User service circuit open, using cache fallback");
            self.user_cache.get(user_id).await
                .ok_or(ServiceError::FallbackExhausted)
        }
        Err(CircuitBreakerError::Inner(e)) => Err(e.into()),
    }
}
```

### Python Implementation

```python
import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, TypeVar, Optional, List
from functools import wraps

T = TypeVar('T')

class CircuitState(Enum):
    CLOSED = auto()      # Normal operation
    OPEN = auto()        # Failing fast
    HALF_OPEN = auto()   # Testing recovery

@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    reset_timeout: float = 30.0  # seconds
    success_threshold: int = 3
    failure_window: float = 60.0  # seconds

@dataclass
class CircuitMetrics:
    failures: List[float] = field(default_factory=list)
    successes: List[float] = field(default_factory=list)
    
    def clean_old(self, window: float):
        cutoff = time.time() - window
        self.failures = [t for t in self.failures if t > cutoff]
        self.successes = [t for t in self.successes if t > cutoff]

class CircuitBreaker:
    """Circuit breaker for protecting external calls."""
    
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._last_failure: Optional[float] = None
        self._half_open_attempts = 0
        self._metrics = CircuitMetrics()
        self._lock = asyncio.Lock()
    
    async def call(self, operation: Callable[..., T], *args, **kwargs) -> T:
        """Execute operation with circuit breaker protection."""
        
        async with self._lock:
            await self._check_state()
        
        try:
            result = await operation(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure()
            raise CircuitBreakerError(f"Circuit open for {self.name}") from e
    
    async def _check_state(self):
        """Check if operation should be allowed."""
        now = time.time()
        
        if self._state == CircuitState.OPEN:
            if self._last_failure and (now - self._last_failure) >= self.config.reset_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_attempts = 0
                print(f"[{self.name}] Entering half-open state")
            else:
                raise CircuitBreakerError(f"Circuit {self.name} is OPEN")
        
        elif self._state == CircuitState.HALF_OPEN:
            if self._half_open_attempts >= self.config.success_threshold:
                raise CircuitBreakerError(f"Circuit {self.name} is OPEN (half-open limit)")
            self._half_open_attempts += 1
    
    async def _on_success(self):
        """Handle successful operation."""
        async with self._lock:
            now = time.time()
            self._metrics.successes.append(now)
            
            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_attempts >= self.config.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._half_open_attempts = 0
                    self._last_failure = None
                    self._metrics.failures.clear()
                    print(f"[{self.name}] Circuit CLOSED after recovery")
            elif self._state == CircuitState.CLOSED:
                self._metrics.clean_old(self.config.failure_window)
    
    async def _on_failure(self):
        """Handle failed operation."""
        async with self._lock:
            now = time.time()
            self._metrics.failures.append(now)
            self._last_failure = now
            
            if self._state == CircuitState.CLOSED:
                self._metrics.clean_old(self.config.failure_window)
                recent_failures = len(self._metrics.failures)
                
                if recent_failures >= self.config.failure_threshold:
                    self._state = CircuitState.OPEN
                    print(f"[{self.name}] Circuit OPENED ({recent_failures} failures)")
            elif self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._half_open_attempts = 0
                print(f"[{self.name}] Circuit re-OPENED after half-open failure")
    
    @property
    def state(self) -> CircuitState:
        return self._state
    
    def get_metrics(self) -> dict:
        return {
            'state': self._state.name,
            'failures': len(self._metrics.failures),
            'successes': len(self._metrics.successes),
            'last_failure': self._last_failure,
        }

class CircuitBreakerError(Exception):
    pass

# Decorator version
def circuit_breaker(breaker: CircuitBreaker):
    """Decorator for circuit breaker protection."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator
```

## Configuration Guidelines

| Scenario | Failure Threshold | Reset Timeout | Success Threshold |
|----------|------------------|---------------|-------------------|
| Critical payment API | 3 | 60s | 3 |
| User service | 5 | 30s | 2 |
| Cache service | 10 | 10s | 1 |
| Analytics (non-critical) | 20 | 300s | 5 |

## Testing

```rust
#[tokio::test]
async fn test_circuit_opens_after_failures() {
    let breaker = CircuitBreaker::new(
        "test",
        CircuitBreakerConfig {
            failure_threshold: 3,
            reset_timeout: Duration::from_secs(1),
            success_threshold: 2,
            ..Default::default()
        }
    );
    
    // First 3 calls fail
    for _ in 0..3 {
        let result: Result<i32, _> = breaker
            .call(|| async { Err::<i32, &str>("error") })
            .await;
        assert!(result.is_err());
    }
    
    // Circuit should now be open
    let result: Result<i32, _> = breaker
        .call(|| async { Ok(42) })
        .await;
    
    assert!(matches!(result, Err(CircuitBreakerError::Open)));
}

#[tokio::test]
async fn test_circuit_recovery() {
    let breaker = CircuitBreaker::new(
        "test",
        CircuitBreakerConfig {
            failure_threshold: 1,
            reset_timeout: Duration::from_millis(100),
            success_threshold: 2,
            ..Default::default()
        }
    );
    
    // Open circuit
    let _: Result<i32, _> = breaker
        .call(|| async { Err::<i32, &str>("error") })
        .await;
    
    // Wait for reset timeout
    tokio::time::sleep(Duration::from_millis(150)).await;
    
    // Circuit should be half-open, needs 2 successes
    for _ in 0..2 {
        let result: Result<i32, _> = breaker
            .call(|| async { Ok(42) })
            .await;
        assert!(result.is_ok());
    }
    
    // Circuit should be closed
    let state = breaker.get_state().await;
    assert_eq!(state.state, CircuitState::Closed);
}
```