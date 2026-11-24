# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-04-02

### Added
- **Hexagonal Architecture** - Complete domain-driven design structure
- **Domain Layer** - Entity, Value Objects, Domain Errors, Ports
- **Inbound Ports** - UseCase interface with Create/Get/Update/Delete/List
- **Outbound Ports** - Repository and UnitOfWork interfaces
- **Echo HTTP Server** - REST API with chi-style routing
- **Health Check Endpoint** - GET /health
- **CRUD Handlers** - Full REST API for entities
- **Error Handling** - Domain error propagation to HTTP responses
- **Middleware** - Logger, Recover, CORS
- **In-Memory Repository** - Reference implementation
- **Command Handler Pattern** - Clean application service structure
- **Module Path** - Placeholder `{{ module_path }}` for easy renaming

### Implemented Templates
- `templates/go/` - Complete Go service template

## [0.1.0] - 2026-04-02

### Added
- Basic go.mod configuration
- Go 1.21+ requirement
- golangci-lint.yml configuration
- Interface contracts in `contracts/`
- Automation scripts in `scripts/`
- Documentation structure in `docs/`

### Not Yet Implemented (Roadmap)
- SQL persistence adapter
- Authentication middleware
- gRPC service template
- CLI application template
- Docker deployment configuration
