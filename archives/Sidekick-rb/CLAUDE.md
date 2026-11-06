# Sidekick — CLAUDE.md

Sidekick is a polyglot Rust + Python workspace of agent utility crates for the Phenotype ecosystem.

## Project

- **Name**: Sidekick
- **Type**: Named collection (workspace, not monorepo)
- **Language Stack**: Rust (2021 edition), Python (FastMCP)
- **Location**: `/Users/kooshapari/CodeProjects/Phenotype/repos/Sidekick`
- **Published**: crates.io (crate prefix: `sidekick-*`)

## AgilePlus Mandate

All work tracked in `/Users/kooshapari/CodeProjects/Phenotype/repos/AgilePlus`:

```bash
cd /Users/kooshapari/CodeProjects/Phenotype/repos/AgilePlus
agileplus specify --title "Feature" --description "Details"
agileplus status <id> --wp <wp> --state <state>
```

## Stack

- **Build**: `cargo build --release --workspace`
- **Test**: `cargo test --workspace`
- **Lint**: `cargo clippy --workspace -- -D warnings`
- **Format**: `cargo fmt --check`

## Crates

| Crate | Source | Purpose |
|-------|--------|---------|
| `sidekick-presence` | agent-user-status | User presence + status tracking |
| `sidekick-dispatch` | thegent-dispatch | Multi-provider agent dispatch |
| `cheap-llm-mcp`      | vendored, updated 2026-06-08 | Budget LLM routing (FastMCP + Python) |
| `sidekick-messaging` | TBD (agent-imessage) | Multi-provider messaging (deferred) |

**FYI:** agent-user-status is a Sidekick-canonical peer of agent-imessage (both MCP servers for agent infrastructure). Both repos maintain independent FR traceability and test coverage under Sidekick governance.

## Workspace Conventions

- Each crate stands alone; no inter-crate dependencies by design
- Shared dependencies declared in root `Cargo.toml` (`workspace = true`)
- All public types: `Debug`, `Clone` where possible
- Errors via `thiserror` with `#[from]`
- Serialization via `serde`
- Tests inline (`#[cfg(test)]` modules)

## Quality Gates

```bash
cargo fmt
cargo clippy --workspace -- -D warnings
cargo test --workspace
```

## Governance

See:
- `/Users/kooshapari/CodeProjects/Phenotype/repos/CLAUDE.md` — Phenotype workspace
- `/Users/kooshapari/CodeProjects/Phenotype/CLAUDE.md` — Org rules
- `~/.claude/CLAUDE.md` — Global governance
