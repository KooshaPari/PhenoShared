# Outbox Pattern

## Overview

The **Outbox Pattern** ensures reliable message delivery by atomically saving domain events to an "outbox" table alongside the business data transaction.

## Problem

Without Outbox, you risk inconsistency:

```
Scenario A: Database commit succeeds, event publish fails
┌──────────┐    ┌──────────┐    ┌──────────┐
│   Save   │───▶│  Commit  │───▶│ Publish  │──❌ FAIL
│  Order   │    │  Order   │    │  Event   │
└──────────┘    └──────────┘    └──────────┘
                                    ▲
Result: Order exists, but no event → downstream systems unaware

Scenario B: Event publish succeeds, database rollback
┌──────────┐    ┌──────────┐    ┌──────────┐
│   Save   │───▶│ Publish  │───▶│  Commit  │──❌ ROLLBACK
│  Order   │    │  Event   │    │  Order   │
└──────────┘    └──────────┘    └──────────┘
Result: Event published, no order → phantom events
```

## Solution

Use Outbox table for atomic dual-write:

```
┌─────────────────────────────────────────────┐
│          Business Transaction               │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │ BEGIN TRANSACTION                   │   │
│  │                                     │   │
│  │   INSERT INTO orders (...)          │   │
│  │                                     │   │
│  │   INSERT INTO outbox (             │   │
│  │     id, aggregate_type,           │   │
│  │     aggregate_id, event_type,     │   │
│  │     payload, created_at            │   │
│  │   ) VALUES (...)                    │   │
│  │                                     │   │
│  │ COMMIT ─────────────────────────▶   │   │
│  └─────────────────────────────────────┘   │
│            Both succeed or both fail       │
└───────────────────────────────────────────┘
                        │
                        ▼
              ┌──────────────────┐
              │  Outbox Relay    │
              │  (Poller)        │
              └────────┬─────────┘
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
    ┌─────────┐ ┌─────────┐ ┌─────────┐
    │  NATS   │ │ Kafka   │ │RabbitMQ │
    └─────────┘ └─────────┘ └─────────┘
```

## Implementation

### Outbox Table Schema

```sql
CREATE TABLE outbox (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregate_type VARCHAR(255) NOT NULL,  -- 'order', 'user', etc.
    aggregate_id VARCHAR(255) NOT NULL,    -- Order-123, User-456
    event_type VARCHAR(255) NOT NULL,      -- OrderCreated, UserUpdated
    payload JSONB NOT NULL,                -- Event data
    headers JSONB DEFAULT '{}',            -- Metadata (trace_id, etc.)
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMP,                -- NULL until published
    retry_count INT DEFAULT 0,
    error_message TEXT,
    
    -- Index for efficient polling
    CONSTRAINT idx_outbox_unprocessed 
        CHECK (processed_at IS NULL)
);

-- Index for poller query
CREATE INDEX idx_outbox_created_unprocessed 
ON outbox(created_at) 
WHERE processed_at IS NULL;

-- Cleanup old processed events (partition or delete)
CREATE INDEX idx_outbox_processed 
ON outbox(processed_at) 
WHERE processed_at IS NOT NULL;
```

### Domain Integration

```rust
pub struct OutboxEvent {
    pub aggregate_type: String,
    pub aggregate_id: String,
    pub event_type: String,
    pub payload: serde_json::Value,
    pub headers: HashMap<String, String>,
}

pub trait OutboxRepository: Send + Sync {
    fn append(&self, events: Vec<OutboxEvent>) -> Result<(), OutboxError>;
}

// Use in domain service
pub struct OrderService<R: OrderRepository, O: OutboxRepository> {
    orders: R,
    outbox: O,
}

impl<R: OrderRepository, O: OutboxRepository> OrderService<R, O> {
    pub async fn create_order(&self, cmd: CreateOrder) -> Result<Order, OrderError> {
        // Start transaction
        let mut tx = self.orders.begin().await?;
        
        // Domain logic
        let order = Order::create(cmd)?;
        
        // Save aggregate
        self.orders.save(&order).await?;
        
        // Convert domain events to outbox
        let outbox_events: Vec<OutboxEvent> = order
            .uncommitted_events()
            .iter()
            .map(|e| OutboxEvent {
                aggregate_type: "order".to_string(),
                aggregate_id: order.id().to_string(),
                event_type: e.event_type(),
                payload: serde_json::to_value(e).unwrap(),
                headers: self.current_context().headers(),
            })
            .collect();
        
        // Append to outbox (same transaction)
        self.outbox.append(outbox_events).await?;
        
        // Commit atomically
        tx.commit().await?;
        
        Ok(order)
    }
}
```

