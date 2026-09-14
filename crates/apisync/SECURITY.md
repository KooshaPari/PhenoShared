# Security Policy

## Reporting a Vulnerability

Apisync takes security seriously. If you discover a vulnerability, please
report it **privately** — do **not** open a public GitHub issue.

### Preferred: GitHub Private Vulnerability Reporting

Use the repository's **Security → Report a vulnerability** page
(https://github.com/KooshaPari/Apisync/security/advisories/new). Reports
land directly with the maintainers and are not visible publicly.

### Alternative: Email

You can also email the maintainers directly at
[security@apisync.dev](mailto:security@apisync.dev).

### What to include

- Affected version(s) and the commit/tag you tested
- Steps to reproduce (minimal example preferred)
- Impact and any suggested mitigation
- Your contact details if you want a follow-up

### What happens next

1. The maintainers will acknowledge the report within **5 business days**.
2. Assessment and a fix plan, with a target disclosure timeline, follow.
3. You'll be credited in the advisory unless you prefer to remain anonymous.

## Supported Versions

| Version | Supported         |
| ------- | ----------------- |
| 0.2.x   | ✅ Latest release |
| < 0.2.0 | ❌ Unsupported    |

## Security Posture

- **Supply chain**: dependency audits run on every push
  (cargo-deny advisories + licenses, rustsec/audit-check), plus daily
  Trivy and weekly OpenSSF Scorecard scans.
- **Secrets**: gitleaks scans every commit; trufflehog runs verified-secret
  scanning on the full history.
- **Static analysis**: CodeQL (Rust) runs on main and pull requests.
- **Releases**: SBOM (CycloneDX) attached to every GitHub Release; the
  crate on crates.io is built from the tagged commit.
