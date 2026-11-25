# CQRS (Command Query Responsibility Segregation)

## Overview

**CQRS** separates read and write operations into different models, allowing optimization for each workload independently.

```
┌─────────────────────────────────────────────────────────────┐
│                     TRADITIONAL CRUD                        │
│                                                             │
│   ┌─────────┐    ┌───────────────┐    ┌─────────┐           │
│   │ Client  │───▶│ Order Service │───▶│ Orders  │           │
│   └─────────┘    │ (CRUD)        │    │  Table  │           │
│   ┌─────────┐    └───────────────┘    └─────────┘           │
│   │ Client  │───▶│ Order Service │───▶│ Orders  │           │
│   └─────────┘    │ (CRUD)        │    │  Table  │           │
│                  └───────────────┘    └─────────┘           │
│                                                             │
└─────────────────────────────────────────────────────────────┘

                        VS

┌─────────────────────────────────────────────────────────────┐
│                        CQRS                                  │
│                                                             │
│  WRITE SIDE                          READ SIDE              │
│  ┌─────────┐    ┌──────────┐         ┌──────────┐          │
│  │         │───▶│ Commands │         │ Queries  │          │
│  │ Client  │    │          │         │          │          │
│  │         │───▶│ Create   │         │ GetOrder │          │
│  └─────────┘    │ Update   │         │ List     │          │
│                 │ Delete   │         │ Search   │          │
│                 └────┬─────┘         └────┬─────┘          │
│                      │                    │                  │
│                      ▼                    ▼                  │
│            ┌──────────────────┐    ┌──────────────────┐     │
│            │  Command Model   │    │   Query Model    │     │
│            │  (Orders Table)  │    │  (Read Model)    │     │
│            │  - Full domain   │    │  - Flattened     │     │
│            │  - Validated     │    │  - Optimized     │     │
│            │  - Events        │    │  - Projections   │     │
│            └──────────────────┘    └──────────────────┘     │
│                      │                    ▲                  │
│                      │                    │                  │
│                      └─────Event Bus───────┘                  │
└─────────────────────────────────────────────────────────────┘
```

## When to Use

### ✅ Use CQRS When

- Different read/write patterns (1000 reads : 1 write)
- Complex query requirements (search, analytics)
- Need different data models for operations
- Microservices with different consumers
- Event sourcing (natural fit)

### ❌ Don't Use When

- Simple CRUD applications
- Small teams (cognitive overhead)
- Strong consistency required everywhere
- No performance/query complexity issues

## Implementation

### Core Interfaces

```rust
// Command side
pub trait CommandHandler<C: Command> {
    type Error: std::error::Error;
    type Result;
    
    async fn handle(&self, command: C) -> Result<Self::Result, Self::Error>;
}

pub trait Command: Send + Sync {
    fn command_type() -> &'static str;
}

// Query side
pub trait QueryHandler<Q: Query> {
    type Error: std::error::Error;
    type Result;
    
    async fn handle(&self, query: Q) -> Result<Self::Result, Self::Error>;
}

pub trait Query: Send + Sync {
    fn query_type() -> &'static str;
}
```

### Command Model

```rust
// Write-optimized model
pub struct Order {
    id: OrderId,
    customer_id: CustomerId,
    items: Vec<OrderItem>,
    status: OrderStatus,
    shipping_address: Address,
    payment_method: PaymentMethod,
    version: u64,
}

impl Aggregate for Order {
    type Command = OrderCommand;
    type Event = OrderEvent;
    type Error = OrderError;
    
    fn handle(&mut self, command: Self::Command) -> Result<Vec<Self::Event>, Self::Error> {
        match command {
            OrderCommand::Create { customer_id, items, address, payment } => {
                self.validate_items(&items)?;
                Ok(vec![OrderEvent::Created {
                    order_id: OrderId::new(),
                    customer_id,
                    items,
                    address,
                    payment,
                    created_at: Utc::now(),
                }])
            }
            OrderCommand::Cancel { reason } => {
                if self.status == OrderStatus::Shipped {
                    return Err(OrderError::CannotCancelShipped);
                }
                Ok(vec![OrderEvent::Cancelled {
                    order_id: self.id.clone(),
                    reason,
                    cancelled_at: Utc::now(),
                }])
            }
            // ... more commands
        }
    }
}
```

