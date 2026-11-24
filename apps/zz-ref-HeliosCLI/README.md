> **Pinned references (Phenotype-org)**
>
> - MSRV: see rust-toolchain.toml
> - cargo-deny config: see deny.toml
> - cargo-audit: rustsec/audit-check@v2 weekly
> - Branch protection: 1 reviewer required, no force-push
> - Authority: phenotype-org-governance/SUPERSEDED.md

# heliosCLI

[![Build](https://img.shields.io/github/actions/workflow/status/KooshaPari/heliosCLI/ci.yml?branch=main&label=build)](https://github.com/KooshaPari/heliosCLI/actions)
[![Release](https://img.shields.io/github/v/release/KooshaPari/heliosCLI?include_prereleases&sort=semver)](https://github.com/KooshaPari/heliosCLI/releases)
[![License](https://img.shields.io/github/license/KooshaPari/heliosCLI)](LICENSE)
[![Phenotype](https://img.shields.io/badge/Phenotype-org-blueviolet)](https://github.com/KooshaPari)
[![AI Slop Inside](https://sladge.net/badge.svg)](https://sladge.net) [![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/KooshaPari/helios-cli/total)](https://github.com/KooshaPari/helios-cli/releases)

Rust-based CLI for managing Helios CLI applications with multi-backend support and sandboxing. A community fork of [OpenAI Codex CLI](https://github.com/openai/codex) with performance optimizations, a multi-crate harness system, and Phenotype governance integration.

> **Note:** The legacy `helioscope` fork (`KooshaPari/helioscope`) was retired 2026-06-21
> per [the v12-20 closure rationale](https://github.com/KooshaPari/helios-cli/blob/main/docs/rationalization/helioscope-absorption.md).
> `helios-cli` is the canonical codex fork in the Phenotype fleet.

<p align="center">
  <strong>helios</strong> - run AI coding agents locally with full control over execution, sandboxing, and model backends.
</p>

## Architecture Overview

The **active** Cargo workspace is the root harness workspace (`Cargo.toml`). The vendored
`codex-rs/` and `codex-cli/` trees are retained as reference material and are **excluded**
from the root workspace (see `ARCHITECTURE.md`).

### Harness Workspace (`Cargo.toml`)

Harness crates for validation, orchestration, and resilience:

```
crates/
+-- harness_queue/          # Task queue management
+-- harness_rollback/       # Rollback and undo support
+-- harness_runner/         # Task execution runner
+-- harness_scaling/        # Dynamic scaling logic
+-- harness_schema/         # Schema definitions
+-- harness_spec/           # Specification parsing
+-- harness_teammates/      # Multi-agent coordination
+-- harness_utils/          # Shared utilities
+-- harness_verify/         # Verification and validation
`-- harness_recorder/       # KLA CLI recorder (binary: kla)
```

**Note:** Additional crates in `crates/` (harness_cache, harness_checkpoint, harness_discoverer, harness_elicitation, harness_interfaces, harness_normalizer, harness_orchestrator, harness_pyo3, arch_test, helios_config, pheno-plugin, plugin-arch) are also workspace members. Vendored `codex-rs/` / `codex-cli/` are not.

### Vendored Codex tree (`codex-rs/`, excluded)

Reference layout for the upstream agent CLI (build separately under `codex-rs/`):

```
codex-rs/
+-- cli/                    # Rust CLI entry point (binary: codex)
+-- core/                   # Core agent logic and config
+-- tui/                    # Terminal UI
+-- exec/                   # Non-interactive execution mode
+-- protocol/               # Wire protocol types
+-- config/                 # Configuration loading
+-- execpolicy/             # Execution policy engine
+-- mcp-server/             # MCP server implementation
+-- login/                  # Authentication (OAuth, API key)
+-- secrets/                # Secure credential storage
+-- hooks/                  # Pre/post execution hooks
+-- state/                  # Session state management
+-- file-search/            # Codebase search
+-- apply-patch/            # Diff application
+-- feedback/               # User feedback collection
`-- utils/                  # Shared utilities
```

### Key Crates and Responsibilities

| Crate                   | Responsibility                                                         |
| ----------------------- | ---------------------------------------------------------------------- |
| `kla`                   | Harness CLI recorder (binary: `kla`)                                   |
| `helios_config`         | Centralised workspace config                                           |
| `codex` (vendored)      | Upstream agent CLI binary under `codex-rs/cli` (not in root workspace) |
| `codex-core` (vendored) | Agent core: config loading, terminal detection, session management     |
| `codex-tui` (vendored)  | Interactive terminal UI with streaming responses                       |
| `codex-exec` (vendored) | Non-interactive execution mode for scripted/CI usage                   |

## Setup Instructions

### System Requirements

| Requirement | Details                                                             |
| ----------- | ------------------------------------------------------------------- |
| OS          | macOS 12+, Ubuntu 20.04+/Debian 10+, or Windows 11 via WSL2         |
| Rust        | Edition 2024 (codex-rs workspace), Edition 2021 (harness workspace) |
| RAM         | 4 GB minimum (8 GB recommended)                                     |
| Git         | 2.23+ for built-in PR helpers (optional)                            |

### Building from Source

```bash
# Clone the repository
git clone https://github.com/KooshaPari/helios-cli.git heliosCLI
cd heliosCLI

# Add upstream for tracking OpenAI Codex changes
git remote add upstream https://github.com/openai/codex.git

# Install Rust toolchain (if not already installed)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source "$HOME/.cargo/env"
rustup component add rustfmt
rustup component add clippy

# Install build helpers
cargo install just
cargo install --locked cargo-nextest  # optional

# Build the Rust workspace
cd codex-rs
cargo build

# Build the CLI workspace
cd ../codex-cli
npm install
npm run build
```

### Running Quality Checks

```bash
# Format check
cargo fmt --check

# Lint (zero warnings)
cargo clippy --all-targets -- -D warnings

# Run all tests
cargo test --all
```

### Syncing with Upstream

```bash
# Fetch upstream changes
git fetch upstream

# Sync main branch
git checkout main
git merge upstream/main
git push origin main

# Rebase a feature branch
git checkout helios-optimization
git rebase upstream/main
```

## CLI Usage Examples

### Interactive Mode (Default)

Launch the TUI with an optional prompt:

```bash
helios
helios "explain this codebase to me"
```

### Non-Interactive Execution

Run a single task without the TUI:

```bash
helios exec "add input validation to the login form"
helios exec --json "refactor the config loader"   # JSON output for scripting
```

### Code Review

Review a PR or branch non-interactively:

```bash
helios review --pr 42
```

### Session Management

Resume or fork a previous session:

```bash
helios resume                          # Pick from session list
helios resume --last                   # Resume most recent session
helios resume <session-id>             # Resume specific session
helios fork <session-id>               # Fork a previous session
```

### Authentication

```bash
helios login                           # OAuth device code flow
helios login --device-auth             # Explicit device auth
printenv OPENAI_API_KEY | helios login --with-api-key  # API key via stdin
helios login status                    # Check auth status
helios logout                          # Remove credentials
```

### Sandbox Execution

Run commands within a platform-specific sandbox:

```bash
# Linux (Landlock + seccomp)
helios sandbox linux -- "cat /etc/passwd"

# macOS (Seatbelt)
helios sandbox macos -- "ls -la"

# Windows (restricted token)
helios sandbox windows -- "dir"
```

### MCP Server Management

Manage external MCP (Model Context Protocol) servers:

```bash
helios mcp list
helios mcp add <name> <command>
helios mcp remove <name>
```

Run helios itself as an MCP server:

```bash
helios mcp-server
```

### Feature Flags

Inspect and toggle feature flags:

```bash
helios features list
helios features enable unified_exec
helios features disable shell_tool
```

Enable/disable features at runtime:

```bash
helios --enable web_search_request --disable unified_exec
```

### Shell Completions

Generate shell completions:

```bash
helios completion bash > ~/.local/share/bash-completion/completions/helios
helios completion zsh > ~/.zfunc/_helios
helios completion fish > ~/.config/fish/completions/helios.fish
```

### App Server (IDE Integration)

Run the app server for IDE extension connectivity:

```bash
helios app-server                           # stdio transport (default)
helios app-server --listen ws://127.0.0.1:4500  # WebSocket transport
```

### Apply Patches

Apply the latest diff produced by a helios agent session:

```bash
helios apply
```

## Configuration

Configuration lives in `~/.helios/config.toml` (or `~/.codex/config.toml` for compatibility). Supports profiles:

```toml
[profile.default]
model = "gpt-4o"
approval_policy = "on-request"
sandbox_mode = "workspace-write"

[profile.ci]
model = "gpt-4o-mini"
approval_policy = "auto-edit"
```

Override config from the CLI:

```bash
helios -c model=gpt-4o -c approval_policy=auto-edit
```

## Project Structure

```
heliosCLI/
+-- Cargo.toml              # Root workspace (harness crates)
+-- codex-rs/               # Vendored Codex Rust workspace (excluded)
|   +-- Cargo.toml
|   `-- cli/src/main.rs     # Upstream CLI entry (binary: codex)
+-- codex-cli/              # Vendored TypeScript CLI (excluded)
+-- crates/                 # Harness crates (kla, helios_config, ...)
+-- docs/                   # Documentation
|   +-- adrs/               # Architecture decision records
|   +-- specs/              # Feature specifications
|   `-- reference/          # Architecture guides
+-- .github/workflows/      # CI/CD pipelines
+-- AGENTS.md               # Agent operating instructions
`-- justfile                # Build/dev task runner
```

## Performance Branches

| Branch           | Focus                |
| ---------------- | -------------------- |
| `helios-cpu-opt` | CPU optimization     |
| `helios-lat-opt` | Latency optimization |
| `helios-mem-opt` | Memory optimization  |

## License

This repository is licensed under the [Apache-2.0 License](LICENSE).

## Documentation

This repository includes the following cross-cutting documents:

- [`AGENTS.md`](AGENTS.md) - operating instructions for AI agents and human contributors
- [`docs/`](docs/) - design notes, ADRs, and supporting documentation (see [`docs/index.md`](docs/index.md))
