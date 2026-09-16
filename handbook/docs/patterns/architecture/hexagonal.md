# Hexagonal Architecture Pattern

## Overview

Hexagonal Architecture (Ports and Adapters) is the foundational pattern for all Phenotype components.

## Structure

```
┌─────────────────────────────────────────┐
│           Application Layer             │
│  ┌─────────────────────────────────┐    │
│  │         Domain Layer            │    │
│  │  ┌─────────────────────────┐    │    │
│  │  │    Core Business Logic  │    │    │
│  │  └─────────────────────────┘    │    │
│  │         (No dependencies)       │    │
│  └─────────────────────────────────┘    │
│           │                 │            │
│    ┌──────┘                 └──────┐    │
│    ▼                               ▼    │
│ ┌──────────────┐          ┌────────────┐│
│ │   Ports      │          │   Ports    ││
│ │  (Inbound)   │          │ (Outbound) ││
│ └──────┬───────┘          └─────┬──────┘│
│        │                        │       │
│ ┌──────▼───────┐          ┌─────▼─────┐│
│ │  Adapters    │          │  Adapters ││
│ │ (Primary)    │          │(Secondary) ││
│ │   - HTTP     │          │  - DB     ││
│ │   - CLI      │          │  - Cache  ││
│ │   - Events   │          │  - Queue  ││
│ └──────────────┘          └───────────┘│
└─────────────────────────────────────────┘
```

## Rules

1. **Domain has zero external dependencies** - Only depends on language standard library
2. **Dependencies point inward** - Application depends on Domain, Adapters depend on Application
3. **Ports define interfaces** - Application defines what it needs (outbound) and provides (inbound)
4. **Adapters implement ports** - Concrete implementations are swappable

## Example

### Domain (Core)

```rust
// Domain has no dependencies
pub struct User {
    pub id: UserId,
    pub email: Email,
}

pub trait UserRepository {
    fn find_by_id(&self, id: UserId) -> Result<Option<User>, DomainError>;
    fn save(&self, user: &User) -> Result<(), DomainError>;
}
```

### Application (Use Cases)

```rust
// Application depends only on Domain
use crate::domain::{User, UserRepository, Email};

pub struct CreateUserUseCase<R: UserRepository> {
    repository: R,
}

impl<R: UserRepository> CreateUserUseCase<R> {
    pub fn execute(&self, email: Email) -> Result<User, ApplicationError> {
        // Business logic here
        let user = User::new(email)?;
        self.repository.save(&user)?;
        Ok(user)
    }
}
```

### Adapters (Infrastructure)

```rust
// Adapter depends on Application (inward dependency)
use phenotype_application::UserRepository;
use sqlx::PgPool;

pub struct SqlUserRepository {
    pool: PgPool,
}

impl UserRepository for SqlUserRepository {
    fn find_by_id(&self, id: UserId) -> Result<Option<User>, DomainError> {
        // SQL implementation
    }
}
```

## Phenotype Conventions

1. **Crate Structure:**
   ```
   phenotype-feature/
   ├── Cargo.toml
   ├── src/
   │   ├── domain/        # Core business logic
   │   ├── application/   # Use cases
   │   ├── adapters/      # Primary & secondary adapters
   │   └── lib.rs
   └── tests/
   ```

2. **Naming:**
   - Domain: `entities/`, `value_objects/`, `ports/`
   - Application: `use_cases/`, `services/`
   - Adapters: `inbound/`, `outbound/`

3. **Testing:**
   - Unit tests in domain (no mocks needed)
   - Integration tests with in-memory adapters
   - E2E tests with real infrastructure

## Anti-Patterns

- ❌ Domain depending on infrastructure
- ❌ Business logic in adapters
- ❌ Direct database calls from use cases
- ❌ Tight coupling to specific frameworks

## Related Patterns

- [Clean Architecture](clean-architecture.md)
- [Ports and Adapters](ports-adapters.md)
- [Dependency Inversion](dependency-inversion.md)

## References

- [AgilePlus Spec 001: Spec-Driven Development](../specs/platform/001-spec-driven-development-engine/spec.md)
- Original: [Alistair Cockburn's Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)