### Query Model (Projection)

```rust
// Read-optimized, denormalized model
pub struct OrderView {
    pub id: String,
    pub customer_name: String,        // Denormalized
    pub customer_email: String,         // Denormalized
    pub items: Vec<OrderItemView>,    // Simplified structure
    pub total_amount: Decimal,          // Pre-calculated
    pub status: String,               // Simple string
    pub shipping_city: String,          // Flattened
    pub shipping_country: String,     // Flattened
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

// Separate collections for different query patterns
pub struct OrderListItem {
    pub id: String,
    pub customer_name: String,
    pub total_amount: Decimal,
    pub status: String,
    pub item_count: i32,
}

pub struct OrderSearchDocument {
    pub id: String,
    pub searchable_text: String,    // Combined customer + items
    pub total_amount: Decimal,
    pub status: String,
    pub tags: Vec<String>,
}
```

### Command Handler

```rust
pub struct CreateOrderHandler {
    order_repo: Arc<dyn OrderRepository>,
    event_bus: Arc<dyn EventBus>,
    outbox: Arc<dyn OutboxRepository>,
}

#[async_trait]
impl CommandHandler<CreateOrder> for CreateOrderHandler {
    type Error = OrderError;
    type Result = OrderId;
    
    async fn handle(&self, command: CreateOrder) -> Result<OrderId, OrderError> {
        // Start transaction
        let mut tx = self.order_repo.begin().await?;
        
        // Load aggregate (or create new)
        let mut order = Order::create(
            command.customer_id,
            command.items,
            command.address,
            command.payment,
        )?;
        
        // Save aggregate
        self.order_repo.save(&mut order).await?;
        
        // Prepare outbox events
        let events: Vec<OutboxEvent> = order
            .uncommitted_events()
            .iter()
            .map(|e| e.into())
            .collect();
        
        // Append to outbox
        self.outbox.append(events).await?;
        
        // Commit
        tx.commit().await?;
        
        // Return result
        Ok(order.id())
    }
}
```

### Query Handler

```rust
pub struct GetOrderHandler {
    order_view_repo: Arc<dyn OrderViewRepository>,
}

#[async_trait]
impl QueryHandler<GetOrder> for GetOrderHandler {
    type Error = QueryError;
    type Result = Option<OrderView>;
    
    async fn handle(&self, query: GetOrder) -> Result<Option<OrderView>, QueryError> {
        // Simple, optimized read
        self.order_view_repo
            .get_by_id(&query.order_id)
            .await
            .map_err(|e| QueryError::database_error(e))
    }
}

pub struct SearchOrdersHandler {
    search_repo: Arc<dyn OrderSearchRepository>,
}

#[async_trait]
impl QueryHandler<SearchOrders> for SearchOrdersHandler {
    type Error = QueryError;
    type Result = PaginatedResult<OrderListItem>;
    
    async fn handle(&self, query: SearchOrders) -> Result<PaginatedResult<OrderListItem>, QueryError> {
        // Complex search handled by search-optimized repository
        self.search_repo
            .search(
                query.search_term,
                query.filters,
                query.sort,
                query.pagination,
            )
            .await
    }
}
```

### Projection Updater

