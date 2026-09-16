# Event-Driven Architecture Pattern

## Overview

Event-driven architecture enables loosely coupled, scalable systems through asynchronous message passing.

## When to Use

- Multiple services need to react to the same event
- Workflows span multiple bounded contexts
- You need temporal decoupling (producer doesn't wait for consumer)
- High throughput requirements

## Structure

```
┌─────────────┐     Event      ┌─────────────┐
│  Producer   │ ───────────────▶ │   Broker    │
│  (Service)  │                  │ (Event Bus) │
└─────────────┘                  └──────┬──────┘
                                        │
                         ┌──────────────┼──────────────┐
                         │              │              │
                         ▼              ▼              ▼
                   ┌─────────┐    ┌─────────┐    ┌─────────┐
                   │ConsumerA│    │ConsumerB│    │ConsumerC│
                   │ (Email) │    │ (Audit) │    │(Analytics)
                   └─────────┘    └─────────┘    └─────────┘
```

## Phenotype Event Bus

### Domain (Core)

```rust
pub trait Event: Serialize + DeserializeOwned + Send + Sync + 'static {
    fn event_type(&self) -> &'static str;
    fn aggregate_id(&self) -> &str;
}

pub trait EventPublisher {
    fn publish<E: Event>(&self, event: E) -> Result<(), EventError>;
}

pub trait EventSubscriber {
    fn subscribe<E: Event, H: EventHandler<E>>(&self, handler: H);
}

pub trait EventHandler<E: Event>: Send + Sync {
    fn handle(&self, event: E) -> Result<(), HandlerError>;
}
```

### Application (Event Sourcing)

```rust
pub struct EventSourcedAggregate {
    id: AggregateId,
    version: u64,
    uncommitted_events: Vec<DomainEvent>,
}

impl EventSourcedAggregate {
    pub fn apply(&mut self, event: DomainEvent) {
        // Apply event to mutate state
        self.version += 1;
        self.uncommitted_events.push(event);
    }
    
    pub fn commit(&mut self) -> Vec<DomainEvent> {
        std::mem::take(&mut self.uncommitted_events)
    }
}
```

### Adapter (NATS Implementation)

```rust
pub struct NatsEventBus {
    client: async_nats::Client,
    jetstream: Context,
}

impl EventPublisher for NatsEventBus {
    fn publish<E: Event>(&self, event: E) -> Result<(), EventError> {
        let subject = format!("events.{}.{}", E::event_type(), event.aggregate_id());
        let payload = serde_json::to_vec(&event)?;
        
        self.jetstream
            .publish(subject, payload.into())
            .await?;
            
        Ok(())
    }
}
```

## Event Types

### Domain Events
- Represent business facts
- Past tense (UserCreated, OrderPlaced)
- Contain full context needed by consumers

### Integration Events
- Cross-boundary context
- Published to external systems
- Schema versioned

### Commands vs Events

| Command | Event |
|---------|-------|
| Imperative (CreateUser) | Past tense (UserCreated) |
| Can be rejected | Immutable fact |
| Sent to specific handler | Broadcast to all subscribers |
| Synchronous expectation | Asynchronous processing |

## Conventions

### Event Naming
```rust
// Good
pub struct UserCreated {
    pub user_id: UserId,
    pub email: Email,
    pub created_at: DateTime<Utc>,
}

// Bad
pub struct CreateUser {  // Command, not event
    pub email: String,
}
```

### Subject Patterns
```
events.{domain}.{aggregate_type}.{aggregate_id}.{event_type}

events.user.User.123e4567.created
events.order.Order.abc123.placed
events.payment.Payment.xyz789.processed
```

## Idempotency

All consumers must be idempotent:

```rust
pub struct IdempotentHandler<H: EventHandler<E>, E: Event> {
    handler: H,
    store: ProcessedEventStore,
}

impl<H: EventHandler<E>, E: Event> EventHandler<E> for IdempotentHandler<H, E> {
    fn handle(&self, event: E) -> Result<(), HandlerError> {
        let event_id = event.id();
        
        // Check if already processed
        if self.store.exists(event_id)? {
            return Ok(());  // Skip
        }
        
        // Process
        self.handler.handle(event)?;
        
        // Mark processed
        self.store.mark(event_id)?;
        Ok(())
    }
}
```

## Error Handling

### Retry Strategy
```rust
pub enum RetryPolicy {
    Immediate(u32),      // Retry N times immediately
    Exponential(u32),    // Exponential backoff
    DeadLetter,          // Send to DLQ after failures
}
```

### Dead Letter Queue
```rust
pub trait DeadLetterQueue {
    fn send(&self, event: Box<dyn Event>, error: HandlerError);
    fn retry_all(&self) -> Result<u64, Error>;
}
```

## Observability

### Event Tracing
```rust
pub struct TracedEvent<E: Event> {
    #[serde(flatten)]
    event: E,
    trace_id: TraceId,
    span_id: SpanId,
    parent_span_id: Option<SpanId>,
}
```

### Metrics
- `events_published_total` - Counter by event type
- `events_consumed_total` - Counter by consumer
- `event_latency_seconds` - Histogram of processing time
- `event_backlog` - Gauge of pending events

## Testing

### Unit Tests
```rust
#[test]
fn user_created_event_applies_correctly() {
    let mut user = User::new();
    let event = UserCreated {
        user_id: UserId::new(),
        email: Email::parse("test@example.com").unwrap(),
    };
    
    user.apply(event.clone());
    
    assert_eq!(user.email(), &event.email);
}
```

### Integration Tests
```rust
#[tokio::test]
async fn event_published_and_consumed() {
    let bus = InMemoryEventBus::new();
    let mut consumer = TestConsumer::new();
    
    bus.subscribe(consumer.clone()).await;
    
    let event = UserCreated::new();
    bus.publish(event.clone()).await.unwrap();
    
    // Wait for processing
    tokio::time::sleep(Duration::from_millis(100)).await;
    
    assert!(consumer.received(event));
}
```

## Anti-Patterns

- ❌ Synchronous waiting for event processing
- ❌ Using events for request-response
- ❌ Event payload too large (>1MB)
- ❌ No schema versioning
- ❌ Missing idempotency handling

## Related Patterns

- [CQRS](cqrs.md)
- [Event Sourcing](event-sourcing.md)
- [Saga Pattern](saga.md)
- [Outbox Pattern](outbox.md)
