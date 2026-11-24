# G4 — SLSA L3 Assessment for IaC Modules

**Date:** 2026-06-25  
**Unit:** G4  
**Type:** slsa  
**Branch:** `slsa/G4-iac-slsa-l3`  
**Scope:** `iac/` workspace (Rust crates) + `iac/terraform/` (Terraform modules)

---

## 1. Summary

| Criterion | Status | Notes |
|-----------|--------|-------|
| **Build-as-scripted** (L1) | ✅ Pass | CI workflows, Makefile, Cargo workspace |
| **Version-controlled provenance** (L2) | ❌ Fail | No provenance/attestation generated |
| **Signed provenance** (L3) | ❌ Fail | No sigstore, cosign, witness, or in-toto |
| **Hermetic builds** (L3) | ❌ Fail | Network access unrestricted; no isolation |
| **Reproducible builds** (L3) | ❌ Fail | No reproducibility verification |
| **Branch protection** | ❌ Fail | `main` has no required PR reviews or status checks |
| **Signed commits** | ❌ Fail | No commit signing enforced |

**Overall SLSA Level: L1** (builds run as scripted, but no provenance artifact is generated)

---

## 2. Current State

### 2.1 IaC Rust Workspace (`iac/Cargo.toml`)

- Cargo workspace with 6 member crates + 1 excluded standalone
- CI via `.github/workflows/iac-rust.yml`:
  - `cargo check`, `cargo clippy`, `cargo test` with `--locked` (pinned deps via `Cargo.lock`)
  - Pinned action SHAs (good supply-chain hygiene)
  - Runs on `ubuntu-24.04` (deterministic runner)
- `Cargo.lock` is committed (enables reproducible dependency resolution)
- `deny.toml` bans unknown-registry sources

### 2.2 IaC Terraform Modules (`iac/terraform/`)

- Terraform providers pinned to specific version constraints
- All resource blocks **commented out** (scaffold only — no real provisioning)
- CI via `.github/workflows/terraform-plan.yml`:
  - `terraform fmt`, `terraform init -backend=false`, `terraform validate`
  - All runs on `ubuntu-24.04`
  - Backend not configured in CI (no credentials)

### 2.3 CI/CD Workflow Gaps

| Gap | Detail |
|-----|--------|
| **No SLSA generator** | No `slsa-github-generator` or similar attestation pipeline |
| **No provenance** | No `actions/attest-build-provenance` or `intoto` attestation |
| **No signing** | No cosign, sigstore, or GPG signing of build artifacts |
| **No SBOM generation** | No CycloneDX or SPDX SBOM creation for Rust binaries |
| **No hermetic isolation** | Builds have full network; no `actions/runner-docker` isolation |
| **No reproducibility check** | No `diffoscope` or rebuild comparison |
| **No signed commits** | Commits not signed; no `git verify-commit` enforcement |

### 2.4 Existing Security Tooling (positive signals)

| Tool | Benefit to SLSA |
|------|-----------------|
| `cargo-deny` | Validated dependency provenance (registry source bans) |
| OSSF Scorecard | Periodic supply-chain health scoring |
| CodeQL | Static analysis |
| TruffleHog | Secret detection |
| Pinned actions (SHA) | Prevents action substitution attacks |
| `Cargo.lock` committed | Pins transitive dependency graph |

---

## 3. SLSA L3 Requirements — Detailed Gap Analysis

### 3.1 Provenance Generation (L2 → L3)

**Requirement:** Build process generates a non-forgeable provenance attestation signed by the build platform.

**Current state:** No provenance generated. The `release.yml` workflow uploads artifacts via `actions/upload-artifact` but produces no attestation.

**Remediation path:**
1. Add `slsa-github-generator/go` workflow to generate signed provenance for Go builds
2. Add `slsa-github-generator/generic` for Rust binaries
3. Use `actions/attest-build-provenance` for GitHub-native attestation
4. Attest container images with cosign + keyless signing (sigstore)

### 3.2 Hermetic Builds (L3)

**Requirement:** Build runs without network access to external resources; all dependencies are pre-fetched and verified.

**Current state:** Builds have full network access. Cargo downloads crates from registries at build time.

**Remediation path:**
1. Pre-populate `CARGO_HOME` vendor directory with `cargo vendor`
2. Run builds in Docker containers with `--network=none`
3. Use `actions/cache` to restore vendored deps before build

### 3.3 Reproducible Builds (L3)

**Requirement:** Rebuilding from the same source at the same commit produces bit-for-bit identical output.

**Current state:** Not verified. Rust builds are mostly deterministic with `Cargo.lock`, but no verification step exists.

**Remediation path:**
1. Add CI job that rebuilds and diffs outputs
2. Set `RUSTFLAGS="-C link-arg=-Wl,--build-id=none"` for deterministic binary IDs
3. Strip timestamps via `REPRODUCIBLE_BUILD=1` convention

### 3.4 Branch Protection

**Requirement:** Changes to the build definition require PR review with two-party approval.

**Current state:** `main` branch has **no branch protection rules**. Direct pushes are possible.

**Remediation path:**
1. Enable branch protection on `main`:
   - Require pull request reviews (at least 1)
   - Require status checks (CI must pass)
   - Require signed commits
   - Restrict force pushes

---

## 4. Findings Register

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| G4-01 | **Critical** | No branch protection on `main` | Enable PR-required protection with status checks |
| G4-02 | **High** | No build provenance/attestation | Integrate `slsa-github-generator` or `actions/attest-build-provenance` |
| G4-03 | **High** | No artifact signing | Add cosign keyless signing for all release artifacts |
| G4-04 | **Medium** | Builds not hermetic | Vendor dependencies; isolate build network |
| G4-05 | **Medium** | No reproducibility checks | Add rebuild-diff step to CI |
| G4-06 | **Low** | No commit signing enforcement | Require GPG/SSH signed commits on `main` |
| G4-07 | **Low** | No SBOM generation | Add `cargo-cyclonedx` to release pipeline |

---

## 5. Scorecard Context

The existing OSSF Scorecard workflow runs weekly. A local `scorecard --show-details` run would provide specific badge scores. The assessment here covers SLSA-specific criteria beyond Scorecard's scope.

---

## 6. Next Steps

1. **Short-term (L2+):** Add `actions/attest-build-provenance` to the release workflow to generate signed provenance.
2. **Medium-term (L3):** Implement hermetic builds via `cargo vendor` + Docker `--network=none`.
3. **Long-term (L3):** Enable branch protection and signed commits on `main`.
4. **Tracking:** Each remediation should become a separate unit (G4.1, G4.2, etc.) in the DAG.

---

*Assessment prepared by Forge (DAG unit G4 execution).*
