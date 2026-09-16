# Saga Pattern

## Overview

The **Saga Pattern** manages distributed transactions across multiple services without using distributed locks.

## When to Use

- Long-running business processes spanning multiple services
- Need for atomicity without 2PC (Two-Phase Commit)
- Compensating actions required for rollback
- Workflow with human approval steps

## Types

### 1. Choreography Saga

Services react to events from other services.

```
┌────────────┐    OrderCreated     ┌────────────┐
│  Order     │ ─────────────────▶ │  Payment   │
│  Service   │                    │  Service   │
└────────────┘                    └──────┬─────┘
      │                                    │
      │         PaymentProcessed          │
      │ ◀─────────────────────────────────┘
      │                                    │
      │         InventoryReserved          │
      │ ◀─────────────────────────────────┐
      │                                    │
┌─────▼──────┐                    ┌────────▼───┐
│ Fulfillment│ ◀──────────────── │ Inventory  │
│  Service   │   OrderShipped   │  Service   │
└────────────┘                    └────────────┘
```

### 2. Orchestration Saga

Central coordinator manages the workflow.

```
┌─────────────────────────────────────────┐
│           Saga Orchestrator             │
│  ┌─────────────────────────────────┐    │
│  │ 1. Create Order ──▶ OrderSvc   │    │
│  │ 2. Process Payment ──▶ PaySvc│    │
│  │ 3. Reserve Inventory ──▶ InvSvc│    │
│  │ 4. Ship Order ──▶ ShipSvc      │    │
│  │ [On failure: Compensate]        │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

## Implementation

### Saga Definition

```rust
pub trait Saga: Send + Sync {
    type State: SagaState;
    
    fn steps(&self) -> Vec<Box<dyn SagaStep<Self::State>>>;
    fn on_error(&self, state: &Self::State, failed_step: usize) -> CompensationPlan;
}

pub struct OrderSaga;

impl Saga for OrderSaga {
    type State = OrderSagaState;
    
    fn steps(&self) -> Vec<Box<dyn SagaStep<OrderSagaState>>> {
        vec![
            Box::new(CreateOrderStep),
            Box::new(ProcessPaymentStep),
            Box::new(ReserveInventoryStep),
            Box::new(ShipOrderStep),
        ]
    }
    
    fn on_error(&self, state: &OrderSagaState, failed_step: usize) -> CompensationPlan {
        match failed_step {
            3 => CompensationPlan::steps(vec![
                Box::new(ReleaseInventoryStep),
                Box::new(RefundPaymentStep),
                Box::new(CancelOrderStep),
            ]),
            2 => CompensationPlan::steps(vec![
                Box::new(RefundPaymentStep),
                Box::new(CancelOrderStep),
            ]),
            1 => CompensationPlan::step(Box::new(CancelOrderStep)),
            _ => CompensationPlan::none(),
        }
    }
}
```

### Saga State

```rust
#[derive(Debug, Clone)]
pub struct OrderSagaState {
    pub order_id: Option<OrderId>,
    pub payment_id: Option<PaymentId>,
    pub inventory_reserved: bool,
    pub shipment_id: Option<ShipmentId>,
    pub status: SagaStatus,
}

#[derive(Debug, Clone)]
pub enum SagaStatus {
    Pending,
    InProgress { current_step: usize },
    Completed,
    Compensating { failed_step: usize, current_compensation: usize },
    Failed { reason: String },
}
```

### Saga Steps

```rust
#[async_trait]
pub trait SagaStep<S: SagaState>: Send + Sync {
    async fn execute(&self, state: &mut S, ctx: &SagaContext) -> Result<(), SagaError>;
    async fn compensate(&self, state: &S, ctx: &SagaContext) -> Result<(), CompensationError>;
}

pub struct ProcessPaymentStep;

#[async_trait]
impl SagaStep<OrderSagaState> for ProcessPaymentStep {
    async fn execute(
        &self,
        state: &mut OrderSagaState,
        ctx: &SagaContext,
    ) -> Result<(), SagaError> {
        let payment = ctx
            .payment_service
            .charge(ChargeRequest {
                order_id: state.order_id.as_ref().unwrap().clone(),
                amount: ctx.order_total,
            })
            .await
            .map_err(|e| SagaError::step_failed("payment", e))?;
        
        state.payment_id = Some(payment.id);
        Ok(())
    }
    
    async fn compensate(
        &self,
        state: &OrderSagaState,
        ctx: &SagaContext,
    ) -> Result<(), CompensationError> {
        if let Some(payment_id) = &state.payment_id {
            ctx.payment_service
                .refund(payment_id.clone())
                .await
                .map_err(|e| CompensationError::failed("refund", e))?;
        }
        Ok(())
    }
}
```

### Orchestrator

```rust
pub struct SagaOrchestrator {
    store: SagaStore,
    event_bus: Box<dyn EventBus>,
}

impl SagaOrchestrator {
    pub async fn execute<S: Saga>(
        &self,
        saga: S,
        initial_state: S::State,
    ) -> Result<S::State, SagaFailure> {
        let saga_id = SagaId::new();
        let mut state = initial_state;
        let steps = saga.steps();
        
        // Persist saga start
        self.store.save(&saga_id, &state).await?;
        
        for (idx, step) in steps.iter().enumerate() {
            // Update status
            state.set_status(SagaStatus::InProgress { current_step: idx });
            self.store.save(&saga_id, &state).await?;
            
            // Execute step
            match step.execute(&mut state, &self.context()).await {
                Ok(()) => {
                    self.event_bus.publish(SagaStepCompleted {
                        saga_id: saga_id.clone(),
                        step: idx,
                    }).await?;
                }
                Err(e) => {
                    // Compensate
                    return self.compensate(saga, &state, idx, e).await;
                }
            }
        }
        
        // Mark complete
        state.set_status(SagaStatus::Completed);
        self.store.save(&saga_id, &state).await?;
        
        Ok(state)
    }
    
