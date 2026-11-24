---
product: PhenoShared
repo: KooshaPari/PhenoShared
commit: origin/main@6ec4ae563 (working tree observed at ad667428b)
date: 2026-11-10
method: read-only file inspection (`head`, `ls`, `awk`, `grep`, `find`, `sed`) of the working tree plus read-only `git log` / `gh repo view` metadata; no builds, no writes inside the repo
confidence: high for file-cited and git-cited facts; build health is UNKNOWN (no build was run for this dossier)
---

# Product Dossier - PhenoShared

## Executive summary

- **What it honestly is:** a *container repository*, not a product. It is a shared-infrastructure foundation monorepo holding the Rust crates, reusable GitHub Actions workflows and composite actions, and shared documentation (including the Global Handbook) that the rest of the fleet consumes (`README.md:3-6`).
- **Role:** the org's *shared layer*, deliberately not a user-facing product surface; category is "Shared infrastructure / foundation monorepo" (`README.md:3-4`; `docs/dossiers/HANDOFF-PHENOSHARED.md`, "Role: Pooled foundation monorepo (Rust workspace + absorbed repos)").
- **Scale:** 283 unique declared workspace member paths (`Cargo.toml` `members` holds 287 strings: 1 comment, 3 duplicates), 372 entries under `crates/`, 84 reusable workflow files, 5 composite actions, 178 project manifests under `projects/*.json`, 2,494 Markdown files under `docs/` (measured 2026-11-10; README snapshot numbers are older and lower).
- **Shape:** a Rust workspace (edition 2021, MSRV 1.80, version `0.3.10`) plus companion TypeScript packages.
- **Flagship:** the `substrate` spine - a dispatch facade that routes a task to the best available coding engine through a deterministic planner and hexagonal ports, so consumers depend on one facade instead of wiring adapters by hand (`README.md:49-56`).
- **Boundary enforcement is mechanical:** `arch-test` fails the build when a dependency edge crosses the domain/adapter boundary the wrong way (`README.md:55-56`).
- **It is an absorption hub:** PhenoFabric (997 files, 118K lines), PhenoRegistry (3,848 files, 2.1M lines), PhenoInfra, PhenoGfx and FocalPoint were absorbed; 33 per-project absorption records live in `docs/absorption/` with an index at `docs/ABSORPTION_INDEX.md`.
- **Maturity verdict (source's own words):** "production-grade foundation that is *actively growing but visibly mid-consolidation*." Build health was last verified 2026-09-16 (`cargo check --workspace` PASS, 0 errors, 47 warnings at `main` @ `1056f3e8`); **current build status is UNKNOWN** - no build was run for this dossier.
- **Known drift:** the README's headline table still reports the older counts (76 packages / 329 manifests) while the tree has grown to 283 members / 372 crate directories; `governance/` has no README despite shipping four happy-path governance files.
- **Real positioning risk:** two self-descriptions coexist - README calls it "a container repository, not a single-purpose project", while `PRD.md:3` calls it "a Rust workspace ... with no inter-crate dependencies", which contradicts the actual substrate spine.
- **Governance posture:** commits carry ledger trailers (`tx-agent`, `tx-validated`), history is append-only, and the file-size budget is "under 500 lines, with 350 as the goal" (`README.md:417-424`).

## Identity card

| Field | Value | Evidence |
|---|---|---|
| Name | **PhenoShared** (former name: **PhenoAI**) | `README.md:1`; `docs/dossiers/HANDOFF-PHENOSHARED.md` |
| Repo | `KooshaPari/PhenoShared` (canonical origin; `KooshaPari/pheno` redirects; local clones often at `repos/pheno`) | `README.md:7-9`; `gh repo view` |
| Visibility | **PUBLIC** (not private, not archived) | `gh repo view KooshaPari/PhenoShared` -> `visibility: PUBLIC`, `isPrivate: false`, `isArchived: false` |
| Created | Repo created **2026-04-03** (GitHub `createdAt`); local history starts earlier at first commit `043003e9a`, 2026-03-17 ("Initial commit: workspace setup") | `gh repo view`; `git log --reverse` first entry |
| Last push | **2026-11-10** 05:20 UTC (GitHub `pushedAt`); newest local commit `ad667428b`, 2026-11-09 20:29 PT | `gh repo view`; `git log -1` |
| Commit under analysis | Basis `origin/main` @ `6ec4ae563`; working tree observed at `ad667428b` - "fix(campaign): stop 63 scripts depending on one machine's absolute home path", 2026-11-09 | `git log -1 ad667428b`; `git rev-parse origin/main` |
| Primary language | **Rust** (workspace edition 2021, MSRV 1.80, version `0.3.10`); companion TypeScript packages | `gh repo view` -> `primaryLanguage: Rust`; `Cargo.toml`; `PRD.md:3` |
| License | **MIT OR Apache-2.0** (GitHub reports the MIT license; repo ships `LICENSE-MIT` and `LICENSE-APACHE`) | `README.md:27`; `gh repo view` -> `licenseInfo.key: mit` |
| Lifecycle stage | **Active growth / mid-consolidation** - a production-grade foundation that absorbed several products; build last verified 2026-09-16, current build UNKNOWN | Source maturity verdict; `docs/dossiers/HANDOFF-PHENOSHARED.md` |
| Category | **Shared infrastructure / foundation monorepo** (not a user-facing product) | `README.md:3-4`; `docs/dossiers/HANDOFF-PHENOSHARED.md` |

## Problem and positioning

**Pain addressed** (`PRD.md:3`, verbatim): "`phenotype-shared` is a Rust workspace (with companion TypeScript packages) providing domain-agnostic, reusable infrastructure primitives for the Phenotype ecosystem. Each crate is independently consumable with no inter-crate dependencies. The workspace is the canonical location for shared infrastructure so that every Phenotype service can depend on the same battle-tested primitives rather than reinventing them."

**Why a monorepo** (`README.md:39-41`): "The workspace consolidates infrastructure, tooling, agent frameworks, connectors, compute-mesh IaC, and ecosystem governance that previously lived across many standalone repositories." Four co-located cross-org functions: shared Rust crates (`crates/`), reusable workflows (`.github/workflows/`, 84 files, called from other repos), shared composite actions (`.github/actions/`, 5), and shared docs (`docs/`, `handbook/` - Global Handbook, ADRs, absorption records, session artifacts).

**What it replaces:**
- The **many standalone repositories** it absorbed, with the trail recorded in `docs/ABSORPTION_INDEX.md` and `docs/absorption/` (33 per-project records); absorbed families include PhenoFabric, PhenoRegistry, PhenoInfra, PhenoGfx and FocalPoint.
- **Hand-wired adapters:** the substrate facade means consumers "depend on one facade instead of wiring adapters by hand" (`README.md:49-56`).
- **Parallel reimplementations:** governance requires checking whether an existing crate already covers a cross-domain dependency, and "the workspace prefers extending an adapter over a new parallel implementation" (`README.md:417-424`).
- **Reinvented primitives:** services are meant to depend on "the same battle-tested primitives rather than reinventing them" (`PRD.md:3`).

**Positioning caveat:** the PRD's "no inter-crate dependencies" claim contradicts the actual substrate spine, where `substrate` depends on `substrate-core` and `substrate-app` depends on core ports (`README.md:57-70`).

