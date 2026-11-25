# Phenotype Ecosystem Index

> Master index of all Phenotype projects in the repos shelf

## Overview

This document provides a comprehensive index of all 29 `phenotype-*` repositories maintained in the Phenotype ecosystem.

## Repository Categories

### Core Infrastructure

| Repository | Purpose | Language | Status |
|------------|---------|----------|--------|
| [phenotype-infrakit](./phenotype-infrakit) | Shared Rust infrastructure crates | Rust | Active |
| [phenotype-go-kit](./phenotype-go-kit) | Go infrastructure toolkit | Go | Active |
| [phenotype-governance](./phenotype-governance) | Shared governance configs | Configs | Active |

### Security & Monitoring

| Repository | Purpose | Language | Status |
|------------|---------|----------|--------|
| [phenotype-cipher](./phenotype-cipher) | Cryptographic operations | Rust | Active |
| [phenotype-sentinel](./phenotype-sentinel) | Security monitoring | Rust | Active |
| [phenotype-dep-guard](./phenotype-dep-guard) | Dependency scanning | Rust | Active |
| [phenotype-router-monitor](./phenotype-router-monitor) | HTTP router monitoring | Rust | Active |

### Development Tools

| Repository | Purpose | Language | Status |
|------------|---------|----------|--------|
| [phenotype-forge](./phenotype-forge) | Code generation and templating | Rust | Active |
| [phenotype-cli-extensions](./phenotype-cli-extensions) | CLI tooling extensions | Rust | Active |
| [phenotype-gauge](./phenotype-gauge) | Benchmarking and xDD testing | Rust | Active |
| [phenotype-patch](./phenotype-patch) | Patch management | Rust | Active |
| [phenotype-skills](./phenotype-skills) | Agent skill definitions | Markdown | Active |

### Documentation & Research

| Repository | Purpose | Language | Status |
|------------|---------|----------|--------|
| [phenotype-docs-engine](./phenotype-docs-engine) | Documentation generation | Rust | Active |
| [phenotype-research-engine](./phenotype-research-engine) | Research data processing | Rust | Active |
| [phenotype-xdd](./phenotype-xdd) | xDD methodology implementation | TypeScript | Active |
| [phenotype-xdd-lib](./phenotype-xdd-lib) | xDD shared library | TypeScript | Active |

### Configuration & Types

| Repository | Purpose | Language | Status |
|------------|---------|----------|--------|
| [phenotype-config-ts](./phenotype-config-ts) | TypeScript configuration | TypeScript | Active |
| [phenotype-types](./phenotype-types) | Shared type definitions | TypeScript | Active |
| [phenotype-auth-ts](./phenotype-auth-ts) | TypeScript authentication | TypeScript | Active |

### Services & Runtime

| Repository | Purpose | Language | Status |
|------------|---------|----------|--------|
| [phenotype-agent-core](./phenotype-agent-core) | Agent runtime core | Rust | Active |
| [phenotype-task-engine](./phenotype-task-engine) | Task execution engine | Rust | Active |
| [phenotype-middleware-py](./phenotype-middleware-py) | Python middleware | Python | Active |
| [phenotype-hub](./phenotype-hub) | Web dashboard (Next.js) | TypeScript | Active |
| [phenotype-design](./phenotype-design) | Design system | Various | Active |
| [phenotype-vessel](./phenotype-vessel) | Container/runtime tools | Rust | Active |

### Specialized Tools

| Repository | Purpose | Language | Status |
|------------|---------|----------|--------|
| [phenotype-evaluation](./phenotype-evaluation) | Code evaluation tools | Rust | Active |
| [phenotype-nexus](./phenotype-nexus) | Service mesh/nexus | Rust | Active |
| [phenotype-shared](./phenotype-shared) | Shared utilities | Rust | Active |
| [phenotype-logging-zig](./phenotype-logging-zig) | Zig logging library | Zig | Archived |

## Documentation Standards

All repositories follow the standard 8-file documentation template:

1. **README.md** - Project overview and quick start
2. **SPEC.md** - Technical specification
3. **PRD.md** - Product requirements document
4. **CHANGELOG.md** - Version history
5. **AGENTS.md** - Agent development guidelines
6. **CLAUDE.md** - Claude-specific guidelines
7. **CONTRIBUTING.md** - Contribution guidelines
8. **ARCHIVED.md** - Archive status

## Statistics

- **Total Repositories**: 29
- **Languages**: Rust (14), TypeScript (8), Go (1), Python (1), Zig (1), Configs (4)
- **Status**: 28 Active, 1 Archived
- **Documentation**: 100% complete (all 8 standard files)

## Quick Navigation

### By Language
- **Rust**: infrakit, cipher, sentinel, dep-guard, router-monitor, forge, cli-extensions, gauge, patch, agent-core, task-engine, vessel, evaluation, nexus, shared
- **TypeScript**: config-ts, types, auth-ts, xdd, xdd-lib, hub
- **Go**: go-kit
- **Python**: middleware-py
- **Zig**: logging-zig (archived)

### By Category
- **Infrastructure**: infrakit, go-kit, governance
- **Security**: cipher, sentinel, dep-guard, router-monitor
- **Tools**: forge, cli-extensions, gauge, patch
- **Docs**: docs-engine, research-engine, xdd, xdd-lib
- **Services**: agent-core, task-engine, hub, vessel
- **Config**: config-ts, types, auth-ts

## License

All Phenotype repositories are licensed under MIT unless otherwise specified.
