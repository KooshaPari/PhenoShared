# agileplus-agents

Overview

agileplus-agents is a small Rust workspace providing helper crates for agent orchestration and workspace automation used by the AgilePlus project. The workspace contains three primary crates:

- crates/agileplus-agent-dispatch — dispatch and adapter layer that spawns/coordinates Claude Code / Codex subprocesses and provides PR/dispatch helpers.
- crates/agileplus-agent-review — review-loop logic that polls external systems (GitHub, Coderabbit) and feeds events back to agents.
- crates/agileplus-agent-service — gRPC server exposing AgentDispatchService (agents.proto) and serving as the entrypoint for local/remote orchestration.

This README documents how to install, run, and develop the workspace locally.

Install

Prerequisites

- Rust toolchain (stable, 1.70+ recommended). Install via rustup: `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`
- cargo and rustc available on PATH (provided by rustup)
- protoc/tonic build dependencies: building the service requires a C toolchain for prost/tonic-build; on macOS install Xcode command line tools: `xcode-select --install`.
- gh CLI (optional) — many adapters call `gh` when creating PRs or inspecting repos; install from https://cli.github.com/

Workspace install

Clone the repository at the workspace root (you already have this repo). Build workspace dependencies and crates with:

    cargo build --workspace --release

Usage

Build + run the gRPC service (development)

    # build
    cargo build --workspace

    # run the service binary from workspace root
    cargo run -p agileplus-agent-service -- --help

Running individual crates

- agileplus-agent-dispatch: provides the adapter/dispatch logic used by review loops and the service. It is a library crate and is consumed by other crates; run unit tests with:

    cargo test -p agileplus-agent-dispatch

- agileplus-agent-review: contains review loop polling logic and integrations (GitHub/Coderabbit). It is exercised by the service and also contains integration tests:

    cargo test -p agileplus-agent-review

Development

Build

    # build everything in debug
    cargo build --workspace

    # build release binaries
    cargo build --workspace --release

Test

    # run unit/integration tests for all workspace crates
    cargo test --workspace

Formatting & linting

This workspace follows strict linting rules and forbids unsafe code via workspace lints. Use rustfmt and clippy during development:

    cargo fmt --all
    cargo clippy --workspace --all-targets -- -D warnings

Notes / Architecture

- The workspace is intentionally small and split into focused crates for dispatch, review, and the gRPC service. See `Cargo.toml` at the workspace root for declared workspace members and shared dependencies.
- The crates rely on Tokio async runtime, Tonic for gRPC, and common crates (serde, tracing, uuid).
- The gRPC service (`agileplus-agent-service`) generates code via `tonic-build` at build time (build.rs). Ensure you have a working toolchain for tonic-build.

AgilePlus governance

Per project governance, any substantive change (code or documentation) must be tracked in AgilePlus using the AgilePlus CLI. If you add or modify functionality, create a spec using the AgilePlus CLI before implementing work:

    agileplus specify --title "<feature>" --description "<short description>"

License

This workspace is licensed under the MIT license. See the repository Cargo.toml for the canonical license field.

Contributing

Please follow the repository contribution guidelines, respect branch naming conventions (feat/, fix/, chore/, docs/, ci/), and ensure all changes are validated against workspace linters and tests before opening a PR.

Files referenced

- /Users/<REDACTED>/CodeProjects/Phenotype/repos/agileplus-agents/Cargo.toml
- /Users/<REDACTED>/CodeProjects/Phenotype/repos/agileplus-agents/crates/agileplus-agent-dispatch
- /Users/<REDACTED>/CodeProjects/Phenotype/repos/agileplus-agents/crates/agileplus-agent-review
- /Users/<REDACTED>/CodeProjects/Phenotype/repos/agileplus-agents/crates/agileplus-agent-service

If you want, I can also create an AgilePlus work package for adding or updating this README so the change is tracked according to project rules.
