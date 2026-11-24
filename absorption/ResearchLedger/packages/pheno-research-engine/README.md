<!-- AI-DD-META:START -->
<!-- This repository is planned, maintained, and managed by AI Agents only. -->
<!-- Slop issues are expected and intentionally present as part of an HITL-less -->
<!-- /minimized AI-DD metaproject of learning, refining, and building brute-force -->
<!-- training for both agents and the human operator. -->
![Downloads](https://img.shields.io/github/downloads/KooshaPari/phenoResearchEngine/total?style=flat-square&label=downloads&color=blue) [![AI slop inside](https://sladge.net/badge.svg)](https://sladge.net)
![GitHub release](https://img.shields.io/github/v/release/KooshaPari/phenoResearchEngine?style=flat-square&label=release)
![License](https://img.shields.io/github/license/KooshaPari/phenoResearchEngine?style=flat-square)
![AI-Slop](https://img.shields.io/badge/AI--DD-Slop%20Expected-orange?style=flat-square)
![AI-Only-Maintained](https://img.shields.io/badge/Planned%20%26%20Maintained%20by-AI%20Agents%20Only-red?style=flat-square)
![HITL-less](https://img.shields.io/badge/HITL--less%20AI--DD-metaproject-yellow?style=flat-square)

> ⚠️ **AI-Agent-Only Repository**
>
> This repo is **planned, maintained, and managed exclusively by AI Agents**.
> Slop issues, rough edges, and AI artifacts are **expected and intentionally
> present** as part of an **HITL-less / minimized AI-DD** metaproject focused
> on learning, refining, and brute-force training both the agents and the
> human operator. Bug reports and contributions are still welcome, but please
> expect AI-generated code, comments, and documentation throughout.
<!-- AI-DD-META:END -->
# phenotype-research-engine

Automated research workflow orchestration and evidence-driven investigation engine for agent-driven research pipelines. Enables composable research tasks, source-provenance tracking, and DAG-based orchestration for multi-step investigation workflows.

> **Status**: **DEPRECATED** (2026-06-20). See [DEPRECATED.md](./DEPRECATED.md) for migration path. Prior state: Archived (2026-03-25).

## Overview

**phenotype-research-engine** was the original research orchestration system for Phenotype agents. It provided evidence-driven research workflows with composable tasks, automatic provenance tracking, and integration with phenotype-task-engine for scheduling.

**Archived**: Functionality has been consolidated into the main Phenotype monorepo structure under `packages/phenotype-research/`. New research workflows should target that location.

## Technology Stack

- **Languages**: Python (primary orchestration), TypeScript (secondary)
- **Core Framework**: DAG task runner, pytest for test orchestration
- **Dependencies**: Python 3.11+, pytest, pyproject.toml configuration
- **Integration**: phenotype-task-engine for distributed task scheduling

## Key Features (Legacy)

- **Evidence-Driven Research**: All outputs include source provenance and citation tracking
- **Composable Tasks**: Research steps modeled as DAG nodes with explicit dependencies
- **Automatic Scheduling**: Integration with phenotype-task-engine for concurrent execution
- **Structured Outputs**: JSON-serialized research results with metadata
- **Test-Driven Design**: pytest-based validation for all research modules

## Archive Migration Guide

### Why Archived

The original research-engine design was consolidated into the main phenotype monorepo for tighter integration with:
- Agent runtime and execution environments
- Unified observability pipeline
- Shared governance and standards
- Simplified dependency management

### Migration Path

```bash
# Old location (deprecated)
phenoResearchEngine/src/ → packages/phenotype-research/

# Update imports
from phenotype_research_engine import ... 
  ↓ (becomes)
from phenotype.research import ...
```

### Legacy Users

If you depend on phenotype-research-engine:

1. Review `ARCHIVED.md` for detailed migration steps
2. Update package imports to new location
3. Check `packages/phenotype-research/docs/migration.md` for breaking changes
4. Run test suite against new location
5. Reference: phenotype-research legacy compatibility layer available in bridge package

## Project Structure (Archive)

```
phenoResearchEngine/           # ARCHIVED
├── src/
│   ├── orchestration/         # DAG-based task orchestration
│   ├── evidence/              # Provenance tracking and citation
│   ├── tasks/                 # Task definitions (legacy)
│   └── integration/           # Task engine bridges
├── tests/
│   ├── test_evidence.py       # Provenance tests
│   ├── test_orchestration.py  # DAG execution tests
│   └── fixtures/              # Test data
├── docs/
│   └── migration.md           # Archive migration guide
├── ARCHIVED.md                # Full archive metadata
├── CLAUDE.md                  # Governance (legacy)
└── pyproject.toml
```

## Related Phenotype Projects

- **packages/phenotype-research**: Active research engine (successor)
- **phenotype-task-engine**: Task scheduling and execution (integrated)
- **Tracera**: Research telemetry and observability
- **AgilePlus**: Work tracking for research projects

## Documentation

This repository includes the following cross-cutting documents:

- [`AGENTS.md`](AGENTS.md) — operating instructions for AI agents and human contributors
- [`SPEC.md`](SPEC.md) — formal specification of behavior and contracts
- [`docs/`](docs/) — design notes, ADRs, and supporting documentation (see [`docs/index.md`](docs/index.md))

