# PhenoShared

The Phenotype ecosystem container repository. Houses product dossiers, shared infrastructure crates, cross-repo governance, and absorbed project sources.

[![CI](https://github.com/KooshaPari/PhenoShared/actions/workflows/ci.yml/badge.svg)](https://github.com/KooshaPari/PhenoShared/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE-MIT)

---

## What It Is

PhenoShared is the umbrella monorepo for the [Phenotype](https://github.com/KooshaPari) ecosystem. It consolidates infrastructure, tooling, governance, and product dossiers that previously lived across dozens of standalone repositories.

**Key facts:**
- Rust workspace with 76 members and 365+ crate directories
- Absorbed repos: PhenoDesign, PhenoFabric, PhenoInfra, PhenoLab, PhenoGfx, PhenoRegistry, PhenoMLX, PhenoAI
- 27 product dossiers in `docs/dossiers/`
- Part of the [docs-3](../../Downloads/docs-3/) Atlas quality-gate program
- Compiles clean: `cargo check --workspace` passes

## Ecosystem Map

### Absorbed Repositories (now part of this monorepo)

| Repo | Absorbed As | Key Content |
|------|-------------|-------------|
| **PhenoDesign** | Early absorption | Design system, shared components |
| **PhenoFabric** | `crates/fabric-*` (21 crates) | Fabric routing, transport, runtime |
| **PhenoInfra** | `crates/phenotype-infrakit` | Compute mesh IaC (OCI/CF/GCP/AWS/Vercel) |
| **PhenoLab** | `crates/*` + `python/` | Compression stack, RLVR harness, 1,553 files |
| **PhenoGfx** | `crates/phenotype-gfx` + `phenotype-gfx/` | GFX SDK (Rust voxel + C# terrain/water) |
| **PhenoRegistry** | `crates/phenotype-*` + `registry/` | Org registry, master index, 3,848 files |
| **PhenoMLX** | `crates/omlx-*` + `python/omlx_research/` | MLX inference engine, perf-core, Rust FFI |

### Standalone Repos (still separate)

| Repo | Role |
|------|------|
| [HeliosLab](https://github.com/KooshaPari/HeliosLab) | Helios compute lab, GPU orchestration |
| [Portage](https://github.com/KooshaPari/portage) | Portage CLI and SDK |
| [pheno](https://github.com/KooshaPari/pheno) | Phenotype Infrastructure Kit (85 Rust crates) |
| [phenotooling](https://github.com/KooshaPari/phenotooling) | Org internal tooling + Benchora |

## Product Dossiers

Each product in the Phenotype ecosystem has a dossier answering the docs-3 Atlas questions with concrete source evidence.

**Location:** `docs/dossiers/`

| File | Purpose |
|------|---------|
| `HANDOFF-PHENOSHARED.md` | This repo's absorption history and current state |
| `HANDOFF-PHENOREGISTRY.md` | Registry handoff context |

**Atlas program:** `~/Downloads/docs-3/` defines quality gates (85% coverage floors, independent negative controls, assurance matrix) that all products must satisfy.

## Repository Structure

```
PhenoShared/
  crates/                  # 365+ Rust crate directories (76 workspace members)
  docs/
    dossiers/              # Product dossiers (docs-3 Atlas)
    absorption/            # Absorption history and tracking
    architecture/          # Architecture decision records
  absorption/              # Absorbed repo snapshots (byteport, pheno-forge, etc.)
  _archived/               # Archived content (byteport, nanovms-core, nvms-ffi)
  governance/              # Cross-repo governance contracts
  python/                  # Python packages (omlx_research, research tools)
  scripts/                 # Automation and CI scripts
  tests/                   # Integration and E2E tests
  Cargo.toml               # Rust workspace root
  pyproject.toml           # Python workspace root
  GOVERNANCE.md            # Decision authority and specification lifecycle
  ECOSYSTEM_MAP.md         # Full ecosystem index
```

## Getting Started

```bash
# Clone
git clone https://github.com/KooshaPari/PhenoShared.git
cd PhenoShared

# Rust workspace
cargo check --workspace

# Python environment
python -m venv .venv
source .venv/bin/activate
pip install -e .

# Run tests
cargo test --workspace
```

## How to Contribute

1. Read `GOVERNANCE.md` for decision authority and evidence rules
2. Check `docs/dossiers/` for the relevant product dossier
3. Follow the specification lifecycle: Captured -> Synthesized -> Specified -> Planned -> Implemented -> Validated -> Shipped
4. All claims require reproducible evidence (see the [Evidence Rule](GOVERNANCE.md#evidence-rule))
5. Open a PR against `main`; CI must pass before merge

**Cross-repo work:** When changes span PhenoShared and a standalone repo (HeliosLab, Portage, etc.), coordinate via issues in both repos and reference the shared AGENTS.md contract.

## Governance

Decisions follow a structured authority model defined in `GOVERNANCE.md`:

| Decision | Owner |
|----------|-------|
| Product intent | Human sponsor |
| Requirements and acceptance | AgilePlus |
| Agent/labor dispatch | thegent |
| Runtime placement | Phenotype Fabric |
| Operational history | SessionLedger |
| Cross-artifact traces | Tracera |

## Related Repos

- [KooshaPari](https://github.com/KooshaPari) -- GitHub org (all repos)
- [PhenoMLX](https://github.com/KooshaPari/phenotype-omlx) -- MLX inference (standalone mirror)
- [HeliosLab](https://github.com/KooshaPari/HeliosLab) -- Compute lab
- [Portage](https://github.com/KooshaPari/portage) -- CLI and SDK
- [pheno](https://github.com/KooshaPari/pheno) -- Infrastructure Kit
- [phenotooling](https://github.com/KooshaPari/phenotooling) -- Internal tooling

## License

MIT -- see [LICENSE-MIT](LICENSE-MIT) for details.

Copyright (c) 2026 Koosha Pari
