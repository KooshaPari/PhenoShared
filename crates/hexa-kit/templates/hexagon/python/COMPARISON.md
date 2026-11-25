# PyHex Feature Comparison Matrix

## Overview

PyHex is a lightweight hexagonal architecture kit for Python that provides structural patterns without forcing specific frameworks or dependencies on your domain.

## Feature Comparison

| Feature | pyhex | fastapi | pyramid | nameko |
|---------|-------|---------|---------|--------|
| **Architecture** |
| Hexagonal/Ports&Adapters | ✅ | ❌ | ⚠️ | ❌ |
| Clean Architecture layers | ✅ | ⚠️ | ⚠️ | ❌ |
| Onion Architecture | ⚠️ | ❌ | ❌ | ❌ |
| **Domain Layer** |
| Zero external deps | ✅ | ❌ | ❌ | ❌ |
| Entity base types | ✅ | ❌ | ⚠️ | ❌ |
| Value object helpers | ✅ | ❌ | ⚠️ | ❌ |
| Aggregate root support | ✅ | ❌ | ❌ | ❌ |
| **Ports (Interfaces)** |
| Generic Repository[T] | ✅ | ❌ | ❌ | ❌ |
| UnitOfWork interface | ✅ | ❌ | ❌ | ❌ |
| EventStore interface | ✅ | ❌ | ❌ | ❌ |
| MessageBus interface | ✅ | ❌ | ❌ | ✅ |
| **Application Layer** |
| UseCase[T,O] interface | ✅ | ⚠️ | ❌ | ✅ |
| Command/Query separation | ✅ | ❌ | ❌ | ❌ |
| **Quality** |
| Type hints | ✅ | ✅ | ⚠️ | ⚠️ |
| Async support | ✅ | ✅ | ⚠️ | ✅ |
| **Testing** |
| Testable without framework | ✅ | ⚠️ | ⚠️ | ⚠️ |

## When to Use

### Use pyhex when:

- ✅ You want strict hexagonal architecture
- ✅ You need zero dependencies in domain layer
- ✅ You want generic, reusable port interfaces
- ✅ You prefer explicit architecture over convention
- ✅ You need event sourcing or CQRS support

### Consider alternatives when:

- ⚠️ You need a full web framework → fastapi
- ⚠️ You prefer SQLAlchemy integration → pyramid
- ⚠️ You're building microservices → nameko

## Unique Value Proposition

1. **Domain-first**: Domain layer has ZERO external dependencies
2. **Pythonic**: Follows Python idioms and conventions
3. **Framework-agnostic**: No assumptions about web frameworks, ORMs, etc.
4. **Minimal footprint**: Small, focused package with no bloat
5. **Explicit over implicit**: Clear separation makes architecture visible

## Alternatives Reference

| Library | GitHub | Focus |
|---------|--------|-------|
| pyhex | [phenotype-dev/pyhex](https://github.com/phenotype-dev/pyhex) | Hexagonal Architecture Kit |
| fastapi | [tiangolo/fastapi](https://github.com/tiangolo/fastapi) | Web API framework |
| pyramid | [Pylons/pyramid](https://github.com/Pylons/pyramid) | General web framework |
| nameko | [nameko/nameko](https://github.com/nameko/nameko) | Microservices framework |
