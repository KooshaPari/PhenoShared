# Contributing to phenotype-forge

Thank you for your interest in contributing to phenotype-forge.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/Phenotype-Enterprise/phenotype-forge
cd phenotype-forge

# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Build
cargo build

# Test
cargo test --all-features

# Lint
cargo clippy
cargo fmt --check
```

## What This Is

phenotype-forge is a **standalone CLI tool** for task running and build orchestration. The `phenotype-` prefix serves as branding, not a library namespace.

## Features

- **Parallel Execution**: Run tasks concurrently with automatic topological sort
- **Dependency Graph**: Automatic resolution of task dependencies
- **Hot Reload**: Watch files and restart on changes
- **Plugin System**: Extend with custom task definitions

## Task System

```rust
use forge::{task, deps};

#[task]
fn build() {
    println!("Building...");
}

#[task]
#[deps(build)]
fn test() {
    println!("Testing...");
}
```

## Making Changes

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Make your changes
4. Add tests for new functionality
5. Ensure all checks pass
6. Commit using conventional commits
7. Push and create PR
8. Publish on tag: `v*.*.*`
