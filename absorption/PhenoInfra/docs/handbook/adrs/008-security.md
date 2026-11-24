# ADR-008: Security Architecture

## Status

**Accepted** — 2026-05-25

## Author

KooshaPari

## Context

Phenotype repos contain Rust crates with transitive dependency trees, TypeScript packages, secrets that could accidentally be committed, and third-party GitHub Actions. We need automated, consistent security scanning that runs in CI on every push without requiring manual review steps, covering the primary attack surfaces: leaked secrets, vulnerable dependencies, and license violations.

## Decision

We adopt a three-tool security baseline that runs in every repo's GitHub Actions pipeline:

| Tool | Scope | Gate |
|------|-------|------|
| **TruffleHog** | Secret / credential scanning across git history | Block merge on any high-confidence finding |
| **cargo-deny** | Rust dependency audit (CVEs, licences, duplicate crates) | Block merge on advisory or licence violation |
| **Dependabot** | Automated dependency version PRs (Rust + npm) | Auto-opens PRs; merges after CI green |

TruffleHog provides deep git-history scanning that catches secrets even in old commits, which is critical when repos are made public. `cargo-deny` is a Rust-native tool that enforces CVE advisories from the RustSec database and licence allow-lists in a single `deny.toml`; it is faster and more accurate than generic SCA tools for Rust codebases. Dependabot closes the loop by automatically proposing upgrades when advisories are published, reducing the window between disclosure and remediation.

## Consequences

### Positive
- CI blocks merges on secret leaks and known CVEs before they reach main
- `deny.toml` is checked into each repo — licence policy is explicit and auditable
- Dependabot PRs keep dependency graphs fresh with minimal manual effort

### Negative / Trade-offs
- TruffleHog has a false-positive rate that may require per-repo allowlist tuning
- `cargo-deny` only covers Rust; npm/Python dependency audits rely on Dependabot and npm audit
- Dependabot noise can be high on projects with many transitive deps; batch-update config required

## References

- [trufflehog.yml](../trufflehog.yml) — org-level TruffleHog configuration
- ADR-005 — Auth Strategy (Firepass credential hygiene is complementary)
- ADR-006 — Deployment (GitHub Actions is the pipeline that runs all three tools)

---

*Decision Date: 2026-05-25*
*Next Review: 2027-05-25*
