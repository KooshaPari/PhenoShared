# G4: SLSA L3 on IaC Modules — Assessment Report

**Date:** 2026-06-24
**Unit:** G4
**Type:** slsa
**Epic:** epic_G — SOTA polish & external differentiation

## Assessment

Reviewed the IaC modules in `iac/` for SLSA L3 readiness. Key findings:

### Current State
- **Build integrity:** Rust workspace uses `Cargo.lock` pinned (committed), enabling reproducible builds
- **Provenance:** No SLSA provenance attestations (no `intoto` attestations, no `slsa-verifier` in CI)
- **Signed releases:** No GPG/cosign signing of build artifacts
- **Isolated build:** CI runs in ephemeral GitHub Actions runners (satisfies L3 isolation requirement)
- **Script dependencies:** Some shell scripts in `iac/scripts/` lack hash-pinned version references

### Recommendations
1. Add `slsa-github-generator` attestation step to CI workflow
2. Sign all release builds with cosign
3. Hash-pin all script dependencies
4. Add SLSA provenance badge to README

### SLSA Score
- **L1:** ✅ Build scripts defined, provenance requested
- **L2:** ✅ CI/CD with isolation
- **L3:** ❌ No signed attestations — requires workflow update
