# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

Security fixes land on the latest release line first. Older tags are not backported unless a maintainer explicitly commits to a patch release.

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for security reports.

Preferred channels (in order):

1. **GitHub Security Advisories** ΓÇö [Report a vulnerability](https://github.com/KooshaPari/SessionLedger/security/advisories/new) on this repository.
2. **Email** ΓÇö contact maintainer **KooshaPari** via the address listed on their [GitHub profile](https://github.com/KooshaPari) (placeholder until a dedicated security inbox is published).

Include:

- Affected version / commit
- Reproduction steps or proof-of-concept
- Impact assessment (confidentiality / integrity / availability)
- Whether the issue is already public

## Disclosure Timeline

| Stage                        | Target                        |
| ---------------------------- | ----------------------------- |
| Initial acknowledgement      | within **3 business days**    |
| Triage / severity assessment | within **7 days** of report   |
| Fix or mitigation plan       | within **30 days** (typical)  |
| Public disclosure / advisory | coordinated after a fix ships |

We follow coordinated disclosure. If a fix cannot ship within 90 days, we will discuss interim guidance with the reporter before any public write-up.

Critical supply-chain or remote-code issues may be accelerated at maintainer discretion.

## Commit signing

- Every commit on `main` must carry a **GPG or SSH** signature in addition to DCO
  sign-off (see [`CONTRIBUTING.md`](CONTRIBUTING.md)).
- Policy and operator steps: [`docs/ops/commit-signing.md`](docs/ops/commit-signing.md);
  decision record: [`docs/adr/0004-commit-signing-policy.md`](docs/adr/0004-commit-signing-policy.md).
- CI runs [`scripts/commit-signing-check.ps1`](scripts/commit-signing-check.ps1) via
  [`.github/workflows/commit-signing.yml`](.github/workflows/commit-signing.yml) to
  verify the `main` tip is signed and to emit a branch-protection checklist.
  GitHub **Require signed commits** on `main` is the enforcement control; the
  checklist step is intentionally soft when admin API scope is unavailable in OSS.
- Branch protection machine-verify:
  [`scripts/branch-protection-check.ps1`](scripts/branch-protection-check.ps1) +
  [`docs/ops/branch-protection.md`](docs/ops/branch-protection.md) +
  [`.github/workflows/branch-protection.yml`](.github/workflows/branch-protection.yml)
  (best-effort `gh api`; soft-skip without admin token; fork PRs continue-on-error).
- Maintainer **2FA** policy SSOT:
  [`docs/ops/maintainer-2fa.md`](docs/ops/maintainer-2fa.md);
  hermetic proof: `pwsh ./scripts/maintainer-2fa-check.ps1 -SelfCheck`.
  Org/account 2FA is **not** attestable from this repository (human attestation
  only; see `NOT_VERIFIABLE_IN_REPO` row in the policy doc).

## Supply Chain & SBOM

- Dependency policy is enforced by [`deny.toml`](deny.toml) via `cargo deny check` (see [`.github/workflows/security.yml`](.github/workflows/security.yml)).
- Secret scanning runs with gitleaks and TruffleHog (dual-scan) in the same workflow on PRs and pushes to `main` (plus a weekly scheduled full scan). Gitleaks uploads SARIF to GitHub code scanning when `security-events` write is available. Local pre-commit hooks use gitleaks only.
- Dependency updates: [`renovate.json`](renovate.json) groups Cargo and GitHub Actions PRs and automerges **patch** (and Actions digest) updates after required CI checks pass. Weekly Dependabot ([`.github/dependabot.yml`](.github/dependabot.yml)) remains as a secondary CVE/update surface until Renovate is the sole bot. Prefer reviewing Renovate majors manually.
- CycloneDX SBOMs are produced in the qgate path as `target/sbom.cdx.json` and per-crate `*.cdx.json` artifacts (see [`.github/workflows/qgate.yml`](.github/workflows/qgate.yml) header comments). Packaging notes: [`packaging/README.md`](packaging/README.md).
- SBOM policy SSOT: [`docs/ops/sbom-policy.json`](docs/ops/sbom-policy.json) pins `cargo-cyclonedx` and documents validation via [`scripts/sbom-validate-check.ps1`](scripts/sbom-validate-check.ps1).

- Advisory scanning: `cargo audit` job in .github/workflows/security.yml.
- SBOM upload: qgate uploads `sbom-cyclonedx` artifact from `target/sbom.cdx.json`.
- CVE feed subscription (GHSA + OSV + NVD): maintainer process and evidence links in [`docs/ops/cve-feed-subscription.md`](docs/ops/cve-feed-subscription.md). Hermetic proof: `pwsh ./scripts/cve-feed-check.ps1 -SelfCheck`.
- Socket.dev supply-chain posture (optional org GitHub App complement): policy SSOT in [`docs/ops/socket-posture.md`](docs/ops/socket-posture.md). Hermetic proof: `pwsh ./scripts/socket-posture-check.ps1 -SelfCheck`. Live org install is **not** attestable from this repository.

## Cryptography inventory

SessionLedger uses **SHA-256 content hashing** (`sha2`) for dedup keys and
**operator-owned TLS** at a reverse proxy for remote-style daemon deploys. There
is **no encryption-at-rest** for OKF bundles or audit files and **no in-tree
KMS** — Phase-0 defers app-level envelope encryption to host FDE / ACLs / vault
injection. See the full inventory, TLS samples (Caddy/nginx), and KMS/at-rest
guidance in [`docs/ops/crypto-inventory.md`](docs/ops/crypto-inventory.md).
STRIDE-lite context: [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md).

## API keys and secret rotation

SessionLedger is a single-user local companion. Do not commit real secrets.

| Surface             | Guidance                                                                                                                                                                                                                           |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Local env sample    | Copy [`.env.example`](.env.example) into your shell or local env manager. Keep `SL_API_KEY` unset for default loopback trust, or set a local-only value outside the repo.                                                          |
| Optional write gate | When `SL_API_KEY` is set, mutating HTTP routes require `Authorization: Bearer …` or `X-API-Key: …`. Details: [`docs/ops/local-trust-boundary.md`](docs/ops/local-trust-boundary.md).                                               |
| Rotation            | Stop callers using the old key → replace `SL_API_KEY` in the daemon environment → restart `sl-daemon` → update automation headers. Treat the previous key as burned; do not reuse it.                                              |
| Repo hygiene        | Never put live keys in `.env.example`, docs, fixtures, or commits. CI runs [`scripts/env-example-check.ps1`](scripts/env-example-check.ps1) (required keys + no high-entropy secret patterns) and gitleaks/TruffleHog on the tree. |

## Privacy hygiene (single-tenant)

SessionLedger is a **single-user** local companion — not a multi-tenant hosted
service. Operator guidance for PII in logs, transcript retention, redaction
before export, and loopback trust lives in
[`docs/ops/privacy-hygiene.md`](docs/ops/privacy-hygiene.md). STRIDE-lite
disclosure context: [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md). Bind and
`SL_API_KEY` policy: [`docs/ops/local-trust-boundary.md`](docs/ops/local-trust-boundary.md).

Local verify:

```powershell
pwsh -NoProfile -File scripts/env-example-check.ps1
pwsh -NoProfile -File scripts/privacy-hygiene-check.ps1 -SelfCheck
pre-commit run gitleaks
```
