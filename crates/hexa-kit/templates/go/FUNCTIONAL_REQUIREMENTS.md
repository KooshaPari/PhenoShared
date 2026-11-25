# Functional Requirements — template-lang-go

**Template ID:** TEMPLATE-GO-001
**Version:** 0.2.0
**Last Updated:** 2026-04-02
**Status:** Alpha (Phase 1 & 2 Complete)

## Overview

Go language layer templates for Phenotype platform projects. Provides hexagonal architecture with HTTP service scaffolding.

## Current Implementation (v0.2.0)

### FR-GO-001: Project Scaffold
- ✅ Basic go.mod configuration
- ✅ golangci-lint.yml configuration
- ✅ Go 1.21+ requirement

### FR-GO-002: HTTP Layer
- ✅ net/http with Echo framework
- ✅ Middleware patterns (Logger, Recover, CORS)
- ✅ Request/Response DTOs
- ✅ Error handling with domain errors
- ✅ Health check endpoint

### FR-GO-003: Hexagonal Architecture
- ✅ Domain layer (Entities, Value Objects, Errors)
- ✅ Inbound ports (UseCase interface)
- ✅ Outbound ports (Repository, UnitOfWork interfaces)
- ✅ Application layer (Command handlers)
- ✅ Infrastructure adapters (HTTP, Persistence)
- ✅ Dependency injection

### FR-GO-004: CRUD Operations
- ✅ Create entity
- ✅ Get entity by ID
- ✅ Update entity
- ✅ Delete entity
- ✅ List all entities

### FR-GO-005: Persistence
- ✅ In-memory repository (reference implementation)

## Roadmap Features (Not Yet Implemented)

### FR-GO-010: Advanced Persistence
- ❌ SQL persistence adapter (Postgres)
- ❌ Repository implementations
- ❌ Transaction management
- ❌ Connection pooling

### FR-GO-011: Testing Structure
- ❌ Go testing package
- ❌ testify assertions
- ❌ mock interfaces
- ❌ Integration tests

### FR-GO-012: Authentication
- ❌ JWT middleware
- ❌ OAuth2 flows
- ❌ Session management

### FR-GO-013: Deployment
- ❌ Docker configuration
- ❌ Docker Compose
- ❌ Kubernetes manifests
- ❌ Deployment scripts

## Template Structure

Template output (`templates/go/`):
```
{project}/
├── cmd/
│   └── server/
│       └── main.go           # Application entry point
├── domain/
│   ├── doc.go                # Package documentation
│   ├── errors/
│   │   └── errors.go         # Domain errors
│   ├── entities/
│   │   └── example.go        # Domain entity
│   ├── ports/
│   │   ├── inbound/
│   │   │   └── usecase.go    # UseCase interface
│   │   └── outbound/
│   │       └── repository.go # Repository interface
│   └── valueobjects/
│       └── vo.go              # Value objects
├── application/
│   └── commands/
│       └── handler.go         # Service implementation
├── infrastructure/
│   ├── adapters/
│   │   └── persistence/
│   │       └── memory.go     # In-memory repository
│   └── http/
│       ├── handlers.go       # HTTP handlers
│       └── server.go         # Echo server setup
├── go.mod                     # Module config
└── Makefile                   # Build commands
```

## Dependencies (v0.2.0)

```go
github.com/labstack/echo/v4 v4.11.0  // HTTP framework
```

## Implemented Templates

| Template | Status | Description |
|----------|--------|-------------|
| phenotype-go-api | ✅ v0.2.0 | HTTP service with hexagonal architecture |
| phenotype-go-cli | ❌ | CLI application template |
| phenotype-go-grpc | ❌ | gRPC service template |

## Next Steps (v0.3.0)

1. **P0**: Add SQL persistence adapter (GORM)
2. **P0**: Add authentication middleware (JWT)
3. **P1**: Add gRPC service template
4. **P1**: Add CLI application template
5. **P2**: Add Docker deployment configuration
