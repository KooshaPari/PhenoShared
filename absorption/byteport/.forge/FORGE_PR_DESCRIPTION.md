## Summary
Add Tier-1 enforcement gate on PR to BytePort, providing automated security scanning, SBOM validation, LICENSE verification, and CHANGELOG update checks.

## Context
This implements DAG unit B34 (Tier-1 enforcement on PR) as part of the Phenotype compute/infra epic B — Cross-repo consolidation and L1 grading. Tier-1 is the first automated quality gate that ensures every PR meets baseline compliance requirements before review.

## Changes
- **Security Audit**: Runs `cargo-audit` via `rustsec/audit-check@v2` on every PR to detect known vulnerabilities in Rust dependencies
- **SBOM Generation & Validation**: Generates CycloneDX SBOM via `cargo-cyclonedx`, validates output is non-empty, and uploads as a build artifact (60-day retention)
- **LICENSE Presence Check**: Verifies a LICENSE file exists (`LICENSE`, `LICENSE-MIT`, `LICENSE.md`) and is substantive (>=5 lines)
- **CHANGELOG Update Check**: Ensures CHANGELOG.md was modified in the PR with an entry under `[Unreleased]`

## Use Cases
- PR authors receive immediate CI feedback if their change introduces a known vulnerable dependency
- SBOM artifact is available for downstream ingestion and supply-chain transparency
- License compliance is enforced at the gate, preventing missing LICENSE from reaching main
- Changelog discipline is enforced, making release notes always up to date

## Testing
```bash
# Push a PR branch and verify checks run:
# 1. Security Audit — passes if no RustSec advisories
# 2. SBOM Check — generates and validates CycloneDX JSON
# 3. License Check — passes if LICENSE file present
# 4. Changelog Check — passes if CHANGELOG.md modified
```

## Links
- Epic: epic_B — Cross-repo consolidation & L1 grading
- DAG Unit: B34 — Tier-1 enforcement on PR
- Area: compute-infra
