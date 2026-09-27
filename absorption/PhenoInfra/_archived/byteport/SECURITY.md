# Security Policy

> BytePort security policy and operational tooling index. This document is
> the single entry point for anyone wanting to (a) report a vulnerability,
> (b) understand the threat model, or (c) audit the supply-chain posture.

## Supported Versions

Latest `main` branch is the only supported version. Older releases are not
patched; users on older versions are encouraged to upgrade.

## Threat Model

The current per-component STRIDE threat model lives at
[`docs/security/threat-model.md`](docs/security/threat-model.md). It enumerates
the production attack surface (SvelteKit frontend, Tauri shell, Go backend,
`nvms` orchestrator, LLM providers, AWS, CI/CD pipeline) and the mitigations
in place today.

**Review cadence:** on every minor release, on any new external dependency,
and quarterly at minimum.

## Reporting Vulnerabilities

Please report security vulnerabilities via GitHub Security Advisories:

- Open a [private security advisory](../../security/advisories/new)
- For sensitive issues, contact the repository owner directly

We follow **coordinated disclosure**: once an issue is patched, an advisory
will be published and the reporter credited.

## Automated Security Tooling

All checks below are enforced in CI. PR-gating checks must pass before merge;
weekly checks provide defense-in-depth on a staggered schedule.

### PR-gating (runs on every PR to `main`)

| Workflow | Job(s) | Purpose |
|----------|--------|---------|
| [`ci.yml`](.github/workflows/ci.yml) | `go-ci`, `rust-ci`, `frontend-ci` | Build + test gates |
| [`deny.yml`](.github/workflows/deny.yml) | `cargo-deny`, `gomod-check` | License / advisory / source compliance |
| [`security-scan.yml`](.github/workflows/security-scan.yml) | `gitleaks`, `cargo-audit` | Secret scan + RustSec advisories |

### Weekly audits (staggered to avoid thundering herd)

| Workflow | Schedule (UTC) | Purpose |
|----------|----------------|---------|
| [`audit.yml`](.github/workflows/audit.yml) | Mon 04:17 / Wed 05:37 / Sat 03:17 | CodeQL (actions/go/js), Gitleaks, TruffleHog, cargo-audit, cargo-semver-checks, **npm audit (frontend/web)**, **govulncheck (Go backends)**, SonarCloud, legacy-tooling scan |
| [`deny.yml`](.github/workflows/deny.yml) | Mon 09:00 (cargo-deny) / Wed 11:00 (gomod-check) | Drift-free license/advisory floor |
| [`scorecard.yml`](.github/workflows/scorecard.yml) | weekly | OpenSSF Scorecard mirror |

### On-demand / manual

- [`sbom.yml`](.github/workflows/sbom.yml) — CycloneDX SBOM generation
- `release-attestation.yml` / `release-attest.yml` — SLSA-style provenance

### Dependency automation

[`.github/dependabot.yml`](.github/dependabot.yml) opens weekly PRs:

| Ecosystem | Day | Scope |
|-----------|-----|-------|
| `cargo` | Monday | Root workspace + nested crates |
| `npm` | Tuesday | `frontend/web` |
| `gomod` | Wednesday | `backend/byteport`, `backend/nvms` |
| `github-actions` | Thursday | `.github/workflows/**` |
| `docker` | Friday | `Dockerfile*` |

Minor and patch updates are batched into `minor-and-patch` groups; major
updates are isolated for review.

## Local Reproduction

All CI checks can be reproduced locally via the [`justfile`](justfile):

```bash
just build    # Rust + Go + SvelteKit
just test     # cargo test + go test + npm test
just lint     # cargo clippy + go vet + npm run lint
just ci       # build + test + lint + fmt + deny + audit
just audit    # cargo-audit + cargo-semver + gitleaks + trufflehog
just deny     # cargo-deny
```

## Local govulncheck / npm-audit

```bash
# Go (byteport is the primary backend)
cd backend/byteport && go install golang.org/x/vuln/cmd/govulncheck@latest && govulncheck ./...

# Frontend (npm — package-lock.json present)
cd frontend/web && npm ci && npm audit --audit-level=high
```

## Secret Scanning

Two independent scanners run on every PR and weekly:

- **Gitleaks** — pattern-based, high recall (`.gitleaks.toml` ruleset)
- **TruffleHog** — verified-secrets only (entropy + endpoint verification)

If either scanner fires, the PR is blocked until the secret is rotated and
removed from history.

## Disclosure Policy

We follow coordinated disclosure with reporters:

1. Reporter opens a private advisory.
2. Maintainer triages within 72h.
3. Patch is developed on a private branch.
4. Advisory is published alongside the fix release.
5. Reporter is credited in the advisory.

## Contact

For non-sensitive security questions, open a public issue with the
`security` label. For sensitive disclosures, use the private advisory
mechanism above.
