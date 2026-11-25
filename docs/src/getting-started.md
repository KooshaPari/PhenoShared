---
title: Getting Started
---

# Getting Started

This page is a quick, opinionated path from a fresh checkout of Pine to a
green local build. It is intentionally short — for the deep design, see
[ARCHITECTURE.md](https://github.com/KooshaPari/Pine/blob/main/docs/ARCHITECTURE.md).

## Prerequisites

| Tool | Version | Why |
|------|---------|-----|
| Rust toolchain | stable (2021 edition) | Builds the `pine-*` workspace crates |
| Node.js | 20+ | Builds this VitePress documentation site |
| Git | any recent | Check out the workspace |

The workspace is a Rust 2021 cargo workspace rooted at `Cargo.toml`. The
authoritative manifest is tiny — it just glues the crates together:

```toml
# Cargo.toml (workspace root)
[workspace]
members = ["crates/*"]
resolver = "2"
```

The five crates that make up the Pine workspace are:

| Crate | Role |
|-------|------|
| `pine-core` | Domain types (`ProcessId`, `SyscallNumber`) and ports (`Loader`, `SyscallHandler`) |
| `pine-loader` | Binary parsers (PE/ELF/Mach-O via `goblin`) |
| `pine-syscall` | Syscall translation tables (Linux + Windows) and plugin registry |
| `pine-compat` | Public `CompatibilityLayer` façade |
| `pine-nvms` | `nvms` microVM runtime adapter (subprocess wrapper) |

## Clone and build

```bash
git clone https://github.com/KooshaPari/Pine.git
cd Pine
cargo build --workspace --all-targets
```

A successful first build produces library artifacts in `target/debug/` and
resolves dependencies like `goblin`, `serde`, `thiserror`, `libloading`, and
`scroll`.

## Run the tests

```bash
cargo test --workspace --all-features --no-fail-fast
```

You should see the full test matrix pass — including the syscall table
completeness tests, the binary loader integration tests (ELF + PE), and the
doc-tests for each crate.

## Lint and format

The Rust quality bar is strict and CI-enforced:

```bash
# Format check (must be clean)
cargo fmt --all -- --check

# Lint (warnings are errors)
cargo clippy --workspace --all-targets --all-features -- -D warnings

# Release build
cargo build --release
```

## Project layout

```
.
├── Cargo.toml              # Workspace manifest
├── Cargo.lock              # Lockfile (generated)
├── crates/                 # Rust workspace members
│   ├── pine-core/          # Domain types + port traits
│   ├── pine-loader/        # PE / ELF / Mach-O loaders
│   ├── pine-syscall/       # Syscall translation tables
│   ├── pine-compat/        # Public façade
│   └── pine-nvms/          # nvms microVM adapter
├── docs/                   # Documentation
│   ├── ARCHITECTURE.md     # Layer design
│   ├── SSOT.md             # Single source of truth
│   ├── index.md            # Auto-generated doc index
│   ├── src/                # VitePress site source
│   └── .vitepress/         # VitePress config
├── .github/
│   └── workflows/          # CI, governance, release, docs
├── README.md
├── AGENTS.md
└── STATUS.md
```

## Working with the docs site

The GitHub Pages site in `docs/` is built with [VitePress](https://vitepress.dev/).

```bash
cd docs
npm install --legacy-peer-deps
npm run docs:dev      # local dev server
npm run docs:build    # production build → docs/.vitepress/dist
npm run docs:preview  # preview the production build locally
```

> The site content lives under `docs/src/`. This keeps it isolated from the
> pre-existing `docs/index.md` (the auto-generated cross-reference index) and
> from the long-form design docs (`ARCHITECTURE.md`, `SSOT.md`, `slsa.md`).

## Environment configuration

Pine itself does not require any API tokens or secrets to build or test. The
`nvms` runtime it depends on for isolation does take runtime configuration
once you go beyond the unit tests — wire it through environment variables,
**never** commit credentials to the repo. When examples or docs need to show
a token, use an obvious placeholder such as `YOUR_API_TOKEN` or
`YOUR_NVMS_ENDPOINT`, never a realistic-looking string.

## Next steps

- Read [ARCHITECTURE.md](https://github.com/KooshaPari/Pine/blob/main/docs/ARCHITECTURE.md)
  for the full layer design and the Win32 → Phenotype syscall mapping.
- Skim [SSOT.md](https://github.com/KooshaPari/Pine/blob/main/docs/SSOT.md)
  for the current architectural state and the dependency DAG.
- Open an issue or pull request on
  [GitHub](https://github.com/KooshaPari/Pine) — contributions welcome.