    async fn compensate<S: Saga>(
        &self,
        saga: S,
        state: &S::State,
        failed_step: usize,
        error: SagaError,
    ) -> Result<S::State, SagaFailure> {
        let compensation = saga.on_error(state, failed_step);
        
        for (idx, step) in compensation.steps().iter().enumerate() {
            state.set_status(SagaStatus::Compensating {
                failed_step,
                current_compensation: idx,
            });
            
            if let Err(e) = step.compensate(state, &self.context()).await {
                // Log critical - manual intervention needed
                tracing::error!(
                    saga_id = %saga_id,
                    compensation_step = idx,
                    error = %e,
                    "Compensation failed - manual intervention required"
                );
                
                return Err(SagaFailure::compensation_failed(e));
            }
        }
        
        state.set_status(SagaStatus::Failed {
            reason: error.to_string(),
        });
        self.store.save(&saga_id, state).await?;
        
        Err(SagaFailure::original_error(error))
    }
}
```

## Compensating Actions

### Compensation Principles

1. **Idempotent**: Can run multiple times safely
2. **Best-effort**: May fail - log for manual review
3. **Ordered**: Reverse order of original execution
4. **Deterministic**: Same input → same output

```rust
pub struct ReleaseInventoryStep;

#[async_trait]
impl CompensationStep for ReleaseInventoryStep {
    async fn execute(
        &self,
        state: &OrderSagaState,
        ctx: &SagaContext,
    ) -> Result<(), CompensationError> {
        if state.inventory_reserved {
            ctx.inventory_service
                .release(ReleaseRequest {
                    order_id: state.order_id.clone().unwrap(),
                })
                .await?;
        }
        Ok(())
    }
}
```

## Timeouts and Retries

### Step Timeout

```rust
pub struct RetryConfig {
    pub max_attempts: u32,
    pub backoff: BackoffStrategy,
    pub timeout: Duration,
}

pub enum BackoffStrategy {
    Fixed(Duration),
    Exponential { base: Duration, max: Duration },
}

impl SagaStep for RetriableStep {
    async fn execute(&self, state: &mut State, ctx: &Context) -> Result<(), SagaError> {
        let config = self.retry_config();
        
        for attempt in 0..config.max_attempts {
            match timeout(config.timeout, self.inner.execute(state, ctx)).await {
                Ok(Ok(())) => return Ok(()),
                Ok(Err(e)) if self.is_retryable(&e) => {
                    sleep(config.backoff.delay(attempt)).await;
                    continue;
                }
                Ok(Err(e)) => return Err(e),
                Err(_) => return Err(SagaError::timeout()),
            }
        }
        
        Err(SagaError::max_retries_exceeded())
    }
}
```

## Observability

### Saga Tracing

```rust
pub struct TracedSaga<S: Saga> {
    inner: S,
    tracer: Tracer,
}

#[async_trait]
impl<S: Saga> Saga for TracedSaga<S> {
    async fn execute(&self, state: S::State) -> Result<S::State, SagaFailure> {
        let span = info_span!(
            "saga.execute",
            saga_id = %saga_id,
            saga_type = %type_name::<S>(),
        );
        
        async move {
            for (idx, step) in steps.iter().enumerate() {
                let _step_span = info_span!(
                    "saga.step",
                    step = idx,
                    step_type = %step.name(),
                );
                
                match step.execute(&mut state).await {
                    Ok(()) => {
                        info!(step = idx, "Step completed");
                    }
                    Err(e) => {
                        error!(step = idx, error = %e, "Step failed - compensating");
                        return self.compensate(state, idx, e).await;
                    }
                }
            }
            
            info!("Saga completed successfully");
            Ok(state)
        }
        .instrument(span)
        .await
    }
}
```

## Testing

### Saga Unit Tests

```rust
#[tokio::test]
async fn saga_completes_all_steps() {
    let saga = OrderSaga::new();
    let mock_ctx = MockSagaContext::new()
        .expect_payment_ok()
        .expect_inventory_ok()
        .expect_shipment_ok();
    
    let result = saga.execute(initial_state(), mock_ctx).await;
    
    assert!(result.is_ok());
    assert_eq!(result.unwrap().status, SagaStatus::Completed);
}

#[tokio::test]
async fn saga_compensates_on_failure() {
    let saga = OrderSaga::new();
    let mock_ctx = MockSagaContext::new()
        .expect_payment_ok()
        .expect_inventory_fail()  // Fails here
        .expect_refund_called()    // Should compensate
        .expect_cancel_called();   // Should compensate
    
    let result = saga.execute(initial_state(), mock_ctx).await;
    
    assert!(result.is_err());
    mock_ctx.verify_all_compensations_called();
}
```

## Anti-Patterns

- ❌ Synchronous saga execution (blocks too long)
- ❌ Missing compensation for non-idempotent operations
- ❌ Not handling compensation failures
- ❌ Too many steps in one saga (consider splitting)
- ❌ Not persisting saga state (can't resume after crash)

## Related Patterns

- [Event-Driven Architecture](./event-driven.md)
- [CQRS](./cqrs.md)
- [Event Sourcing](./event-sourcing.md)
- [Outbox Pattern](./outbox.md)

## References

- [Saga Pattern - Chris Richardson](https://microservices.io/patterns/data/saga.html)
- [Microsoft Saga Pattern](https://docs.microsoft.com/en-us/azure/architecture/reference-architectures/saga/saga)
