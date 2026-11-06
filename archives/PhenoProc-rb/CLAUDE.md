# PhenoProc — Claude Code Instructions

## Project Overview
- **Name**: PhenoProc
- **Description**: Phenotype processor workspace for AI agent infrastructure and tools
- **Location**: `/Users/kooshapari/CodeProjects/Phenotype/repos/PhenoProc`
- **Language Stack**: Go, Python
- **Status**: Active development

## AgilePlus Mandate
All work MUST be tracked in AgilePlus:
- Reference: `/Users/kooshapari/CodeProjects/Phenotype/repos/AgilePlus`
- CLI: `cd /Users/kooshapari/CodeProjects/Phenotype/repos/AgilePlus && agileplus <command>`
- No code without corresponding AgilePlus spec.

## Stack & Commands
```bash
# Build
go build ./...

# Test
go test ./...

# Lint
golangci-lint run
```

## Quality Checks
From this repository root:
- `go build ./...` — compile check
- `go test ./...` — unit tests

## Git & Branch Discipline
- Feature branches: `worktrees/<topic>/`
- Canonical: `main`
- Never commit directly to `main`

## References
- Parent workspace: `/Users/kooshapari/CodeProjects/Phenotype/repos/CLAUDE.md`
- AgilePlus: `/Users/kooshapari/CodeProjects/Phenotype/repos/AgilePlus`
