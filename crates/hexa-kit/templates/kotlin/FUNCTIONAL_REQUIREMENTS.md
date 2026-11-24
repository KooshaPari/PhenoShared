# Functional Requirements — template-lang-kotlin

**Template ID:** TEMPLATE-KOTLIN-001
**Version:** 0.2.0
**Last Updated:** 2026-04-02
**Status:** Alpha (Phase 1 & 2 Complete)

## Overview

Kotlin language layer templates for Phenotype platform projects. Provides hexagonal architecture with Ktor HTTP server scaffolding.

## Current Implementation (v0.2.0)

### FR-KOTLIN-001: Project Scaffold
- ✅ Basic build.gradle.kts configuration
- ✅ Gradle Kotlin DSL
- ✅ Kotlin 2.0.0 support
- ✅ JVM 21 target
- ✅ Multi-module workspace structure

### FR-KOTLIN-002: Hexagonal Architecture
- ✅ Domain layer (Entities, Errors, Ports)
- ✅ Inbound ports (UseCase interface)
- ✅ Outbound ports (Repository, UnitOfWork interfaces)
- ✅ Application layer (Service implementation)
- ✅ Adapters layer (HTTP, Persistence)

### FR-KOTLIN-003: HTTP Layer
- ✅ Ktor CIO server
- ✅ REST routing with type-safe handlers
- ✅ Health check endpoint
- ✅ CRUD handlers
- ✅ Error handling with domain errors

### FR-KOTLIN-004: Entity Model
- ✅ ExampleEntity with state machine
- ✅ Status transitions (PENDING → ACTIVE → ARCHIVED)
- ✅ Validation logic
- ✅ Invariant enforcement

### FR-KOTLIN-005: Persistence
- ✅ In-memory repository (reference implementation)

## Roadmap Features (Not Yet Implemented)

### FR-KOTLIN-010: Dependency Injection
- ❌ Koin DI framework
- ❌ Module configuration
- ❌ Injection patterns

### FR-KOTLIN-011: Serialization & Async
- ❌ Kotlinx Serialization plugin
- ❌ Coroutines dependency
- ❌ Flow patterns

### FR-KOTLIN-012: Testing Infrastructure
- ❌ JUnit 5 test framework
- ❌ Kotest property-based testing
- ❌ MockK mocking

### FR-KOTLIN-013: Advanced Persistence
- ❌ SQL repository (Exposed)
- ❌ Connection pooling
- ❌ Transaction management

## Template Structure

Template output (`templates/kotlin/`):
```
{project}/
├── build.gradle.kts           # Multi-module Gradle config
├── src/
│   └── main/
│       ├── kotlin/
│       │   └── com/phenotype/
│       │       ├── Main.kt              # Application entry
│       │       ├── domain/
│       │       │   ├── errors/
│       │       │   │   └── DomainErrors.kt
│       │       │   ├── model/
│       │       │   │   └── ExampleEntity.kt
│       │       │   └── ports/
│       │       │       ├── inbound/
│       │       │       │   └── UseCaseService.kt
│       │       │       └── outbound/
│       │       │           └── Repository.kt
│       │       ├── application/
│       │       │   └── ExampleService.kt
│       │       └── adapters/
│       │           ├── http/
│       │           │   └── Routing.kt
│       │           └── persistence/
│       │               └── InMemoryRepository.kt
│       └── resources/
│           └── application.yaml
└── src/
    └── test/
        └── kotlin/
            └── com/phenotype/          # Test files
```

## Dependencies (v0.2.0)

```kotlin
// HTTP Server
io.ktor:ktor-server-cio:2.3.7

// Domain
org.jetbrains.kotlin:kotlin-stdlib
```

## Implemented Templates

| Template | Status | Description |
|----------|--------|-------------|
| phenotype-kotlin-api | ✅ v0.2.0 | HTTP service with hexagonal architecture |
| phenotype-kotlin-cli | ❌ | CLI application template |
| phenotype-kotlin-lib | ❌ | Library template |

## Next Steps (v0.3.0)

1. **P0**: Add Koin dependency injection
2. **P0**: Add Kotlinx Serialization
3. **P0**: Add Coroutines support
4. **P1**: Add JUnit 5 testing
5. **P1**: Add MockK mocking
