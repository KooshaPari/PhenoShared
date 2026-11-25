# Phenotype Core

Umbrella crate re-exporting all common phenotype crates for easier dependency management.

## Usage

Instead of adding 10+ individual phenotype crates, add just this one:

```toml
[dependencies]
phenotype-core = { workspace = true }
```

## Re-exports

### Error Handling
- `phenotype_error_core::ApiError`
- `phenotype_error_core::DomainError`
- `phenotype_error_core::RepositoryError`
- `phenotype_error_core::StorageError`

### Configuration
- `phenotype_config_core::ConfigLoader`
- `phenotype_config_core::Priority`

### Event Bus
- `phenotype_event_bus::EventBus`
- `phenotype_event_bus::EventEnvelope`
- `phenotype_event_bus::EventId` (ULID-based)

### Validation
- `phenotype_validation::ValidationRule`
- `phenotype_validation::RequiredRule`

### Health
- `phenotype_health::HealthChecker`
- `phenotype_health::HealthStatus`

### Ports
- `phenotype_port_traits::Repository`
- `phenotype_port_traits::CachePort`
- `phenotype_port_traits::SecretPort`

### Contracts
- `phenotype_contracts::InMemoryRepository`
- `phenotype_contracts::InMemoryCache`

### Async
- `phenotype_async_traits::AsyncIterator`
- `phenotype_retry::RetryPolicy`

### External Crates
- `ulid::Ulid` - Sortable unique IDs
- `dashmap::DashMap` - Concurrent HashMap

## Modules

- `prelude` - Wildcard import for most common types
- `types` - Type aliases for common results
- `external` - Re-exports of external crates
