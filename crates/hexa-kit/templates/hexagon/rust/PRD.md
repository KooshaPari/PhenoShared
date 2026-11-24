# PRD: Phenotype Kits Workspace

## Overview
Phenotype Kits is a curated collection of reusable Rust libraries implementing hexagonal architecture primitives. It provides foundational kit libraries (clikit, agentkit, evalkit, taskkit, configkit, authkit, cachekit) for building consistent, composable Rust applications across the Phenotype ecosystem.

## Problem Statement
Rust teams building Phenotype services repeatedly implement CLI frameworks, agent scaffolding, configuration management, and auth patterns from scratch. This creates divergent implementations, maintenance overhead, and inconsistent APIs.

## Goals
1. Single, versioned source of truth for shared Rust primitives
2. Hexagonal architecture enforcement across all kit libraries
3. Composable kit design — only import what is needed
4. Consistent API surface and error handling patterns

## Epics

### E1: Core Kit Libraries
- E1.1: clikit — Universal CLI framework (clap-based, with skill dispatch)
- E1.2: agentkit — Agent lifecycle management (spawn, message, terminate)
- E1.3: evalkit — Evaluation harness (assertions, scoring, comparison)
- E1.4: taskkit — Task executor (parallel, sequential, retry, timeout)
- E1.5: configkit — Configuration management (layered, env, file, defaults)
- E1.6: authkit — Auth/AuthZ framework (JWT, RBAC, policy evaluation)
- E1.7: cachekit — Caching abstraction (in-memory, Redis, TTL, LRU)

### E2: Workspace Infrastructure
- E2.1: Unified Cargo workspace with shared dev-dependencies
- E2.2: CI/CD for all crates (build, test, lint, coverage)
- E2.3: Crate versioning and release automation

### E3: Hexagonal Architecture Enforcement
- E3.1: Domain/Application/Ports/Adapters layer boundaries per kit
- E3.2: Trait-based port definitions (no leaking concrete adapters)
- E3.3: Architecture linting via cargo-deny and import rules

## Acceptance Criteria
- All kits compile with `cargo build --workspace`
- All kits have ≥80% test coverage
- No direct cross-kit implementation dependencies (only trait ports)
- Each kit has a working example in `examples/`
- Clippy clean with `deny(warnings)`

