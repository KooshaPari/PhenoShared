# phenotype-infra - Design Document

## Overview

phenotype-infra is the **infrastructure spine** for the phenotype-org polyrepo portfolio. It provides shared CI/CD, governance, observability, and build tooling for all phenotype-org repositories.

## Architecture

### Modules

- `/crates/` - Rust workspace crates (pheno-config, pheno-compose, nanovms-core, nvms-ffi, observability, oci-helpers, oci-lottery, oci-post-acquire, phenotype-logging-stub)
- `/iac/` - Infrastructure as code (Terraform modules for Cloudflare Workers, R2, D1, KV; Ansible playbooks; Tailscale config)
- `/benches/` - Criterion benchmarks
- `/fuzz/` - Fuzz testing harnesses (cargo-fuzz)
- `/tests/` - Integration tests
- `/scripts/` - CI helpers, linter configs, audit scripts
- `/tools/` - Auxiliary build and development tooling
- `/configs/` - Shared configuration files
- `/docs/` - Documentation and governance records

### CI/CD

- **Trunk Check** - Linting and formatting (Prettier, Ruff, Taplo, YAMLlint)
- **Cargo Deny** - License and advisory auditing
- **Scorecard** - OpenSSF security scorecard (88-pillar audit)
- **Infisical** - Secret synchronization
- **Mergify** - Auto-merge on approved + green CI
- **Lefthook** - Local pre-commit hooks
- **Pre-commit** - Standard commit hooks framework

### Domain

- **Cloudflare Workers** - Primary deployment target
- **Terraform** - Infrastructure as code
- **Ansible** - Configuration management
- **Rust** - Core implementation language (workspace of 8+ crates)
- **Docker** - Container builds for OCI helpers and nanovms

## Quality Gates

- All PRs require >=1 approval (branch protection)
- CODEOWNERS scoped per directory
- Dual license: Apache-2.0 OR MIT
- 88-pillar audit scorecard for regression prevention
- Cargo deny for license/advisory auditing
- Clippy, rustfmt, and tarpaulin coverage enforcement

## GFX SDK (absorbed from PhenoGfx)

**phenotype-gfx** is a polyglot graphics SDK providing voxel rendering, terrain, and water simulation primitives. It exposes both a Rust core library and Unity C# bindings.

### GFX Architecture

```
phenotype-gfx/
├── crates/
│   └── phenotype-voxel/  # Compatibility shim re-exporting the core voxel kernel (ADR-004)
├── src/
│   ├── voxel/            # Voxel kernel: chunk storage, meshing (cubic, greedy), materials
│   ├── lod.rs            # LOD system: frustum culling, chunk render planning
│   ├── streaming.rs      # Streaming window: ring-based chunk lifecycle, eviction
│   ├── water/            # Water simulation: Gerstner waves, fluid mesh
│   ├── postfx/           # Post-processing: SSAO, SSGI, Bloom, ACES, LUT
│   ├── terrain/          # Terrain: height field, chunk mesh builder
│   └── voxelizer.rs      # Sprite voxelizer: voxel-to-sprite rendering
├── tests/                # Cross-module integration tests
├── examples/             # Sample projects
└── docs/                 # API reference + design docs
```

### Key GFX Design Decisions

1. **Rust core + C# bindings** — performance-critical rendering in Rust, Unity integration via P/Invoke FFI
2. **Dual license (Apache-2.0 OR MIT)** — maximum compatibility for game studios and open-source projects
3. **Crate-per-feature** — each rendering primitive is an isolated crate for independent compilation and testing

## See Also

- `AGENTS.md` - AI agent instructions
- `CLAUDE.md` - Claude Code instructions
- `CONTRIBUTING.md` - Contribution guidelines
- `SECURITY.md` - Security policy