```rust
pub struct OrderProjectionUpdater {
    order_view_repo: Arc<dyn OrderViewRepository>,
    customer_repo: Arc<dyn CustomerRepository>,
}

impl EventHandler<OrderEvent> for OrderProjectionUpdater {
    async fn handle(&self, event: OrderEvent) -> Result<(), ProjectionError> {
        match event {
            OrderEvent::Created { order_id, customer_id, items, address, .. } => {
                // Fetch denormalized data
                let customer = self.customer_repo.get(&customer_id).await?;
                
                // Calculate derived fields
                let total_amount: Decimal = items.iter()
                    .map(|i| i.price * i.quantity)
                    .sum();
                
                // Build view
                let view = OrderView {
                    id: order_id.to_string(),
                    customer_name: customer.name,
                    customer_email: customer.email,
                    items: items.into_iter().map(|i| i.into()).collect(),
                    total_amount,
                    status: "created".to_string(),
                    shipping_city: address.city,
                    shipping_country: address.country,
                    created_at: Utc::now(),
                    updated_at: Utc::now(),
                };
                
                // Upsert to read model
                self.order_view_repo.upsert(&view).await?;
                
                // Update search index
                self.update_search_index(&view).await?;
            }
            OrderEvent::Cancelled { order_id, .. } => {
                self.order_view_repo
                    .update_status(&order_id.to_string(), "cancelled")
                    .await?;
            }
            OrderEvent::Shipped { order_id, tracking_number, .. } => {
                self.order_view_repo
                    .update_shipped(&order_id.to_string(), tracking_number)
                    .await?;
            }
            // ... handle all event types
        }
        
        Ok(())
    }
}
```

## Data Stores

### Typical CQRS Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                         CQRS SYSTEM                            │
│                                                                │
│  COMMAND SIDE                                                  │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────────┐   │
│  │ Command API │────▶│  Command    │────▶│  Event Store    │   │
│  │  (REST)     │     │  Handlers   │     │  (PostgreSQL)   │   │
│  └─────────────┘     └──────┬──────┘     │                 │   │
│                             │            │  - Events table │   │
│                             │            │  - Snapshots    │   │
│                             ▼            └─────────────────┘   │
│                       ┌─────────────┐                            │
│                       │  Outbox     │                            │
│                       │  Table      │                            │
│                       └──────┬──────┘                            │
│                              │                                   │
│                              ▼                                   │
│                       ┌─────────────┐                            │
│                       │  Event Bus  │                            │
│                       │  (NATS)     │                            │
│                       └──────┬──────┘                            │
│                              │                                   │
└──────────────────────────────┼───────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────┼───────────────────────────────────┐
│                              │                                   │
│  QUERY SIDE                  │                                   │
│  ┌─────────────┐     ┌───────┴───────┐     ┌─────────────────┐   │
│  │  Query API  │────▶│   Projection  │◀────│   Read Models   │   │
│  │  (GraphQL)  │     │    Updater    │     │                 │   │
│  └─────────────┘     └───────────────┘     │  - PostgreSQL   │   │
│                              │             │  - Elasticsearch│   │
│                              │             │  - Redis        │   │
│                              │             │  - MongoDB      │   │
│                              ▼             └─────────────────┘   │
│                       ┌─────────────┐                            │
│                       │ Search Index│                            │
│                       │ (MeiliSearch│                            │
│                       │ or Algolia) │                            │
│                       └─────────────┘                            │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### Command Store Options

| Store | Use Case | Consistency |
|-------|----------|-------------|
| PostgreSQL | Event sourcing with JSONB | Strong |
| MongoDB | Document-based commands | Eventual |
| DynamoDB | Serverless | Eventual |

### Read Model Options

| Store | Use Case | Query Types |
|-------|----------|-------------|
| PostgreSQL | Relational queries, joins | SQL |
| Elasticsearch | Full-text search | Search DSL |
| Redis | Caching, leaderboards | Key-value |
| MongoDB | Document queries | Aggregation |
| ClickHouse | Analytics | OLAP |

## Consistency Models

### 1. Eventual Consistency (Recommended)

```rust
// Command returns immediately, projection updates async
let order_id = command_bus
    .send(CreateOrder { ... })
    .await?;

// Read may be stale briefly
let order = query_bus
    .send(GetOrder { order_id })
    .await?;
    
// Handle "not found yet" case
match order {
    Some(o) => Ok(o),
    None => {
        // Wait briefly or return "processing"
        sleep(Duration::from_millis(100)).await;
        query_bus.send(GetOrder { order_id }).await
    }
}
```

