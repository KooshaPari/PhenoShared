# CLAUDE.md - Development Guidelines for kits-workspace

## Project Overview

Workspace template and tooling for Phenotype kits

## Key Files

-  - Project overview
- See project-specific directories

## Development Commands

```bash
ls -la && cat kit.yaml 2>/dev/null || echo 'No kit.yaml found'
```

## Architecture Principles

- **SOLID** - Single Responsibility, Dependency Inversion
- **DRY** - Shared abstractions
- **PoLA** - Descriptive error types

## Phenotype Org Rules

- UTF-8 encoding only in all text files
- Worktree discipline: canonical repo stays on `main`
- CI completeness: fix all CI failures before merging
- Never commit agent directories (`.claude/`, `.codex/`, `.cursor/`)
