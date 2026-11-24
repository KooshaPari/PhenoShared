# ADR-001: Hexagonal Architecture as Foundational Pattern

## Status

**Accepted** — 2026-04-04

## Context

The Phenotype ecosystem requires a consistent architectural approach across all components:

- **heliosCLI**: Command-line interface and workflow engine
- **thegent**: Dotfiles and environment management
- **portage**: Repository adapter and migration tool
- **AgilePlus**: Spec-driven development platform
- **heliosApp**: Web application framework

We need an architecture that supports:
1. **Testability** — Easy to test without complex mocking infrastructure
2. **Technology Independence** — Ability to swap implementations (DB, HTTP framework, etc.)
3. **Parallel Development** — Teams can work on different adapters simultaneously
4. **Domain Clarity** — Business logic separated from technical concerns
5. **Maintenance** — Long-term code health and refactoring ease

## Decision

We will adopt **Hexagonal Architecture** (Ports and Adapters) as the foundational pattern for all Phenotype components.

### Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                    Hexagonal Architecture                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                      Domain Layer                            ││
│  │                    (Core Business Logic)                     ││
│  │                                                              ││
│  │  • Entities (User, Order, Workflow)                          ││
│  │  • Value Objects (Email, Money, Status)                     ││
│  │  • Domain Services (Pure functions)                         ││
│  │  • Domain Events (Business facts)                         ││
│  │                                                              ││
│  │  ZERO EXTERNAL DEPENDENCIES                                 ││
│  └─────────────────────────────────────────────────────────────┘│
│                           │                                      │
│                           │ (depends on)                         │
│                           ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                   Application Layer                          ││
│  │                  (Use Cases / Orchestration)                  ││
│  │                                                              ││
│  │  • Use Cases (CreateUser, ProcessOrder)                     ││
│  │  • Application Services (Transaction handling)              ││
│  │  • Ports (Repository interfaces)                            ││
│  │  • DTOs (Request/Response objects)                         ││
│  │                                                              ││
│  │  Depends only on Domain Layer                                ││
│  └─────────────────────────────────────────────────────────────┘│
│                           │                                      │
│          ┌────────────────┼────────────────┐                      │
│          │                │                │                      │
│          ▼                │                ▼                      │
│  ┌───────────────┐       │        ┌───────────────┐             │
│  │ Primary       │       │        │ Secondary     │             │
│  │ Adapters      │       │        │ Adapters      │             │
│  │ (Inbound)     │       │        │ (Outbound)    │             │
│  │               │       │        │               │             │
│  │ • CLI         │       │        │ • PostgreSQL  │             │
│  │ • HTTP API    │       │        │ • Redis       │             │
│  │ • Events      │       │        │ • NATS        │             │
│  │ • Scheduler   │       │        │ • Email       │             │
│  └───────────────┘       │        └───────────────┘             │
│                          │                                      │
│  All adapters implement ports defined by Application layer      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Dependency Rule

The fundamental rule: **Dependencies point INWARD only.**

```
Domain → Application → Adapters
   │         │            │
   │         │            │
   ▼         ▼            ▼
No deps   Domain only   App + Domain
```

### Crate Structure (Rust)

```
phenotype-component/
├── Cargo.toml
├── src/
│   ├── domain/              # No external deps
│   │   ├── entities/
│   │   ├── value_objects/
│   │   ├── errors.rs
│   │   └── ports.rs         # Trait definitions
│   │
│   ├── application/         # Depends on domain
│   │   ├── use_cases/
│   │   ├── services/
│   │   └── dto.rs
│   │
│   ├── adapters/            # Depends on application
│   │   ├── primary/
│   │   │   ├── cli/
│   │   │   ├── http/
│   │   │   └── scheduler/
│   │   └── secondary/
│   │       ├── postgres/
│   │       ├── redis/
│   │       └── nats/
│   │
│   └── lib.rs
│
└── tests/
    ├── unit/               # Domain tests (no mocks)
    ├── integration/        # Adapter tests
    └── e2e/               # Full flow tests
```

## Consequences

### Positive

1. **Testability** — Domain logic tests require no mocks (pure functions)
2. **Flexibility** — Swap PostgreSQL for DynamoDB by implementing same port
3. **Parallel Development** — Team A works on HTTP adapter, Team B on domain
4. **Technology Decoupling** — Business logic survives framework changes
5. **Clear Boundaries** — Easy to identify what belongs where

### Negative

1. **Initial Complexity** — More files and abstractions than simple CRUD
2. **Learning Curve** — Team must understand dependency direction
3. **Boilerplate** — Some repetitive adapter code
4. **Over-engineering Risk** — Simple features may feel heavyweight

### Mitigations

- Use code generation (portage) for adapter scaffolding
- Provide templates in HexaKit
- Document clear criteria for when to use simpler patterns

## Alternatives Considered

| Alternative | Pros | Cons | Verdict |
|-------------|------|------|---------|
| **Layered Architecture** | Simple, familiar | Business logic leaks to UI, hard to test | Rejected |
| **Clean Architecture** | Similar benefits | More layers, rigid structure | Reference only |
| **Onion Architecture** | Domain-centric | Overlapping concepts | Reference only |
| **Microservices** | Independent deploy | Operational complexity | Apply at service boundary |
| **Simple CRUD** | Fast to write | Technical debt accumulation | Rejected |

## Implementation

### Phase 1: New Components
All new Phenotype components must implement hexagonal architecture from day one.

### Phase 2: Existing Components
Gradual refactoring of existing code during feature work:
- Extract domain logic into pure functions
- Create port interfaces for external dependencies
- Move framework code to adapters

### Phase 3: Verification
- Automated architecture tests (cargo-architect)
- PR checklist for hexagonal compliance
- Architecture decision records for exceptions

## Compliance Checklist

- [ ] Domain has zero external dependencies (check with `cargo tree`)
- [ ] Application depends only on domain
- [ ] Adapters implement application ports
- [ ] No business logic in adapters
- [ ] Framework code isolated in adapters
- [ ] Unit tests for domain require no mocks

## References

1. [Alistair Cockburn — Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)
2. [Clean Architecture — Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
3. [Microsoft — Implementing Hexagonal Architecture](https://docs.microsoft.com/en-us/dotnet/architecture/modern-web-apps-azure/common-web-application-architectures#hexagonal-architecture-ports-and-adapters)
4. [PhenoHandbook — Hexagonal Pattern](../../patterns/architecture/hexagonal.md)

## Notes

This ADR supersedes any previous architectural discussions. All components should reference this decision for architectural guidance.

---

*Decision Date: 2026-04-04*  
*Decision Makers: Phenotype Architecture Team*  
*Next Review: 2027-04-04*