# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-04-02

### Added
- **Hexagonal Architecture** - Complete domain-driven design structure
- **Domain Layer** - Entity, Domain Errors, Ports
- **Inbound Ports** - UseCase interface with Create/Get/Update/Delete/List
- **Outbound Ports** - Repository and UnitOfWork interfaces
- **Ktor HTTP Server** - REST API with routing
- **Health Check Endpoint** - GET /health
- **CRUD Handlers** - Full REST API for entities
- **Error Handling** - Domain error propagation to HTTP responses
- **In-Memory Repository** - Reference implementation
- **Application Service** - Clean application service structure
- **State Machine** - Entity status transitions (PENDING → ACTIVE → ARCHIVED)

### Implemented Templates
- `templates/kotlin/` - Complete Kotlin service template

## [0.1.0] - 2026-04-02

### Added
- Basic build.gradle.kts configuration
- Gradle Kotlin DSL setup
- Interface contracts in `contracts/`
- Automation scripts in `scripts/`
- Documentation structure in `docs/`

### Not Yet Implemented (Roadmap)
- Koin dependency injection
- Kotlinx Serialization
- Coroutines/Flow support
- JUnit 5 testing
- Kotest property-based testing
- MockK mocking
- SQL repository implementation
