# Product Requirements Document — template-lang-kotlin

**Product:** Phenotype Kotlin Language Templates
**Template Version:** 0.1.0
**Date:** 2026-04-02
**Status:** Foundation Only

## Purpose

Provide Kotlin project templates that follow Phenotype platform conventions. Currently provides basic scaffolding; hexagonal architecture, DI, and testing templates are on the roadmap.

## Current State

The template currently provides:
- Basic build.gradle.kts configuration
- Gradle Kotlin DSL setup
- Basic project structure

## Target State

### Phase 1: Foundation (Current - v0.1.0) ✅
- [x] Basic project scaffolding
- [x] Gradle Kotlin DSL configuration

### Phase 2: Hexagonal Architecture (v0.2.0) 🚧
- [ ] hexagonal-kotlin template
- [ ] Domain/application/adapters/ports layers
- [ ] Repository interfaces
- [ ] Service interfaces

### Phase 3: DI & Serialization (v0.3.0) 📋
- [ ] Koin dependency injection
- [ ] Kotlinx Serialization
- [ ] Coroutines and Flow

### Phase 4: Testing (v0.4.0) 📋
- [ ] JUnit 5 setup
- [ ] Kotest integration
- [ ] MockK mocking framework

## Problem Statement

Starting a new Kotlin project requires:
- ✅ Basic project setup (covered)
- ⏳ Gradle build configuration (basic coverage)
- ⏳ Hexagonal architecture structure (pending)
- ⏳ Dependency injection setup (pending)
- ⏳ Testing infrastructure (pending)

## User Stories

### US-KOTLIN-001: Basic Project Setup ✅
**As a** Kotlin developer
**I want to** generate a basic Kotlin project
**So that** I have a starting point

**Status:** Implemented (v0.1.0)

### US-KOTLIN-002: Follow Hexagonal Architecture 🚧
**As a** backend developer
**I want to** implement hexagonal architecture
**So that** my code is testable and maintainable

**Status:** Roadmap (v0.2.0)

### US-KOTLIN-003: Use Phenotype Platform 🚧
**As a** platform engineer
**I want to** integrate with Phenotype platform
**So that** my service works with the ecosystem

**Status:** Roadmap (v0.3.0+)

## Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Project generation | < 30 seconds | ✅ |
| Build success | 100% | ✅ |
| Template completeness | 100% | ⏳ Pending |

## Constraints

- Kotlin 1.9+ target
- Gradle Kotlin DSL required
- JVM 17 minimum (target)
