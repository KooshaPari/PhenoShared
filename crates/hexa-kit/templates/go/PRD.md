# Product Requirements Document — template-lang-go

**Product:** Phenotype Go Language Templates
**Template Version:** 0.2.0
**Date:** 2026-04-02
**Status:** Alpha

## Purpose

Provide Go project templates that follow Phenotype platform conventions. Includes hexagonal architecture with HTTP service scaffolding.

## Current State

The template currently provides:
- Basic go.mod configuration
- golangci-lint.yml configuration
- Go 1.21+ requirement
- Complete hexagonal architecture
- Echo HTTP server with CRUD endpoints
- In-memory repository

## Target State

### Phase 1: Foundation (v0.1.0) ✅
- [x] Basic go.mod scaffold
- [x] golangci-lint configuration

### Phase 2: HTTP Services (v0.2.0) ✅
- [x] phenotype-go-api template
- [x] Echo framework integration
- [x] Middleware patterns (Logger, Recover, CORS)
- [x] Error handling with domain errors
- [x] CRUD handlers
- [x] Health check endpoint

### Phase 3: Architecture (v0.2.0) ✅
- [x] Hexagonal architecture
- [x] Repository interfaces
- [x] Service layer
- [x] Command handler pattern

### Phase 4: Persistence (v0.3.0) 📋
- [ ] SQL persistence adapter (GORM)
- [ ] Repository implementations
- [ ] Transaction management

### Phase 5: Testing (v0.4.0) 📋
- [ ] Testify integration
- [ ] Mock interfaces
- [ ] Integration tests

### Phase 6: Authentication (v0.5.0) 📋
- [ ] JWT middleware
- [ ] OAuth2 flows
- [ ] Session management

## User Stories

### US-GO-001: Basic Project Setup ✅
**As a** Go developer
**I want to** generate a basic Go project
**So that** I have a starting point

**Status:** Implemented (v0.1.0)

### US-GO-002: Build HTTP Services ✅
**As a** backend engineer
**I want to** generate a Go HTTP service
**So that** I can build REST APIs quickly

**Status:** Implemented (v0.2.0)

### US-GO-003: Domain-Driven Design 🚧
**As a** software architect
**I want to** use hexagonal architecture patterns
**So that** my services are maintainable and testable

**Status:** Implemented (v0.2.0)

### US-GO-004: CLI Applications 📋
**As a** DevOps engineer
**I want to** generate a Go CLI application
**So that** I can build command-line tools

**Status:** Roadmap (v0.3.0)

### US-GO-005: gRPC Services 📋
**As a** backend engineer
**I want to** generate a gRPC service
**So that** I can build high-performance APIs

**Status:** Roadmap (v0.4.0)

## Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Project generation | < 30 seconds | ✅ |
| golangci-lint valid | 100% | ✅ |
| Template completeness | 100% | ⏳ 60% |
| HTTP endpoints | 6 | ✅ 6 |
| Architecture layers | 4 | ✅ 4 |

## Constraints

- Go 1.21+ required
- go modules for dependencies
- golangci-lint required
- Echo framework for HTTP (not chi - easier setup)