### 2. Read-Your-Writes

```rust
pub struct CommandWithSyncRead {
    command_bus: Arc<dyn CommandBus>,
    query_bus: Arc<dyn QueryBus>,
    projection_timeout: Duration,
}

impl CommandWithSyncRead {
    pub async fn execute<C, Q>(
        &self,
        command: C,
        query: Q,
    ) -> Result<Q::Result, Error>
    where
        C: Command,
        Q: Query,
    {
        // Execute command
        let result = self.command_bus.send(command).await?;
        
        // Poll for projection
        let start = Instant::now();
        loop {
            if let Ok(Some(data)) = self.query_bus.send(query.clone()).await {
                return Ok(data);
            }
            
            if start.elapsed() > self.projection_timeout {
                return Err(Error::projection_timeout());
            }
            
            sleep(Duration::from_millis(10)).await;
        }
    }
}
```

### 3. Strong Consistency (Synchronous Projection)

```rust
pub struct SynchronousCQRS {
    command_handler: Arc<dyn CommandHandler<CreateOrder>>,
    projection_updater: Arc<dyn ProjectionUpdater>,
}

impl SynchronousCQRS {
    async fn execute(&self, command: CreateOrder) -> Result<OrderView, Error> {
        // Execute command
        let order_id = self.command_handler.handle(command).await?;
        
        // Synchronously update projection
        self.projection_updater
            .update_for_aggregate(&order_id)
            .await?;
        
        // Now read is guaranteed consistent
        self.query_bus
            .send(GetOrder { order_id })
            .await
            .map(|o| o.ok_or(Error::NotFound))
    }
}
```

## API Design

### Command API (REST)

```rust
#[post("/orders")]
async fn create_order(
    body: Json<CreateOrderRequest>,
    bus: Data<CommandBus>,
) -> Result<HttpResponse, ApiError> {
    let command = body.into_inner().into_command()?;
    let order_id = bus.send(command).await?;
    
    // Return 202 Accepted for async processing
    // Or 201 Created for synchronous
    Ok(HttpResponse::Created()
        .insert_header(("Location", format!("/orders/{}", order_id)))
        .json(json!({ "order_id": order_id })))
}

#[post("/orders/{id}/cancel")]
async fn cancel_order(
    path: Path<OrderId>,
    body: Json<CancelOrderRequest>,
    bus: Data<CommandBus>,
) -> Result<HttpResponse, ApiError> {
    let command = CancelOrder {
        order_id: path.into_inner(),
        reason: body.reason.clone(),
    };
    
    bus.send(command).await?;
    Ok(HttpResponse::Ok().finish())
}
```

### Query API (GraphQL)

```graphql
type Order {
  id: ID!
  customerName: String!
  customerEmail: String!
  items: [OrderItem!]!
  totalAmount: Float!
  status: OrderStatus!
  shippingCity: String!
  shippingCountry: String!
  createdAt: DateTime!
}

type Query {
  order(id: ID!): Order
  orders(
    filter: OrderFilter
    sort: OrderSort
    pagination: PaginationInput
  ): OrderConnection!
  searchOrders(query: String!): [Order!]!
}

input OrderFilter {
  status: OrderStatus
  customerId: ID
  dateFrom: DateTime
  dateTo: DateTime
  minAmount: Float
  maxAmount: Float
}
```

```rust
pub struct OrderQueryRoot;

#[Object]
impl OrderQueryRoot {
    async fn order(&self, ctx: &Context<'_>, id: ID) -> Result<Option<Order>, Error> {
        let bus = ctx.data::<QueryBus>()?;
        bus.send(GetOrder { order_id: id.into() }).await
    }
    
    async fn orders(
        &self,
        ctx: &Context<'_>,
        filter: Option<OrderFilter>,
        sort: Option<OrderSort>,
        pagination: Option<PaginationInput>,
    ) -> Result<OrderConnection, Error> {
        let bus = ctx.data::<QueryBus>()?;
        bus.send(ListOrders {
            filter,
            sort: sort.unwrap_or_default(),
            pagination: pagination.unwrap_or_default(),
        }).await
    }
}
```

