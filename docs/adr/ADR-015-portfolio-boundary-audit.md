# ADR-015: Portfolio Boundary Audit and Code De-Duplication

**Status:** Accepted  
**Date:** 2026-09-13  
**Deciders:** KooshaPari, Jcode (agent)  
**Relates to:** REP-048, REP-059, REP-080, REP-010, REC-DEC-004

## Context

A cross-repo audit revealed embedded copies, forks, and duplicated code across
the Phenotype portfolio. Several repos contained full or partial copies of code
that already existed in canonical repositories, creating maintenance hazards and
boundary violations.

## Repos Audited

| Repo | Language | Boundary Status | Action Taken |
|------|----------|----------------|--------------|
| nanovms | Go | ✅ Clean — canonical runtime | None (source of truth) |
| PhenoCompose | Rust | ✅ Born unified with nanovms | None (intentional monorepo) |
| BytePort | Go + Svelte | ⚠️ Had embedded NVMS impl (67 files, 7,094 LOC) | **Ejected** via merge of `consolidate/B11-delete-nvms-impl` |
| thegent | Python + Rust | ⚠️ Embedded BytePort (612 files, 133K LOC) + FFI crate | **BytePort → git submodule**, FFI crate moved to nanovms |
| phenotype-infra | Go + Rust | ⚠️ Consolidation scaffold with copied code (7,558 LOC) | **Flagged** — scaffold contradicts REP-080 (IaC-only scope) |
| Eidolon | Rust | ✅ Clean — consumer via `sandbox-nanovm` feature flag | None |
| sharecli | Rust | ✅ Clean — standalone process runtime | None |
| NetWeave | — | ⚫ Does not exist on disk | None |
| localbase3 | — | ⚫ Does not exist on disk | None |
| hwLedger | — | ⚫ Does not exist on disk | None |

## What Was Fixed

### 1. BytePort NVMS Ejection (7,094 LOC removed)

BytePort contained `backend/nvms/` — an independent NVMS implementation
predating the nanovms repo by 16 months (2024-12-01 vs 2026-04-05). It was
not a fork but parallel code. Merged `consolidate/B11-delete-nvms-impl` into
main, deleted `backend/nvms/`, and updated README.

BytePort now calls the canonical nanovms API via `NANOVMS_URL`.

### 2. thegent BytePort Submodule Conversion (133K LOC deduplicated)

thegent contained `apps/byteport/` as a full embedded copy. Converted to a
git submodule pointing at `https://github.com/KooshaPari/BytePort.git`.
Updated `.gitmodules`, `.gitignore`, and AGENTS.md.

### 3. thegent-nvms FFI Crate Migration (441 LOC)

`crates/thegent-nvms/` (Rust FFI bindings to nanovms) was moved to
`nanovms/sdk/rust/thegent-nvms/` to co-locate with the runtime it binds to.
Removed from thegent workspace members.

### 4. CI Cleanup (4 workflow files)

Removed all `backend/nvms` references from BytePort CI:
- `.github/workflows/ci.yaml` — matrix entry + gofmt
- `.github/workflows/audit.yml` — govulncheck step + cache path
- `.github/workflows/tier-0-gate.yml` — gofmt line
- `.github/workflows/ci.yml` — gofmt line

### 5. thegent AGENTS.md Update

Removed stale `apps/byteport/` "Do Not Touch" rules (now a submodule).
Added `services/colab` submodule note.

### 6. thegent services/colab Submodule Removal

Uninitialized dead submodule removed from git index and `.gitmodules`.

## phenotype-infra Boundary Violation

**phenotype-infra** is a consolidation monorepo scaffolded to absorb nanovms,
PhenoCompose, and BytePort. It contains:

| Crate | LOC | Duplicates |
|-------|-----|------------|
| `crates/nanovms-core/` | 5,720 Go | Canonical nanovms repo |
| `crates/nvms-ffi/` + `crates/pheno-compose/` | 1,757 Rust | Canonical PhenoCompose |
| `tools/byteport/` | 81 Go + Svelte | Canonical BytePort |

**Per REP-080**, phenotype-infra should "Own shared IaC only; eject BytePort
back to its repo." The current scaffold contradicts this directive. The
consolidation approach was abandoned in favor of:

- nanovms as canonical runtime (Go)
- PhenoCompose as canonical FFI/driver (Rust, born unified)
- BytePort as canonical product (Go + Svelte, calls nanovms API)
- Eidolon as consumer (Rust, `sandbox-nanovm` feature flag)

**Recommended:** Archive or delete phenotype-infra crates that duplicate
canonical repos. Retain only IaC, ADRs, and shared infrastructure config.

## Decision

1. **Canonical ownership is settled.** Each component has one canonical repo.
2. **No more embedded copies.** Dependencies flow via git submodules, crate
   paths, or API calls — never copy-paste.
3. **phenotype-infra scope narrows.** Per REP-080, it owns IaC and shared
   infra only. Code consolidation crates should be archived.

## Consequences

- **Positive:** Single source of truth for each component. No more divergent
  copies. CI validates canonical code only.
- **Positive:** BytePort CI is now nvms-free and will pass cleanly.
- **Positive:** thegent no longer carries 133K LOC of embedded BytePort.
- **Risk:** phenotype-infra crates are now stale. Should be archived or
  deleted in a follow-up.
- **Risk:** Thegent has 28 GitHub vulnerabilities (2 critical) unrelated to
  this audit but worth triaging.
