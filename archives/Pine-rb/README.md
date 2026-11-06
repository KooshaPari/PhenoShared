Work-state: active — `[#######---] 70%`

<!-- AI-DD-META:START -->
<!-- This repository is planned, maintained, and managed by AI Agents only. -->
<!-- Slop issues are expected and intentionally present as part of an HITL-less -->
<!-- /minimized AI-DD metaproject of learning, refining, and building brute-force -->
<!-- training for both agents and the human operator. -->
![Downloads](https://img.shields.io/github/downloads/KooshaPari/Pine/total?style=flat-square&label=downloads&color=blue) [![AI slop inside](https://sladge.net/badge.svg)](https://sladge.net)
![GitHub release](https://img.shields.io/github/v/release/KooshaPari/Pine?style=flat-square&label=release)
![License](https://img.shields.io/github/license/KooshaPari/Pine?style=flat-square)
![AI-Slop](https://img.shields.io/badge/AI--DD-Slop%20Expected-orange?style=flat-square)
![AI-Only-Maintained](https://img.shields.io/badge/Planned%20%26%20Maintained%20by-AI%20Agents%20Only-red?style=flat-square)
![HITL-less](https://img.shields.io/badge/HITL--less%20AI--DD-metaproject-yellow?style=flat-square)

> ⚠️ **AI-Agent-Only Repository**
>
> This repo is **planned, maintained, and managed exclusively by AI Agents**.
> Slop issues, rough edges, and AI artifacts are **expected and intentionally
> present** as part of an **HITL-less / minimized AI-DD** metaproject focused
> on learning, refining, and brute-force training both the agents and the
> human operator. Bug reports and contributions are still welcome, but please
> expect AI-generated code, comments, and documentation throughout.
<!-- AI-DD-META:END -->

> **Work-state:** pre-alpha — `[###-------] 25%`
>
> Wine-equivalent compatibility layer for Phenotype; foundation bootstrapped 2026-04-30. Research + architecture phase. Pending: Windows syscall translation layer, macOS/Linux adapter scaffolding, nanovms integration.

# Pine — Wine-Equivalent for Phenotype

**Pine** is a compatibility layer enabling Windows, macOS, and Linux applications to run on Phenotype-native infrastructure. Like Wine translates Windows syscalls to POSIX, Pine translates applications into Phenotype execution environments.

## Quickstart

```bash
git clone https://github.com/KooshaPari/Pine.git
cd Pine
cargo build --workspace --all-targets
cargo test  --workspace --all-features --no-fail-fast
```

The workspace builds five crates (`pine-core`, `pine-loader`, `pine-syscall`,
`pine-compat`, `pine-nvms`) on stable Rust (2021 edition). For the full
prerequisites, layout walkthrough, and docs-site workflow, see
[`docs/src/getting-started.md`](docs/src/getting-started.md) and
[`CONTRIBUTING.md`](CONTRIBUTING.md).

## PINE where PINE is an enhancemnt over WINE similar to Proton and Re-eng of Crossover  + Adaptation to Phenotype OS targets
## Status

**PRE-ALPHA** — Foundation bootstrapped 2026-04-30.

## Architecture

See `docs/ARCHITECTURE.md` for layer design.

## Competitor Analysis

| Project | What it does | Pine relevance |
|---------|-------------|----------------|
| **Wine** | Windows→Linux syscall translation | Canonical reference |
| **Proton** | Wine + DXVK/GE-Proton for Steam | DirectX→Vulkan translation |
| **Box86/Box64** | x86/ARM binary translation | Interpreter-level emulation |
| **Darling** | macOS apps on Linux | Cocoa→GTK translation |
| **QEMU** | Full hardware emulation | Emulation reference |
| **OrbStack** | Docker Desktop replacement | Docker-less containerization |
| **nvms/nanovms** | Phenotype microVM runtime | Isolation layer to build on |
| **Firecracker** | Lightweight microVMs | MicroVM isolation reference |
| **Docker Desktop** | Container runtime | Docker API compatibility |

## Why Pine

Phenotype needs application compatibility. Users will want to run Windows apps (legacy LOB, games), macOS apps (native tooling), Linux GUI apps, Android apps, and other cross-platform binaries. Pine is the translation and compatibility layer.

## Key Research Questions

1. **Translation scope**: Syscall-only (Wine) vs. binary translation (Box86)?
2. **Isolation**: Use nvms microVMs for untrusted code, native execution for trusted?
3. **Performance target**: Wine ~5-15% overhead vs QEMU 10-1000%?
4. **Win32 surface**: Which APIs first? Start with filesystem + process + networking?
5. **DXVK**: Can we leverage Proton's DXVK/vkd3d-proton?
6. **nvms integration**: Build isolation layer on existing Firecracker runtime?

## Stack

- Core: Rust (translation layer, syscall emulation)
- Runtime: Go (orchestration, lifecycle management)
- Agents: Python/TypeScript (testing harness)
<!-- ci-refresh: 2026-06-10T09:24:35Z -->

## Documentation

This repository includes the following cross-cutting documents:

- [`AGENTS.md`](AGENTS.md) — operating instructions for AI agents and human contributors
- [`docs/`](docs/) — design notes, ADRs, and supporting documentation (see [`docs/index.md`](docs/index.md))

