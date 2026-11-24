# CLAUDE.md - Development Guidelines for pyhex

## Project Overview

pyhex is a lightweight, dependency-free hexagonal architecture kit for Python applications. It provides structural patterns for building applications with Ports & Adapters while respecting Python's idioms.

## Key Files

- `README.md` - Project overview and quick start
- `pyhex/domain/` - Pure business logic (no external dependencies)
- `pyhex/ports/` - Interface definitions for driving and driven ports
- `pyhex/application/` - Use cases and DTOs
- `pyhex/adapters/` - Concrete implementations

## Development Commands

```bash
pytest              # Run all tests
pytest --cov=pyhex  # With coverage
mypy pyhex          # Type check
black --check pyhex # Format check
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
