# TsHex Feature Comparison Matrix

## Overview

TsHex is a lightweight hexagonal architecture kit for TypeScript that provides structural patterns without forcing specific frameworks or dependencies on your domain.

## Feature Comparison

| Feature | ts-hex | nestjs | inversify | angular |
|---------|--------|--------|----------|---------|
| **Architecture** |
| Hexagonal/Ports&Adapters | ✅ | ⚠️ | ⚠️ | ❌ |
| Clean Architecture layers | ✅ | ⚠️ | ❌ | ❌ |
| Dependency Injection | ✅ | ✅ | ✅ | ✅ |
| **Domain Layer** |
| Zero external deps | ✅ | ❌ | ❌ | ❌ |
| Entity base types | ✅ | ⚠️ | ❌ | ⚠️ |
| Value object helpers | ✅ | ⚠️ | ❌ | ❌ |
| Aggregate root support | ✅ | ⚠️ | ❌ | ❌ |
| **Ports (Interfaces)** |
| Generic Repository | ✅ | ⚠️ | ❌ | ❌ |
| UnitOfWork interface | ✅ | ❌ | ❌ | ❌ |
| EventStore interface | ✅ | ⚠️ | ❌ | ❌ |
| MessageBus interface | ✅ | ✅ | ❌ | ❌ |
| **Quality** |
| TypeScript-first | ✅ | ✅ | ✅ | ✅ |
| Tree-shakeable | ✅ | ❌ | ⚠️ | ❌ |
| Framework-agnostic | ✅ | ❌ | ⚠️ | ❌ |

## When to Use

### Use ts-hex when:

- ✅ You want strict hexagonal architecture
- ✅ You need zero dependencies in domain layer
- ✅ You want generic, reusable port interfaces
- ✅ You prefer explicit architecture over convention
- ✅ You need event sourcing or CQRS support
- ✅ You want to avoid heavy frameworks like NestJS

### Consider alternatives when:

- ⚠️ You need a full-stack framework → NestJS
- ⚠️ You only need DI → inversify
- ⚠️ You're building Angular apps → Use Angular DI

## Unique Value Proposition

1. **Domain-first**: Domain layer has ZERO external dependencies
2. **TypeScript-native**: Leverages TypeScript's type system
3. **Framework-agnostic**: No assumptions about web frameworks, ORMs, etc.
4. **Minimal footprint**: Small, focused package with no bloat
5. **Explicit over implicit**: Clear separation makes architecture visible

## Alternatives Reference

| Library | GitHub | Focus |
|---------|--------|-------|
| ts-hex | [phenotype-dev/ts-hex](https://github.com/phenotype-dev/ts-hex) | Hexagonal Architecture Kit |
| nest | [nestjs/nest](https://github.com/nestjs/nest) | Progressive Node.js framework |
| inversify | [inversify/InversifyJS](https://github.com/inversify/InversifyJS) | IoC container |
