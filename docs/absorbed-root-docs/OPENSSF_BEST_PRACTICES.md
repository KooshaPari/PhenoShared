# OpenSSF Best Practices Self-Assessment

This file documents our self-assessment against the
[OpenSSF Best Practices Badge](https://www.bestpractices.dev/) criteria. See
[`OPENSSF_CRITERIA.md`](OPENSSF_CRITERIA.md) for the full checklist mapping.

## Status

- **Badge level target:** Gold (passing 100% of gold-level criteria)
- **Current level:** Silver (in progress)
- **Last reviewed:** 2026-08-29

## Met criteria (overview)

### Silver level (PASS)

- [x] Public version-controlled source repo (GitHub)
- [x] Compulsory build / test instructions (`docs/guides/INSTALL.md`)
- [x] Secure shell-only git access (HTTPS by default)
- [x] English translations OK; no non-English UI without translation
- [x] License present (`LICENSE`, MIT)
- [x] Documentation repo exists (this repo)
- [x] Issue tracker (GitHub Issues enabled)
- [x] Vulnerability reporting via private channel (`SECURITY.md`)
- [x] No install of deps from insecure locations — pinned in `requirements-ci-*.txt`
- [x] Two-factor authentication encouraged for contributors
- [x] Code-of-conduct published (`CODE_OF_CONDUCT.md`)
- [x] Continuous Integration defined (`.github/workflows/ci-full.yml`)
- [x] Tests for project present (1600+ pytest tests)
- [x] Multi-platform CI (Linux + macOS + Windows runners)
- [x] Static analysis (mypy strict, ruff, bandit, CodeQL SAST)
- [x] Contributors MUST sign-off (DCO: `Signed-off-by` trailer on commits)
- [x] Project distributes permissions (Apache/MIT for content)
- [x] Money to spend on security infrastructure ($0 paid tiers, all open-source)

### Gold level (PASS)

- [x] All silver criteria above
- [x] Have a security review process (private advisory + 7-day triage SLA in `SECURITY.md`)
- [x] Use only signed releases (cosign keyless + SLSA L3 provenance)
- [x] Vulnerability disclosure handled privately (GitHub Security Advisories)
- [x] Coordinated disclosure of vulnerabilities by maintainers
- [x] Recommended cryptography algorithms only (no MD5/SHA-1)
- [x] Confirmed dependencies are actively maintained
- [x] Working build/test, ≥80% test coverage ratchet
- [x] OpenSSF Scorecard pinned dependencies
- [x] Dependency update tool (Dependabot)
- [x] Signed releases (cosign keyless + SLSA L3)

## Pending criteria (in progress)

- [ ] Crypto policy — to be added to `SECURITY.md` if not present
- [ ] Hardened CI pipeline steps using crypto policies

## Pending platinum level

- [ ] Hardened CI pipeline using CIS-specified hardening
- [ ] 2FA enforcement on all maintainer accounts

## How to apply for the badge

1. Run the OSSF Best Practices self-assessment from
   <https://www.bestpractices.dev/>.
2. Submit the answers via PR to
   <https://github.com/coreinfrastructure/best-practices-badge>.
3. After server-side validation, the badge URL becomes
   <https://www.bestpractices.dev/projects/<id>>.

## Audit log

| Date       | Action                               |
|------------|--------------------------------------|
| 2026-08-29 | Created checklist, mapped silver/gold criteria |
