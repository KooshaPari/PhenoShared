# CLAUDE.md - Development Guidelines for ts-hex

## Project Overview

ts-hex is a lightweight, dependency-free hexagonal architecture kit for TypeScript/JavaScript applications. It provides structural patterns for building applications with Ports & Adapters while respecting TypeScript's types.

## Key Files

- `README.md` - Project overview and quick start
- `src/domain/` - Pure business logic (no external dependencies)
- `src/ports/` - Interface definitions for driving and driven ports
- `src/application/` - Use cases and DTOs
- `src/adapters/` - Concrete implementations

## Development Commands

```bash
npm test       # Run all tests
npm run build  # Build
npm run lint   # Lint
npm run typecheck # Type check
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
