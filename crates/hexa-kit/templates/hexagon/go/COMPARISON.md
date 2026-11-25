# Go-Hex Feature Comparison Matrix

## Overview

Go-Hex is a lightweight hexagonal architecture kit for Go that provides structural patterns without forcing specific frameworks or dependencies on your domain.

## Feature Comparison

| Feature | go-hex | go-clean | go-kit | go-tddd | buffalo |
|---------|--------|----------|--------|---------|---------|
| **Architecture** |
| Hexagonal/Ports&Adapters | ✅ | ⚠️ | ⚠️ | ⚠️ | ❌ |
| Clean Architecture layers | ✅ | ✅ | ⚠️ | ⚠️ | ⚠️ |
| Onion Architecture | ⚠️ | ⚠️ | ❌ | ⚠️ | ❌ |
| **Domain Layer** |
| Zero external deps | ✅ | ❌ | ❌ | ❌ | ❌ |
| Entity base types | ✅ | ⚠️ | ❌ | ⚠️ | ⚠️ |
| Value object helpers | ✅ | ⚠️ | ❌ | ✅ | ❌ |
| Aggregate root support | ✅ | ⚠️ | ❌ | ⚠️ | ❌ |
| **Ports (Interfaces)** |
| Generic Repository[T] | ✅ | ❌ | ❌ | ❌ | ❌ |
| UnitOfWork interface | ✅ | ❌ | ✅ | ❌ | ❌ |
| EventStore interface | ✅ | ❌ | ✅ | ❌ | ❌ |
| MessageBus interface | ✅ | ❌ | ✅ | ❌ | ❌ |
| **Application Layer** |
| UseCase[T,O] interface | ✅ | ⚠️ | ⚠️ | ✅ | ⚠️ |
| Command/Query separation | ✅ | ❌ | ⚠️ | ✅ | ❌ |
| DTO helpers | ✅ | ⚠️ | ✅ | ✅ | ⚠️ |
| **Quality** |
| Type-safe generics | ✅ | ⚠️ | ⚠️ | ✅ | ❌ |
| Context propagation | ✅ | ✅ | ✅ | ✅ | ✅ |
| Error wrapping | ✅ | ✅ | ✅ | ✅ | ✅ |

## When to Use

### Use go-hex when:

- ✅ You want strict hexagonal architecture
- ✅ You need zero dependencies in domain layer
- ✅ You want generic, reusable port interfaces
- ✅ You prefer explicit architecture over convention
- ✅ You need event sourcing or CQRS support

### Consider alternatives when:

- ⚠️ You prefer convention over configuration → go-clean
- ⚠️ You need microservices with observability → go-kit
- ⚠️ You're building a monolith with Rails-like DX → buffalo
- ❌ You want simple CRUD apps → Use direct database access

## Unique Value Proposition

1. **Domain-first**: Domain layer has ZERO external dependencies
2. **Generics-native**: Leverages Go 1.18+ generics for type-safe ports
3. **Framework-agnostic**: No assumptions about web frameworks, ORMs, etc.
4. **Minimal footprint**: Small, focused package with no bloat
5. **Explicit over implicit**: Clear separation makes architecture visible

## Alternatives Reference

| Library | GitHub | Focus |
|---------|--------|-------|
| go-hex | [phenotype-dev/go-hex](https://github.com/phenotype-dev/go-hex) | Hexagonal Architecture Kit |
| go-clean | [livepros/go-clean](https://github.com/qiangxue/go-clean) | Clean Architecture template |
| go-kit | [go-kit/kit](https://github.com/go-kit/kit) | Microservices toolkit |
| go-tddd | [checkr/go-flipr](https://github.com/checkr/flagr) | TDD-ready structure |
