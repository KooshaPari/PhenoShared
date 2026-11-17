> **Work state:** ACTIVE · **Progress:** `███████░░░ 70%`
> Rust PTY CLI recorder (Playwright-for-CLI): record/screenshot/gif/demo. Builds; rck-core rich summary adopted. Hardening + broader script coverage ongoing. · updated 2026-06-02

# KLA (Kommand Line Automation)

[![Rust](https://img.shields.io/badge/rust-2021-orange.svg)](https://www.rust-lang.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

KLA is a Rust PTY CLI recorder for turning terminal sessions into repeatable recordings, screenshots, and scripted demos — a Playwright-for-CLI. It ships today as the `kla` command-line tool for documenting shell workflows and replaying them with consistent output, and is evolving toward a reusable CLI-recording framework other Phenotype tools can build on.

## Installation

Install from the Git repository with Cargo:

```bash
cargo install --git https://github.com/KooshaPari/KommandLineAutomation
```

For local development:

```bash
git clone https://github.com/KooshaPari/KommandLineAutomation
cd KommandLineAutomation
cargo build
```

## Usage

Record a scripted terminal session:

```bash
kla record examples/git-workflow.kla.yaml --output ./output --format gif
```

Run a script in demo mode:

```bash
kla demo examples/git-workflow.kla.yaml
```

Step through commands manually:

```bash
kla demo examples/git-workflow.kla.yaml --interactive
```

Convert a recording to another format:

```bash
kla convert input.gif --output output.png
```

Take a single-command screenshot:

```bash
kla screenshot "echo hello" --output hello.png
```

## Script Format

Scripts are YAML files that describe terminal settings and steps. A script typically includes:

```yaml
name: "Git Workflow Demo"
settings:
  width: 120
  height: 30
  shell: "bash"
  theme: "default"
steps:
  - type: command
    text: "git status"
    wait: "1s"
  - type: screenshot
    name: "status"
```

## Dependencies

KLA is built with:

- `portable-pty` for PTY control
- `clap` for the CLI
- `tokio` for async execution
- `serde`, `serde_yaml`, and `serde_json` for script parsing
- `crossterm`, `vt100`, and `image` for terminal rendering and output generation
- `gif` for animated exports
- `anyhow` and `thiserror` for error handling

## Development

Run the build and test suite:

```bash
cargo build
cargo test
```

## Notes

The current CLI surface is centered on `record`, `demo`, `screenshot`, and `convert`. The recorder core is the starting point: the trajectory is to evolve it into a reusable CLI-recording framework (a Playwright-for-CLI) that other Phenotype tools can drive — a recording/replay engine plus the thin `kla` binary on top. Implementation stays lean (KISS applies to how it's built, not to how far it can grow).