### Relay/Poller

```rust
pub struct OutboxRelay {
    db: DatabaseConnection,
    publisher: Box<dyn EventPublisher>,
    config: RelayConfig,
}

impl OutboxRelay {
    pub async fn run(&self) -> Result<(), RelayError> {
        loop {
            self.poll_and_publish().await?;
            sleep(self.config.poll_interval).await;
        }
    }
    
    async fn poll_and_publish(&self) -> Result<(), RelayError> {
        // Fetch batch of unprocessed events
        let events: Vec<OutboxEvent> = sqlx::query_as!(
            OutboxEvent,
            r#"
            SELECT * FROM outbox 
            WHERE processed_at IS NULL 
            ORDER BY created_at 
            LIMIT $1
            FOR UPDATE SKIP LOCKED
            "#,
            self.config.batch_size
        )
        .fetch_all(&self.db)
        .await?;
        
        for event in events {
            match self.publish(&event).await {
                Ok(()) => {
                    // Mark as processed
                    sqlx::query!(
                        "UPDATE outbox SET processed_at = NOW() WHERE id = $1",
                        event.id
                    )
                    .execute(&self.db)
                    .await?;
                    
                    info!(event_id = %event.id, "Event published successfully");
                }
                Err(e) => {
                    // Increment retry count, log error
                    sqlx::query!(
                        r#"
                        UPDATE outbox 
                        SET retry_count = retry_count + 1,
                            error_message = $2
                        WHERE id = $1
                        "#,
                        event.id,
                        e.to_string()
                    )
                    .execute(&self.db)
                    .await?;
                    
                    error!(event_id = %event.id, error = %e, "Failed to publish event");
                    
                    // If max retries exceeded, move to dead letter
                    if event.retry_count >= self.config.max_retries {
                        self.move_to_dead_letter(&event, e).await?;
                    }
                }
            }
        }
        
        Ok(())
    }
    
    async fn publish(&self, event: &OutboxEvent) -> Result<(), PublishError> {
        let subject = format!(
            "events.{}.{}.{}.{}", 
            event.event_type,
            event.aggregate_type,
            event.aggregate_id
        );
        
        let message = Message {
            payload: event.payload.clone(),
            headers: event.headers.clone(),
            timestamp: event.created_at,
        };
        
        self.publisher
            .publish(&subject, message)
            .await
            .map_err(|e| PublishError::broker_error(e))
    }
}
```

### Relay Configuration

```rust
pub struct RelayConfig {
    pub poll_interval: Duration,      // How often to check (e.g., 100ms)
    pub batch_size: usize,            // Events per poll (e.g., 100)
    pub max_retries: u32,             // Retry before dead letter (e.g., 3)
    pub backoff: BackoffConfig,      // Exponential backoff between retries
    pub dead_letter_enabled: bool,    // Move failed events to DLQ
}

impl Default for RelayConfig {
    fn default() -> Self {
        Self {
            poll_interval: Duration::from_millis(100),
            batch_size: 100,
            max_retries: 3,
            backoff: BackoffConfig::exponential(
                Duration::from_secs(1),
                Duration::from_secs(60)
            ),
            dead_letter_enabled: true,
        }
    }
}
```

## Variations

### 1. Polling Publisher (Basic)

Simple SELECT + UPDATE loop. Good for low-throughput.

### 2. Transaction Log Tailing (Advanced)

Monitor database WAL directly (Debezium, etc.):

```rust
// With Debezium / PostgreSQL logical replication
pub struct LogTailingRelay {
    replication_slot: String,
    publisher: Box<dyn EventPublisher>,
}

impl LogTailingRelay {
    async fn run(&self) -> Result<(), RelayError> {
        let mut stream = self.connect_to_replication_slot().await?;
        
        while let Some(change) = stream.next().await {
            match change {
                WalChange::Insert { table, data } if table == "outbox" => {
                    self.publish_from_wal(data).await?;
                }
                _ => {} // Ignore other tables
            }
        }
        
        Ok(())
    }
}
```

### 3. Hybrid (Polling + Tail)

Use polling for bootstrap, switch to WAL for real-time.

## Dead Letter Queue

