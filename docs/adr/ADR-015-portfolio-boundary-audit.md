# ADR-015: Portfolio Boundary Audit and Code De-Duplication

**Status:** Accepted  
**Date:** 2026-09-13  
**Deciders:** <REDACTED>, Jcode (agent)  
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
| thegent | Python + Rust | ⚠️ Embedded BytePort (612 files, 133K LOC) + FFI crate + dead code (7,514 LOC) | **BytePort → git submodule**, FFI crate moved to nanovms, dead code deleted |
| phenotype-infra | Go + Rust | ⚠️ Consolidation scaffold with copied code (7,558 LOC) | **Archived** duplicate crates to `_archived/` per REP-080 (PR #192) |
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

### 7. thegent Dead Code Removal (7,514 LOC deleted)

- `sharecli/preserved/`: 25 dead files from archived projects (KWatch, KlipDot,
  KVirtualStage, KodeVibeGo, KodeVibe, KDesktopVirt)
- `crates/harness-native/`: migrated to canonical sharecli repo, already
  excluded from workspace; 20 .rs files removed
- `.archive/`: stale duplicate test/component files referencing dead byteport paths

### 8. phenotype-infra Duplicate Crate Archival (633 files moved)

Per REP-080 and this ADR, moved duplicate code to `_archived/`:
- `crates/nanovms-core` (5,720 LOC Go) → canonical: nanovms
- `crates/nvms-ffi` + `crates/pheno-compose` (1,757 LOC Rust) → canonical: PhenoCompose
- `tools/byteport` (Go + Svelte) → canonical: BytePort

PR: https://github.com/KooshaPari/phenotype-infra/pull/192

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
- **Positive:** thegent dead code removed (preserved/, harness-native/, .archive/).
- **Positive:** phenotype-infra duplicate crates archived to `_archived/`.
- **Resolved:** phenotype-infra scope now matches REP-080 (IaC + shared infra only).
- **Risk:** Thegent has 28 GitHub vulnerabilities (2 critical) unrelated to
  this audit but worth triaging.
