<!-- AI-DD-META:START -->
<!-- This repository is planned, maintained, and managed by AI Agents only. -->
<!-- Slop issues are expected and intentionally present as part of an HITL-less -->
<!-- /minimized AI-DD metaproject of learning, refining, and building brute-force -->
<!-- training for both agents and the human operator. -->
![License](https://img.shields.io/github/license/KooshaPari/phenotype-infra?style=flat-square)
![AI-Slop](https://img.shields.io/badge/AI--DD-Slop%20Expected-orange?style=flat-square)
![AI-Only-Maintained](https://img.shields.io/badge/Planned%20%26%20Maintained%20by-AI%20Agents%20Only-red?style=flat-square)
<!-- AI-DD-META:END -->

> **Work state:** SCAFFOLD · **Progress:** `█████░░░░░ 50%`
> Compute/Infra consolidation monorepo (nanovms + PhenoCompose + BytePort). IaC validates, crates compile, but human-apply-only gate. · updated 2026-06-24

# phenotype-infra — Compute/Infra Consolidation Monorepo

> **Consolidation target** for nanovms (Go, 3-tier isolation) + PhenoCompose (Rust FFI + driver) + BytePort (Svelte tooling).

[![AI slop inside](https://sladge.net/badge.svg)](https://sladge.net) [![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/KooshaPari/phenotype-infra/total)](https://github.com/KooshaPari/phenotype-infra/releases)

This monorepo is created as part of the **L1-Alpha** wave of the Master DAG
(Compute/Infra + Observability Consolidation). It absorbs three previously
separate repositories into a single polyglot workspace:

| Component | Source | Language | Role |
|-----------|--------|----------|------|
| **nanovms-core** | `nanovms` | Go | 3-tier isolation (WASM/gVisor/Firecracker) |
| **nvms-ffi** | `PhenoCompose/bindings/rust-ffi` | Rust | `extern "C"` FFI bindings |
| **pheno-compose** | `PhenoCompose/pheno-compose-driver` | Rust | High-level Rust driver |
| **byteport** | `BytePort` | Svelte/TS | Infra tooling UI |

## Architecture

```
phenotype-infra/
├── crates/
│   ├── nanovms-core/       # Go source → libnvms_core.a (via CGo)
│   ├── nvms-ffi/           # Rust FFI bindings
│   └── pheno-compose/      # High-level Rust driver
├── tools/
│   └── byteport/           # Svelte infra tooling
├── docs/
│   ├── adr/                # Architecture Decision Records
│   ├── specs/              # Specifications
│   ├── governance/         # Governance docs
│   └── audit/              # Audit scorecards
└── .github/workflows/      # CI/CD
```

## Quick Start

```bash
# Build Go static lib
make nvms-c-archive

# Build Rust workspace
cargo build --workspace

# Run tests
cargo test --workspace

# All checks
cargo check --workspace

# BytePort (Svelte frontend)
cd tools/byteport && npm install && npm run dev
```

## License

Apache-2.0
