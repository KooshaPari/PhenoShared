# ADR-002: NATS JetStream as Event Backbone

## Status

**Accepted** — 2026-04-04

## Context

The Phenotype ecosystem requires a unified messaging infrastructure for:

1. **Event-Driven Communication** — Service-to-service async messaging
2. **Command Distribution** — Workflow step distribution
3. **Log Aggregation** — Centralized logging pipeline
4. **Configuration Propagation** — Dynamic config updates
5. **Observability** — Distributed tracing spans, metrics

Current state analysis:
- Multiple Redis instances for caching and pub/sub (separation of concerns violation)
- No persistent messaging for critical events
- No built-in observability integration
- Custom retry logic scattered across services

Requirements:
| Requirement | Priority | Notes |
|-------------|----------|-------|
| At-least-once delivery | P0 | Critical for workflow events |
| Exactly-once semantics | P1 | Idempotency still required |
| Ordering guarantees | P1 | Per-aggregate ordering |
| Horizontal scaling | P1 | Add nodes as load increases |
| Multi-region | P2 | Active-active deployments |
| Low latency | P1 | < 10ms p99 for local clusters |
| Persistence | P0 | Survive broker restarts |
| Observability | P1 | OpenTelemetry integration |
| Rust ecosystem | P0 | First-class async support |

## Decision

We will adopt **NATS JetStream** as the unified event backbone for the Phenotype ecosystem.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    NATS JetStream Topology                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                     NATS Cluster                             ││
│  │                                                              ││
│  │   ┌─────────┐      ┌─────────┐      ┌─────────┐            ││
│  │   │ Server  │◄────►│ Server  │◄────►│ Server  │            ││
│  │   │  n0     │      │  n1     │      │  n2     │            ││
│  │   │ (RAFT)  │      │ (RAFT)  │      │ (RAFT)  │            ││
│  │   └────┬────┘      └────┬────┘      └────┬────┘            │
│  │        │                │                │                  ││
│  │        └────────────────┴────────────────┘                  ││
│  │                     │                                      ││
│  │              ┌──────┴──────┐                               ││
│  │              │ Meta Group   │ (Cluster management)          ││
│  │              └─────────────┘                               ││
│  │                                                              ││
│  │   Streams:                                                   ││
│  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        ││
│  │   │ WORKFLOW    │  │ DOMAIN      │  │ LOGS        │        ││
│  │   │ (3 replicas)│  │ (3 replicas)│  │ (1 replica) │        ││
│  │   │ Retention:  │  │ Retention:  │  │ Retention:  │        ││
│  │   │ Limits      │  │ WorkQueue   │  │ Interest    │        ││
│  │   └─────────────┘  └─────────────┘  └─────────────┘        ││
│  │                                                              ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  Consumers:                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ Durable     │  │ Durable     │  │ Ephemeral   │              │
│  │ Push        │  │ Pull        │  │ Request-Reply              │
│  │ (Notify)    │  │ (Workers)   │  │ (RPC)       │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Stream Design

| Stream | Subjects | Retention | Replicas | Max Age |
|--------|----------|-----------|----------|---------|
| **WORKFLOW** | `workflow.>` | Limits | 3 | 7 days |
| **DOMAIN** | `domain.*.events` | WorkQueue | 3 | 30 days |
| **COMMANDS** | `commands.>` | WorkQueue | 3 | 1 day |
| **LOGS** | `logs.>` | Interest | 1 | 1 day |
| **TRACES** | `traces.>` | Interest | 1 | 1 hour |
| **CONFIG** | `config.>` | Limits | 3 | Forever |

### Subject Patterns

```
Domain Events:
  domain.{aggregate_type}.{aggregate_id}.{event_type}.{version}
  domain.user.123e4567-e89b-12d3.UserCreated.v1

Workflow Events:
  workflow.{workflow_id}.{step_id}.{status}
  workflow.abc123.step1.started
  workflow.abc123.step1.completed

Commands:
  commands.{service}.{action}
  commands.order-service.CreateOrder

Logs:
  logs.{service}.{level}
  logs.helios-cli.error
```

### Rust Implementation

```rust
// Domain - Port Definition
#[async_trait::async_trait]
pub trait EventBus: Send + Sync {
    async fn publish<E: DomainEvent>(&self, event: E) -> Result<(), EventBusError>;
    async fn subscribe<E: DomainEvent, H: EventHandler<E>>(
        &self,
        handler: H,
    ) -> Result<Subscription, EventBusError>;
}

// Application - Use Case
pub struct CreateOrderUseCase<B: EventBus, R: OrderRepository> {
    event_bus: B,
    repository: R,
}

impl<B: EventBus, R: OrderRepository> CreateOrderUseCase<B, R> {
    pub async fn execute(&self, cmd: CreateOrderCommand) -> Result<Order, DomainError> {
        let order = Order::create(cmd)?;
        self.repository.save(&order).await?;
        
        // Publish domain event
        self.event_bus.publish(OrderCreated::from(&order)).await?;
        
        Ok(order)
    }
}

// Adapter - NATS Implementation
pub struct NatsEventBus {
    jetstream: async_nats::jetstream::Context,
    tracer: Arc<dyn Tracer>,
}

#[async_trait::async_trait]
impl EventBus for NatsEventBus {
    async fn publish<E: DomainEvent>(&self, event: E) -> Result<(), EventBusError> {
        let subject = format!(
            "domain.{}.{}.{}.v{}",
            E::aggregate_type(),
            event.aggregate_id(),
            E::event_type(),
            E::version()
        );
        
        let payload = serde_json::to_vec(&event)?;
        
        // Include trace context
        let headers = self.build_trace_headers();
        
        self.jetstream
            .publish_with_headers(subject, headers, payload.into())
            .await?;
            
        Ok(())
    }
    
    async fn subscribe<E: DomainEvent, H: EventHandler<E>>(
        &self,
        handler: H,
    ) -> Result<Subscription, EventBusError> {
        let consumer = self.jetstream
            .create_consumer_on_stream(
                Config {
                    name: Some(format!("{}-consumer", H::name())),
                    durable_name: Some(H::name()),
                    deliver_policy: DeliverPolicy::All,
                    ack_policy: AckPolicy::Explicit,
                    max_deliver: 3,
                    ..Default::default()
                },
                "DOMAIN",
            )
            .await?;
            
        // Spawn consumer task
        tokio::spawn(async move {
            while let Some(message) = consumer.next().await {
                if let Err(e) = Self::process_message(&handler, &message).await {
                    error!(error = %e, "Message processing failed");
                    // After max_deliver, goes to DLQ
                }
            }
        });
        
        Ok(Subscription)
    }
}
```

