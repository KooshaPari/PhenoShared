# Security Policy

HeliosCLI takes the security of its users, their data, and the surrounding ecosystem
seriously. This document explains how to report a vulnerability, what to expect, and
which versions we currently support.

## Reporting a Vulnerability

**Please do not file public issues for suspected security vulnerabilities.**

Report privately via one of the following channels, in order of preference:

1. **GitHub Security Advisories**: <https://github.com/KooshaPari/HeliosCLI/security/advisories/new>
2. **Email**: <security@phenotype.dev> (PGP key available on request)
3. **Direct DM** to the maintainer: [@kooshapari](https://github.com/kooshapari)

Please include:

- A clear description of the issue and its impact.
- Steps to reproduce, ideally with a minimal test case or `helios --version` output.
- The commit SHA, tag, or release affected.
- Your contact details for follow-up.

We acknowledge new reports within **3 business days** and aim to provide a triage
decision within **10 business days**.

## Supported Versions

| Version                          | Status             | Security fixes             |
| -------------------------------- | ------------------ | -------------------------- |
| `main`                           | Active development | Yes                        |
| Latest tagged release (`v*.*.*`) | Supported          | Yes                        |
| Older releases                   | Best effort        | At maintainer's discretion |

HeliosCLI is currently published from the `main` branch; we strongly recommend
running the latest commit on `main` or the most recent tagged release.

## Coordinated Disclosure

We follow a 90-day coordinated disclosure window. We will:

- Confirm the report and assign a CVE ID (via GitHub Security Advisories).
- Develop, review, and ship a fix in a private fork.
- Credit the reporter (unless anonymity is requested) in the release notes.
- Publish the advisory and CVE details once a fix is available or the 90-day
  window expires, whichever comes first.

If a reported issue is already publicly known, or if the reporter fails to engage
in good faith during the disclosure window, we may release a fix and advisory
on our own schedule.

## Security Tooling

The following tooling runs on every push and pull request:

- `cargo check --workspace` and `cargo clippy --all-targets -- -D warnings`
- `cargo test --all`
- `cargo fmt --all -- --check`
- `cargo-audit` (RustSec advisory database) — see
  `codex-rs/.github/workflows/cargo-audit.yml`
- `cargo-deny` (licenses, advisories, bans, sources) — see `deny.toml`
- OpenSSF Scorecard (SARIF results uploaded via the CodeQL action) — see
  `.github/workflows/scorecard.yml`

Supply-chain hardening:

- All third-party GitHub Actions are pinned by SHA.
- Release artifacts are attested with SLSA Build provenance by the `attest`
  job in `.github/workflows/rust-release.yml`
  (`actions/attest-build-provenance@v2.1.0` over the release artifacts).
- Dependency updates run through Renovate (grouped, automerged, vulnerability
  alerts) — see `renovate.json`. There is no `.github/dependabot.yml`.

## Out of Scope

The following are not considered security vulnerabilities in HeliosCLI:

- Issues in upstream crates we vendor verbatim from `openai/codex`
  (`codex-rs/`) — please report these to the upstream project.
- Issues in third-party `codex-rs` extensions that run untrusted code.
- Self-inflicted damage from running `helios exec` with elevated approvals.

## Acknowledgements

We thank all security researchers and contributors who report issues responsibly.
Past reporters are credited in the relevant GitHub Security Advisories.
