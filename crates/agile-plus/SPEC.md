# Specification: AgilePlus

AgilePlus - The primary project management and workflow automation platform.

## Overview

Rust + TypeScript monorepo containing the core AgilePlus system including:
project management, CLI tooling, agents, MCP integrations, and infrastructure crates.

## Tech Stack

- **Language**: Rust (edition 2021), TypeScript
- **Build**: Cargo, Bun
- **Testing**: Cargo test, Bun test

## Key Components

- `agileplus/` - Core CLI application
- `agileplus-agents/` - Agent implementations
- `agileplus-mcp/` - MCP server integrations
- `crates/` - Rust workspace crates
- `libs/` - TypeScript libraries
- `pheno-cli/` - Phenotype CLI
- `docs/` - Documentation
- `kitty-specs/` - Feature specifications

## Quality Standards

- All linters must pass: `cargo clippy --workspace -- -D warnings`
- All tests must pass: `cargo test --workspace`
- Test-First Mandate: failing test before fix

## Links

- PLAN.md - Project plan
- PRD.md - Product requirements
- FUNCTIONAL_REQUIREMENTS.md - Feature requirements