## Testing Strategies

### Command Side Testing

```rust
#[tokio::test]
async fn create_order_saves_and_emits_event() {
    let repo = InMemoryOrderRepository::new();
    let outbox = InMemoryOutbox::new();
    let handler = CreateOrderHandler::new(repo.clone(), outbox.clone());
    
    let command = CreateOrder {
        customer_id: CustomerId::new(),
        items: vec![test_item()],
        address: test_address(),
        payment: test_payment(),
    };
    
    let order_id = handler.handle(command).await.unwrap();
    
    // Verify aggregate saved
    assert!(repo.get(&order_id).await.unwrap().is_some());
    
    // Verify event in outbox
    let events = outbox.events_for_aggregate(&order_id).await.unwrap();
    assert_eq!(events.len(), 1);
    assert!(matches!(events[0], OutboxEvent::OrderCreated { .. }));
}

#[tokio::test]
async fn cancel_shipped_order_fails() {
    let repo = InMemoryOrderRepository::with_order(Order::shipped_test_order());
    let handler = CancelOrderHandler::new(repo);
    
    let result = handler.handle(CancelOrder {
        order_id: test_order_id(),
        reason: "test".to_string(),
    }).await;
    
    assert!(matches!(result, Err(OrderError::CannotCancelShipped)));
}
```

### Query Side Testing

```rust
#[tokio::test]
async fn get_order_returns_projection() {
    let repo = InMemoryOrderViewRepository::with_views(vec![
        OrderView::test_order(),
    ]);
    let handler = GetOrderHandler::new(repo);
    
    let result = handler.handle(GetOrder {
        order_id: test_order_id(),
    }).await.unwrap();
    
    assert!(result.is_some());
    let view = result.unwrap();
    assert_eq!(view.customer_name, "Test Customer");
}

#[tokio::test]
async fn search_finds_by_customer_name() {
    let search_repo = InMemorySearchRepository::with_documents(vec![
        OrderSearchDocument::for_customer("Alice"),
        OrderSearchDocument::for_customer("Bob"),
    ]);
    let handler = SearchOrdersHandler::new(search_repo);
    
    let results = handler.handle(SearchOrders {
        search_term: "Alice".to_string(),
        ..Default::default()
    }).await.unwrap();
    
    assert_eq!(results.items.len(), 1);
    assert_eq!(results.items[0].customer_name, "Alice");
}
```

### Integration Testing

```rust
#[tokio::test]
async fn command_eventually_projects_to_query_model() {
    let system = TestCQRS::new().await;
    
    // Execute command
    let order_id = system
        .command_bus
        .send(CreateOrder { ... })
        .await
        .unwrap();
    
    // Wait for projection
    system.wait_for_projection(&order_id, Duration::from_secs(5)).await;
    
    // Query should now find it
    let order = system
        .query_bus
        .send(GetOrder { order_id })
        .await
        .unwrap();
    
    assert!(order.is_some());
}
```

## Anti-Patterns

- ❌ Same data model for commands and queries
- ❌ Synchronous projection on hot path
- ❌ No handling for eventual consistency in UI
- ❌ Complex business logic in query handlers
- ❌ Writing to read models
- ❌ N+1 queries in projections

## Related Patterns

- [Event Sourcing](./event-sourcing.md)
- [Outbox Pattern](./outbox.md)
- [Saga Pattern](./saga.md)
- [Event-Driven Architecture](./event-driven.md)

## References

- [CQRS, Task-Based UIs, Event Sourcing - Greg Young](https://cqrs.files.wordpress.com/2010/11/cqrs_documents.pdf)
- [Microsoft CQRS Journey](https://docs.microsoft.com/en-us/previous-versions/msp-n-p/jj554200(v=pandp.10))
- [CQRS and Event Sourcing on AWS](https://docs.aws.amazon.com/prescriptive-guidance/latest/modernization-data-intensive-apps-event-driven-architecture/cqrs-pattern.html)
