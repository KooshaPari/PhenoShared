---
layout: home

hero:
  name: Sidekick
  text: Agent Utility Collection
  tagline: A polyglot Rust + Python workspace of agent utility crates for the Phenotype ecosystem.
  actions:
    - theme: brand
      text: Getting Started
      link: /getting-started
    - theme: alt
      text: View on GitHub
      link: https://github.com/KooshaPari/Sidekick

features:
  - title: Rust Workspace
    icon: 🦀
    details: Compiled Rust 2021 edition crates with strict linting and full test coverage.
  - title: Python Integration
    icon: 🐍
    details: FastMCP server for budget LLM routing, vendored as a Python sub-package.
  - title: Phenotype Native
    icon: 🔗
    details: Designed for the Phenotype collections ecosystem — emit dispatch events, integrate with phenoEvents.
---

## About

**Sidekick** is a named Rust workspace consolidating core agent infrastructure
utilities for the Phenotype ecosystem. Each sub-crate is independently versioned
and consumable; consumers import only what they need.

## Members

| Crate | Purpose |
|-------|---------|
| `sidekick-presence` | User presence and status tracking (MCP server) |
| `sidekick-dispatch` | Multi-provider agent dispatch |
| `cheap-llm-mcp` | Budget LLM routing (FastMCP + Python) |
| `sidekick-messaging` | Multi-provider messaging adapter (stub) |

## Quality bar

All canonical members maintain 100% functional requirement traceability.

- Workspace edition: Rust 2021
- Build profile: `opt-level = 3`, LTO enabled
- Errors: `thiserror` with `#[from]`
- Serialization: `serde` (derive)
- Tests: inline `#[cfg(test)]` modules
- Linting: `cargo clippy -- -D warnings`

See the [Getting Started](./getting-started) guide to build the workspace and
run the test suite, or browse the source on
[GitHub](https://github.com/KooshaPari/Sidekick).
