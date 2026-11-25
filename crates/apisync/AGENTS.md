# Apisync — AGENTS.md

## Project Overview

Rust API toolkit providing REST, GraphQL, and WebSocket support.

## Agent Rules

1. **Read CLAUDE.md first** before making changes
2. **Test first** - write tests before implementation
3. **Clippy clean** - all lints must pass before PR
4. **Async-first** - all handlers must be async

## Quality Gates

```bash
cargo test
cargo clippy -- -D warnings
cargo fmt --check
cargo doc
```

## Architecture

Follow tower-based middleware pattern:
- Implement `tower::Layer` for new middleware
- Implement `tower::Service` for request handlers
- Async-first design with tokio/hyper

## Key Components

- **REST** - Router and handler abstractions
- **GraphQL** - Schema and resolver helpers
- **WebSocket** - Connection management
- **Middleware** - Auth, logging, CORS

## See Also

- **CLAUDE.md**: `./CLAUDE.md`
- **PRD.md**: `./PRD.md`

## Backlog pointer

The next round of v37 audit findings to tackle lives in
`docs/audit/v37-findings.md` (if present) or in the `## [Unreleased]` section
of `CHANGELOG.md`. Start there before opening new work.
