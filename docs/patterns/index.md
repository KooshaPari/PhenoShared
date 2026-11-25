---
# Pattern index - organized by domain
layout: home
hero:
  name: Design Patterns
  text: by Domain
  tagline: Organized collection of battle-tested patterns for building robust systems
  actions:
    - theme: brand
      text: Architecture Patterns
      link: /patterns/architecture/
    - theme: alt
      text: Async Patterns
      link: /patterns/async/
    - theme: alt
      text: Auth Patterns
      link: /patterns/auth/

features:
  - icon: 🏗️
    title: Architecture
    details: Hexagonal, CQRS, Event-Driven, and Saga patterns for system design
    link: /patterns/architecture/
  
  - icon: ⚡
    title: Async & Messaging
    details: Outbox, CQRS, Saga, and Event-Driven patterns for distributed systems
    link: /patterns/async/
  
  - icon: 🔐
    title: Authentication
    details: OAuth 2.0 with PKCE, JWT patterns for secure applications
    link: /patterns/auth/
  
  - icon: 💾
    title: Caching
    details: Cache-Aside, Write-Through, and cache invalidation strategies
    link: /patterns/caching/
  
  - icon: 📊
    title: Observability
    details: Tracing, metrics, and logging patterns for production systems
    link: /patterns/observability/
  
  - icon: 🧪
    title: Testing
    details: Unit testing, integration testing, and contract testing patterns
    link: /patterns/testing/
---

## Pattern Categories

### Architecture Patterns
Design patterns for system structure and organization.

- [Hexagonal Architecture](./architecture/hexagonal.md) - Ports and adapters pattern
- [CQRS](./architecture/cqrs.md) - Command Query Responsibility Segregation
- [Event-Driven Architecture](./architecture/event-driven.md) - Event-based system design
- [Saga Pattern](./async/saga.md) - Distributed transaction management

### Async & Messaging Patterns
Patterns for asynchronous and distributed systems.

- [Outbox Pattern](./async/outbox.md) - Reliable message delivery
- [Saga Pattern](./async/saga.md) - Long-running transaction coordination
- [CQRS](./architecture/cqrs.md) - Separating read and write models

### Authentication & Security Patterns
Patterns for secure authentication and authorization.

- [OAuth 2.0 with PKCE](./auth/oauth-pkce.md) - Modern OAuth with PKCE

### Caching Patterns
Patterns for effective caching strategies.

- [Cache-Aside](./caching/cache-aside.md) - Lazy loading pattern

## Using This Handbook

Each pattern includes:

1. **Overview** - What problem it solves and when to use it
2. **Visual Diagrams** - ASCII art showing the pattern flow
3. **Implementation** - Code examples in Rust, Go, Python, TypeScript
4. **Anti-Patterns** - Common mistakes to avoid
5. **Related Patterns** - Links to complementary patterns

## Contributing

Patterns should follow the [kitty-spec format](../../kitty-specs/) from PhenoSpecs.

---

*Part of the [Phenotype Registry System](https://github.com/KooshaPari/phenotype-registry)*
