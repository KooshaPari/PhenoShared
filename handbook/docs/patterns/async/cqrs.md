# CQRS Pattern

## Overview

**Command Query Responsibility Segregation** separates read and write operations into different models.

## When to Use

- Different read/write scaling requirements
- Complex read models vs simple writes
- Event sourcing with projected read models
- Different teams owning reads vs writes

## Structure

```
┌─────────────────────────────────────────────┐
│               Client                        │
│         ┌─────────┐                         │
│         │ Command │                         │
│         └────┬────┘                         │
│              │                              │
│              ▼                              │
│  ┌─────────────────────┐                    │
│  │   Command Handler   │  Write Model       │
│  │   (Validation,     │  ───────────       │
│  │    Business Logic) │                    │
│  └──────────┬──────────┘                    │
│             │                               │
│             ▼                               │
│  ┌─────────────────────┐     ┌────────────┐ │
│  │   Event Store /     │────▶│  Projector │ │
│  │   Write Database    │     └─────┬──────┘ │
│  └─────────────────────┘           │        │
│                                    │        │
│                                    ▼        │
│                          ┌────────────────┐ │
│                          │  Read Database │ │
│                          │  (Optimized)   │ │
│                          └────────┬───────┘ │
│                                   │         │
│              ┌────────────────────┘         │
│              │                               │
│              ▼                               │
│  ┌─────────────────────┐                    │
│  │   Query Handler     │                    │
│  │   (Simple reads)    │                    │
│  └─────────────────────┘                    │
└─────────────────────────────────────────────┘
```

## Implementation

### Domain (Commands)

```rust
pub trait Command: Send + Sync {
    type Aggregate: Aggregate;
    
    fn execute(
        &self,
        aggregate: &mut Self::Aggregate,
    ) -> Result<Vec<DomainEvent>, DomainError>;
}

pub struct CreateOrder {
    pub order_id: OrderId,
    pub customer_id: CustomerId,
    pub items: Vec<OrderItem>,
}

impl Command for CreateOrder {
    type Aggregate = Order;
    
    fn execute(
        &self,
        order: &mut Order,
    ) -> Result<Vec<DomainEvent>, DomainError> {
        order.create(self.customer_id.clone(), self.items.clone())?;
        Ok(vec![OrderCreated::new(self.order_id.clone())])
    }
}
```

### Read Model

```rust
#[derive(Queryable)]
pub struct OrderView {
    pub id: String,
    pub customer_name: String,
    pub total: Decimal,
    pub status: String,
    pub item_count: i32,
}

pub trait OrderQueries {
    fn get_by_id(&self, id: &OrderId) -> Result<Option<OrderView>, QueryError>;
    fn list_by_customer(&self, customer_id: &CustomerId) -> Result<Vec<OrderView>, QueryError>;
    fn search(&self, criteria: SearchCriteria) -> Result<Paginated<OrderView>, QueryError>;
}
```

### Projector (Event Handler)

```rust
pub struct OrderProjector {
    db: DatabaseConnection,
}

impl EventHandler for OrderProjector {
    fn handle(&self, event: DomainEvent) -> Result<(), HandlerError> {
        match event {
            DomainEvent::OrderCreated(e) => {
                diesel::insert_into(orders::table)
                    .values((
                        orders::id.eq(e.order_id.to_string()),
                        orders::customer_id.eq(e.customer_id.to_string()),
                        orders::status.eq("pending"),
                        orders::created_at.eq(Utc::now()),
                    ))
                    .execute(&self.db)?;
            }
            DomainEvent::OrderItemAdded(e) => {
                diesel::update(orders::table)
                    .filter(orders::id.eq(e.order_id.to_string()))
                    .set((
                        orders::total.eq(orders::total + e.price),
                        orders::item_count.eq(orders::item_count + 1),
                    ))
                    .execute(&self.db)?;
            }
            // ... other events
        }
        Ok(())
    }
}
```

## Data Consistency

### Eventual Consistency

```
Write ──▶ Event Store ──▶ Projector ──▶ Read DB
  │                              │         │
  │                              │         │
  └────────────── < 1s delay ─────┴─────────┘
```

### Handling Stale Reads

```rust
pub struct VersionedQuery<T> {
    data: T,
    version: u64,
    timestamp: DateTime<Utc>,
}

impl<T> VersionedQuery<T> {
    pub fn is_stale(&self, write_version: u64) -> bool {
        self.version < write_version
    }
}
```

## Patterns

### 1. Separate Databases

```yaml
# Write: PostgreSQL (ACID, normalized)
write_db: postgresql://primary.internal

# Read: Redis / Elasticsearch (fast, denormalized)
read_db: redis://cache.internal
search_db: elasticsearch://search.internal
```

### 2. Same Database, Different Schemas

```sql
-- Write schema (normalized)
CREATE TABLE orders.write_orders (
    id UUID PRIMARY KEY,
    customer_id UUID REFERENCES customers(id),
    status order_status,
    created_at TIMESTAMP
);

-- Read schema (denormalized)
CREATE TABLE orders.read_order_summaries (
    id UUID PRIMARY KEY,
    customer_name TEXT,  -- Denormalized
    total DECIMAL,
    item_count INT,
    status TEXT,
    updated_at TIMESTAMP
);
```

### 3. Materialized Views

```sql
CREATE MATERIALIZED VIEW order_summaries AS
SELECT 
    o.id,
    c.name as customer_name,
    SUM(oi.price * oi.quantity) as total,
    COUNT(oi.id) as item_count,
    o.status
FROM orders o
JOIN customers c ON o.customer_id = c.id
JOIN order_items oi ON o.id = oi.order_id
GROUP BY o.id, c.name, o.status;

-- Refresh strategy
CREATE OR REPLACE FUNCTION refresh_order_summaries()
RETURNS TRIGGER AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY order_summaries;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

## Testing

### Command Tests

```rust
#[test]
fn create_order_command_generates_event() {
    let mut order = Order::default();
    let cmd = CreateOrder::new(customer_id, items);
    
    let events = cmd.execute(&mut order).unwrap();
    
    assert_eq!(events.len(), 1);
    assert!(matches!(events[0], DomainEvent::OrderCreated(_)));
}
```

### Projection Tests

```rust
#[tokio::test]
async fn projector_updates_read_model() {
    let projector = OrderProjector::new(in_memory_db());
    
    projector.handle(OrderCreated::new(order_id)).await.unwrap();
    
    let view = read_db.get_order(order_id).await.unwrap();
    assert_eq!(view.status, "pending");
}
```

### Integration Tests

```rust
#[tokio::test]
async fn command_eventually_visible_in_query() {
    let cmd = CreateOrder::new(customer_id, items);
    
    // Execute command
    command_bus.send(cmd).await.unwrap();
    
    // Wait for projection
    tokio::time::sleep(Duration::from_millis(100)).await;
    
    // Verify in query model
    let view = query_bus.get_order(order_id).await.unwrap();
    assert!(view.is_some());
}
```

## Anti-Patterns

- ❌ Using CQRS for simple CRUD (unnecessary complexity)
- ❌ Synchronous projection (blocks writes)
- ❌ No handling of projection failures
- ❌ Ignoring eventual consistency in UI

## Related Patterns

- [Event Sourcing](./event-sourcing.md)
- [Event-Driven Architecture](./event-driven.md)
- [Outbox Pattern](./outbox.md)

## References

- [CQRS, Task Based UIs, Event Sourcing - Greg Young](https://cqrs.nu/)
- [Microsoft CQRS Pattern](https://docs.microsoft.com/en-us/azure/architecture/patterns/cqrs)