```sql
CREATE TABLE outbox_dead_letter (
    id UUID PRIMARY KEY,
    original_event JSONB NOT NULL,
    error_message TEXT NOT NULL,
    failed_at TIMESTAMP NOT NULL DEFAULT NOW(),
    retry_count INT NOT NULL,
    manual_review_notes TEXT
);
```

```rust
impl OutboxRelay {
    async fn move_to_dead_letter(
        &self,
        event: &OutboxEvent,
        error: PublishError,
    ) -> Result<(), RelayError> {
        // Insert to DLQ
        sqlx::query!(
            r#"
            INSERT INTO outbox_dead_letter 
            (id, original_event, error_message, retry_count)
            VALUES ($1, $2, $3, $4)
            "#,
            event.id,
            serde_json::to_value(event)?,
            error.to_string(),
            event.retry_count
        )
        .execute(&self.db)
        .await?;
        
        // Remove from outbox
        sqlx::query!("DELETE FROM outbox WHERE id = $1", event.id)
            .execute(&self.db)
            .await?;
        
        // Alert on-call
        self.alert_dead_letter(event).await?;
        
        Ok(())
    }
}
```

## Ordering Guarantees

### Per-Aggregate Ordering

```rust
// Ensure events for same aggregate processed in order
let events: Vec<OutboxEvent> = sqlx::query_as!(
    OutboxEvent,
    r#"
    SELECT * FROM outbox 
    WHERE processed_at IS NULL 
    AND (aggregate_type, aggregate_id) IN (
        SELECT aggregate_type, aggregate_id 
        FROM outbox 
        WHERE processed_at IS NULL 
        ORDER BY created_at 
        LIMIT $1
    )
    ORDER BY aggregate_type, aggregate_id, created_at
    FOR UPDATE SKIP LOCKED
    "#,
    self.config.batch_size
)
.fetch_all(&self.db)
.await?;
```

### Global Ordering

```sql
-- Use sequence or timestamp-based ordering
ALTER TABLE outbox ADD COLUMN sequence BIGINT;
CREATE SEQUENCE outbox_seq;

-- Insert with sequence
INSERT INTO outbox (..., sequence) 
VALUES (..., nextval('outbox_seq'));
```

## Cleanup

```rust
pub struct OutboxCleaner;

impl OutboxCleaner {
    async fn cleanup_processed(&self, retention: Duration) -> Result<u64, Error> {
        let cutoff = Utc::now() - retention;
        
        let result = sqlx::query!(
            "DELETE FROM outbox WHERE processed_at < $1",
            cutoff
        )
        .execute(&self.db)
        .await?;
        
        Ok(result.rows_affected())
    }
}
```

## Testing

```rust
#[tokio::test]
async fn outbox_saves_event_with_order() {
    let service = OrderService::new(in_memory_db());
    
    let order = service.create_order(cmd).await.unwrap();
    
    // Verify both saved atomically
    let outbox_events = outbox_repo
        .find_by_aggregate("order", order.id())
        .await
        .unwrap();
    
    assert_eq!(outbox_events.len(), 1);
    assert_eq!(outbox_events[0].event_type, "OrderCreated");
}

#[tokio::test]
async fn relay_publishes_and_marks_processed() {
    let relay = OutboxRelay::new(test_db(), mock_publisher());
    
    // Pre-populate outbox
    outbox_repo.append(vec![test_event()]).await.unwrap();
    
    // Run relay once
    relay.poll_and_publish().await.unwrap();
    
    // Verify published
    assert!(mock_publisher.was_published(&test_event()));
    
    // Verify marked processed
    let event = outbox_repo.find_by_id(test_event().id).await.unwrap();
    assert!(event.processed_at.is_some());
}
```

## Anti-Patterns

- ❌ Publishing events directly (no outbox)
- ❌ Separate transactions for data and events
- ❌ Not handling relay failures
- ❌ No cleanup → outbox table grows forever
- ❌ Not preserving ordering guarantees

## Related Patterns

- [Event-Driven Architecture](./event-driven.md)
- [CQRS](./cqrs.md)
- [Saga Pattern](./saga.md)
- [Event Sourcing](./event-sourcing.md)

## References

- [Outbox Pattern - Chris Richardson](https://microservices.io/patterns/data/transactional-outbox.html)
- [Debezium Outbox Event Router](https://debezium.io/documentation/reference/stable/transformations/outbox-event-router.html)
