# A-07 Validation

## Files present
- [x] `.github/workflows/quality-gate.yml` — cargo check + go vet + rustfmt + lint
- [x] `.github/workflows/release.yml` — Go static lib + Rust release
- [x] `.github/workflows/audit.yml` — Trivy scanning (from nanovms)
- [x] `.github/workflows/scorecard.yml` — OSSF Scorecard (from nanovms)
- [x] `.github/codecov.yml` — coverage config (from nanovms)
- [x] `deny.toml` — cargo-deny license/advisory/bans

## CI checks
- [x] Quality gate covers Go (vet, lint, security) and Rust (cargo check, fmt)
- [x] Release builds both Go staticlib and Rust release artifacts
- [x] Trivy scans on push/PR/schedule
- [x] Scorecard runs weekly

## Git state
- [x] All files committed
- [x] CRLF warnings are cosmetic (Windows git)

**Status: PASS** — ready for A-08