## Consequences

### Positive

1. **Unified Infrastructure** — One system for events, commands, logs
2. **Persistence** — Events survive restarts, enable replay
3. **Observability** — Native OTel integration, message tracing
4. **Scalability** — Horizontal scaling via cluster
5. **Rust Native** — Excellent async support, no FFI
6. **Cloud Native** — Kubernetes operator available
7. **Zero Dependencies** — Single binary deployment

### Negative

1. **Operational Complexity** — Cluster management required
2. **New Technology** — Team learning curve
3. **Migration Effort** — Move from Redis pub/sub
4. **Backup Strategy** — Stream backup/restore procedures

### Mitigations

- Single-node mode for development
- Kubernetes operator for production
- Incremental migration (dual-publish during transition)
- Automated backup to S3

## Alternatives Considered

| Alternative | Pros | Cons | Verdict |
|-------------|------|------|---------|
| **Redis Streams** | Already deployed | No persistence guarantee, limited scaling | Rejected |
| **Apache Kafka** | Mature ecosystem | Heavyweight, JVM dependency | Rejected |
| **RabbitMQ** | Good routing | Complex clustering, throughput | Rejected |
| **Amazon SNS/SQS** | Managed | Vendor lock-in, latency | Rejected |
| **GCP Pub/Sub** | Managed | Vendor lock-in, cost at scale | Rejected |
| **Pulsar** | Good features | Operational complexity | Rejected |
| **NATS Core** | Simple | No persistence | Insufficient |
| **NATS JetStream** | Persistence + simplicity | Newer ecosystem | **Selected** |

## Migration Plan

### Phase 1: Development Setup (Week 1)
- [ ] Single-node NATS for local dev
- [ ] Docker compose configuration
- [ ] Basic publisher/subscriber implementations

### Phase 2: Core Integration (Weeks 2-4)
- [ ] heliosCLI workflow events
- [ ] Domain event publishing
- [ ] Command distribution

### Phase 3: Production Cluster (Weeks 5-6)
- [ ] 3-node cluster deployment
- [ ] Stream configuration
- [ ] Monitoring integration

### Phase 4: Migration (Weeks 7-8)
- [ ] Dual-publish to Redis and NATS
- [ ] Gradual consumer migration
- [ ] Redis pub/sub deprecation

### Phase 5: Cleanup (Week 9)
- [ ] Remove Redis pub/sub code
- [ ] Documentation updates
- [ ] Team training

## Configuration

```yaml
# nats-server.conf
jetstream {
    store_dir: "/data/jetstream"
    max_memory_store: 1GB
    max_file_store: 100GB
}

cluster {
    name: "phenotype"
    listen: "0.0.0.0:6222"
    routes: [
        "nats://nats-0.nats:6222",
        "nats://nats-1.nats:6222",
        "nats://nats-2.nats:6222"
    ]
}

# helios-cli configuration
messaging:
  provider: nats
  servers:
    - nats://nats-0.nats:4222
    - nats://nats-1.nats:4222
    - nats://nats-2.nats:4222
  jetstream:
    enabled: true
    replicas: 3
  streams:
    workflow:
      max_age: 7d
      retention: limits
    domain:
      max_age: 30d
      retention: workqueue
```

## Monitoring

| Metric | Type | Alert Threshold |
|--------|------|-----------------|
| `nats_server_cpu` | Gauge | > 80% |
| `nats_server_mem` | Gauge | > 80% |
| `nats_varz_connections` | Gauge | Baseline + 50% |
| `nats_stream_msgs` | Counter | Growth rate |
| `nats_consumer_pending` | Gauge | > 1000 |
| `nats_consumer_delivered` | Counter | < expected rate |

## References

1. [NATS JetStream Documentation](https://docs.nats.io/nats-concepts/jetstream)
2. [NATS Rust Client](https://github.com/nats-io/nats.rs)
3. [Event-Driven Architecture Pattern](../../patterns/async/event-driven.md)
4. [Outbox Pattern](../../patterns/async/outbox.md)
5. [SAGA-001: Workflow Engine with JetStream](../specs/messaging/saga-001.md)

## Notes

This ADR establishes NATS JetStream as the primary messaging infrastructure. Redis remains in use for caching (separation of concerns).

---

*Decision Date: 2026-04-04*  
*Decision Makers: Phenotype Platform Team*  
*Next Review: 2026-10-04*