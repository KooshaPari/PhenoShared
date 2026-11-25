# Hexacore — Workspace Specification

Rust workspace of 11 reusable hexagonal architecture kits for the Phenotype ecosystem.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Hexacore Workspace                       │
├──────────┬──────────┬──────────┬──────────┬─────────────────┤
│  clikit  │agentkit  │ evalkit  │ taskkit  │   configkit     │
├──────────┼──────────┼──────────┼──────────┼─────────────────┤
│ authkit  │ cachekit │  logkit  │tracingkit│   metrickit     │
├──────────┼──────────┴──────────┴──────────┴─────────────────┤
│ eventkit │         Shared: phenotype-contracts               │
└──────────┴──────────────────────────────────────────────────┘
```

Each kit follows hexagonal (ports & adapters) layers:

```
┌───────────────────────────────┐
│       Adapters Layer          │  CLI, HTTP, gRPC, DB, Queue
├───────────────────────────────┤
│        Ports Layer            │  Input/Output interfaces
├───────────────────────────────┤
│       Domain Layer            │  Entities, Value Objects, Events
├───────────────────────────────┤
│     Application Layer         │  Use Cases, Commands, Queries
└───────────────────────────────┘
```

## Components

| Kit | Purpose | Key Types |
|-----|---------|-----------|
| clikit | Universal CLI framework | App, Command, Flag, Arg |
| agentkit | Agent framework with skills | Agent, Skill, Context, Tool |
| evalkit | Evaluation framework | Evaluator, Metric, Benchmark |
| taskkit | Task execution framework | Task, Scheduler, Queue, Worker |
| configkit | Configuration management | Config, Provider, Loader |
| authkit | Auth/AuthZ framework | Token, Principal, Policy |
| cachekit | Caching abstraction | Cache, Store, Serializer |
| logkit | Structured logging | Logger, Span, Field |
| tracingkit | Distributed tracing | Tracer, Span, Context |
| metrickit | Metrics collection | Counter, Gauge, Histogram |
| eventkit | Event-driven architecture | Event, Bus, Store, Handler |

## Data Models

```rust
trait Port { fn name(&self) -> &str; }
trait InputPort: Port { fn execute(&self, cmd: Command) -> Result<Output>; }
trait OutputPort: Port { fn connect(&mut self) -> Result<()>; }

struct Entity<ID> { id: ID, created_at: SystemTime }
trait AggregateRoot<ID>: Entity<ID> {
    fn domain_events(&self) -> &[DomainEvent];
    fn clear_events(&mut self);
}
```

## API Design

```rust
// Kit initialization
let app = clikit::App::new("myapp")
    .command(HelloCommand::default())
    .middleware(LoggingMiddleware::new());

// Agent execution
let agent = agentkit::Agent::builder()
    .skill(WebSearch::new())
    .skill(CodeExec::new())
    .build();
let result = agent.execute(context, input).await?;

// Event publishing
let bus = eventkit::Bus::new();
bus.publish(OrderCreated { order_id }).await?;
```

## Workspace Layout

```
Hexacore/
├── Cargo.toml              # Workspace root
├── clikit/src/
├── agentkit/src/
├── evalkit/src/
├── taskkit/src/
├── configkit/src/
├── authkit/src/
├── cachekit/src/
├── logkit/src/
├── tracingkit/src/
├── metrickit/src/
└── eventkit/src/
```

## Performance Targets

| Metric | Target |
|--------|--------|
| Workspace build (cold) | < 60s |
| Workspace build (incremental) | < 5s |
| Test suite | < 30s |
| Clippy pass | 0 warnings |
| Individual kit size | < 10KB compiled |
| Zero unsafe | All kits |

## Quality Gates

- `cargo build --workspace` — clean build
- `cargo test --workspace` — all tests pass
- `cargo clippy --workspace -- -D warnings` — zero warnings
- `cargo fmt --check` — formatted
- All public types implement `Debug` + `Clone`
- Domain layer has zero external dependencies
