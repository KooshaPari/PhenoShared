# CLAUDE.md - Development Guidelines for go-hex

## Project Overview

go-hex is a lightweight, dependency-free hexagonal architecture kit for Go applications. It provides structural patterns for building applications with Ports & Adapters while respecting Go's idioms.

## Key Files

- `README.md` - Project overview and quick start
- `domain/` - Pure business logic (no external dependencies)
- `ports/` - Interface definitions for driving and driven ports
- `application/` - Use cases and DTOs
- `infrastructure/` - Concrete implementations (REST, gRPC, CLI adapters)

## Development Commands

```bash
go test ./...        # Run all tests
go test -cover ./... # With coverage
go vet ./...         # Lint
go fmt ./...         # Format
```

## Architecture Principles

- **Hexagonal Architecture** - Ports & Adapters isolation
- **SOLID** - Single Responsibility, Dependency Inversion via ports
- **DRY** - Shared port interfaces
- **PoLA** - Descriptive error types

## Phenotype Org Rules

- UTF-8 encoding only in all text files
- Worktree discipline: canonical repo stays on `main`
- CI completeness: fix all CI failures before merging
- Never commit agent directories (`.claude/`, `.codex/`, `.cursor/`)
- Domain layer must have ZERO external dependencies
