# ADR — template-lang-kotlin

## ADR-001: Kotlin Version and JVM Target
**Status:** Accepted
**Context:** Kotlin and JVM compatibility are central decisions.
**Decision:** Target Kotlin 1.9+ with JVM 17 as minimum. Generated projects support JVM 17, 21.
**Rationale:** JVM 17 is the current LTS; 21 offers virtual threads (Project Loom).

## ADR-002: Build System
**Status:** Accepted
**Context:** Gradle and Maven both support Kotlin.
**Decision:** Use Gradle with Kotlin DSL (build.gradle.kts). Kotlin Multiplatform for cross-platform modules.
**Rationale:** Kotlin DSL provides better IDE support and type-safe build scripts.

## ADR-003: Coroutines for Async
**Status:** Accepted
**Context:** Kotlin has native coroutines support.
**Decision:** Use Kotlin Coroutines with structured concurrency. Flow for streaming. No blocking calls in async contexts.
**Rationale:** Structured concurrency prevents leaks; Flow provides backpressure.

## ADR-004: Error Handling
**Status:** Accepted
**Context:** Kotlin has Result, sealed classes, and exceptions.
**Decision:** Use sealed classes for domain errors. Result<T> for recoverable errors. Exceptions only for truly exceptional cases.
**Rationale:** Explicit error types are more testable and self-documenting.

## ADR-005: Dependency Injection
**Status:** Accepted
**Context:** Multiple DI frameworks exist for Kotlin.
**Decision:** Use Koin for generated projects (lightweight, no code generation). Option to switch to Hilt for Android projects.
**Rationale:** Koin requires no annotation processing; faster builds.

## ADR-006: Serialization
**Status:** Accepted
**Context:** JSON serialization is essential for most services.
**Decision:** Use Kotlinx Serialization for JSON. Generate serializers automatically.
**Rationale:** First-class Kotlin support, excellent performance, no reflection.
