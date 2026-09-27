# Security Policy — phenotype-infra

## 1. Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| latest  | :white_check_mark: |
| < latest| :x:                |

Only the latest tagged release receives security updates. Older versions are not patched; please upgrade.

## 2. Reporting a Vulnerability

Do **not** open public issues for security vulnerabilities in `phenotype-infra`
(infrastructure configs, IaC, tunnel/DNS topology, runbooks, or any crate in
this workspace). Report them privately:

- **Email:** kooshapari@kooshapari.com
- **GitHub:** Open a private security advisory via the Security tab on this repository
- **DO NOT** open a public issue, PR, or discussion for security vulnerabilities
- **DO NOT** disclose the vulnerability publicly until we have issued a fix and an advisory

Please include:

- A description of the vulnerability (e.g. leaked credential pattern, exposed
  service, privilege escalation path, misconfigured firewall/ACL, memory safety
  issue in native code, or supply-chain risk).
- Steps to reproduce.
- Potential blast radius (which node, which provider, which tenant data).
- Any suggested mitigations.

We aim to acknowledge new reports within **3 business days** and to issue a fix
or mitigation within **30 days** for critical issues.

## 3. Vulnerability Disclosure Process

1. **Report received** — maintainer acknowledges and assigns a CVE-style tracking ID.
2. **Triage** — severity assessed (Critical / High / Medium / Low) using CVSS 3.1.
3. **Patch development** — fix authored in a private fork; CI validates the fix.
4. **Coordinated disclosure** — embargo window negotiated (default 90 days from report).
5. **Public advisory** — GitHub Security Advisory + CVE assignment + release notes.

## 4. Security Update Cadence

- **Critical / High:** patch release within 7 days; GHSA published simultaneously
- **Medium:** patch release within 30 days
- **Low:** bundled into next regular release

## 5. Scope

**In scope:**

- The `phenotype-infra` source tree on the default branch
- Tagged releases on the default branch
- Pre-built artifacts published from CI (crates.io, Docker images, Go modules)
- IaC definitions (Terraform modules, Ansible playbooks, Cloudflare/Tailscale topology)
- Runbooks and incident-response playbooks under `docs/governance/`

**Out of scope:**

- Issues in transitive dependencies — report upstream
- Application secrets — those live in Vaultwarden and are injected at apply time
- Issues requiring physical access to the user's machine
- Denial-of-service via resource exhaustion in user-supplied inputs (best-effort mitigation only)

## 6. Security Tooling

This repository runs the following security tooling on every push and weekly cron:

- `cargo audit` — Rust dependency CVE scanning
- `gitleaks` — secret detection (`.gitleaks.toml` allowlists known false positives)
- `trufflehog` — additional secret scanning
- `trivy` — filesystem and container vulnerability scanning
- `codeql` — static analysis for Rust, Go, TypeScript
- `cargo-deny` — license and advisory checking
- SLSA provenance attestation for releases

See `.github/workflows/` for the full CI configuration:
- `audit.yml` — scheduled dependency auditing
- `cargo-deny.yml` — deny-check workflow
- `codeql.yml` — CodeQL analysis
- `scorecard.yml` — OpenSSF Scorecard
- `trufflehog.yml` — secret leak detection
- `quality-gate.yml` — pre-merge gate

## 7. Dependencies and Supply Chain

- Rust dependencies pinned via `Cargo.lock`
- Go dependencies pinned via `go.sum`
- `dependabot.yml` configured for security-only updates
- `cargo deny` enforces advisory allow/deny policies via `deny.toml`
- SBOMs are generated on every release
- SLSA Build Level 3 provenance attestation via `slsa-github-generator`

## 8. Secrets and PII Handling

Do not commit raw session dumps, provider console exports, credentials, or
files that may contain personal data. Use sanitized operational notes that
preserve decisions, alert numbers, paths, and remediation status without
including token values, account identifiers, IP addresses, or personal content.

This repository holds **declarative infrastructure** only — application secrets
live in Vaultwarden and are injected at apply time.

**Credential exposure procedure:**

1. Contain public access and automation execution.
2. Revoke or rotate exposed credentials at the provider.
3. Preserve a sanitized alert inventory and evidence trail in `docs/audit/`.
4. Remove exposed material from retained refs (use `git filter-repo` if needed).
5. Request cache/unreachable-object purge from GitHub where applicable.
6. Restore public access or automation only after scans and provider evidence
   prove the incident is closed.

## 9. Acknowledgements

We thank the security researchers and contributors who report vulnerabilities
responsibly.

---

See `docs/governance/security-policy.md` for the full token and SSH rotation
policy, and `docs/governance/incident-response.md` for outage playbooks.
