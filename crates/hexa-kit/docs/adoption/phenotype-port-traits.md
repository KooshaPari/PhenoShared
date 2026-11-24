# phenotype-port-traits Adoption Guide

## Overview

`phenotype-port-traits` provides canonical async trait definitions for the hexagonal architecture pattern.

## Quick Start

### Add Dependency

```toml
[dependencies]
phenotype-port-traits = { path = "../crates/phenotype-port-traits" }
```

### Use Inbound Ports

```rust
use phenotype_port_traits::inbound::{UseCase, CommandHandler, QueryHandler};
use phenotype_port_traits::inbound::use_case::UseCase;
use async_trait::async_trait;

#[async_trait]
impl&lt;I, O&gt; UseCase&lt;I, O&gt; for MyService
where
    I: Send + Sync,
    O: Send + Sync,
{
    async fn execute(&self, input: I) -> Result&lt;O, Self::Error&gt; {
        // Your business logic
        Ok(output)
    }
}
```

### Use Outbound Ports

```rust
use phenotype_port_traits::outbound::{Repository, CachePort, EventPublisher};

#[async_trait]
impl&lt;E, I&gt; Repository&lt;E, I&gt; for SqliteRepository
where
    E: Entity + Send + Sync,
    I: EntityId + Send + Sync,
{
    async fn find(&self, id: &I) -> Result&lt;Option&lt;E&gt;, RepositoryError&gt; {
        // Implementation
        Ok(None)
    }
}
```

## Traits Available

### Inbound Ports

| Trait | Purpose | Methods |
|-------|---------|---------|
| `UseCase&lt;I, O&gt;` | Generic use case | `execute(input) -> Result&lt;O, E&gt;` |
| `CommandHandler&lt;C&gt;` | CQRS command handler | `handle(cmd) -> Result&lt;(), E&gt;` |
| `QueryHandler&lt;Q, R&gt;` | CQRS query handler | `handle(query) -> Result&lt;R, E&gt;` |
| `EventHandler&lt;E&gt;` | Domain event handler | `handle(event) -> Result&lt;(), E&gt;` |

### Outbound Ports

| Trait | Purpose | Methods |
|-------|---------|---------|
| `Repository&lt;E, I&gt;` | Persistence | `find`, `save`, `delete` |
| `CachePort` | Caching | `get`, `set`, `delete` |
| `EventPublisher` | Event emission | `publish`, `publish_batch` |
| `SecretPort` | Secrets management | `get`, `set`, `rotate` |

## Migration from Custom Traits

### Before

```rust
#[async_trait]
pub trait MyCustomRepository {
    async fn find(&self, id: &str) -> Result&lt;Option&lt;Entity&gt;, Error&gt;;
    async fn save(&self, entity: &Entity) -> Result&lt;(), Error&gt;;
}
```

### After

```rust
use phenotype_port_traits::outbound::Repository;
use phenotype_port_traits::models::{Entity, EntityId};

#[async_trait]
impl&lt;E, I&gt; Repository&lt;E, I&gt; for MyRepository
where
    E: Entity + Send + Sync,
    I: EntityId + Send + Sync,
{
    // Default implementations available for common patterns
}
```

## Feature Flags

```toml
[dependencies]
phenotype-port-traits = { 
    path = "../crates/phenotype-port-traits",
    features = ["inbound", "outbound", "models"]
}
```

## Related Crates

- `phenotype-error-core` - Error types compatible with these traits
- `phenotype-event-sourcing` - Event patterns using these traits
