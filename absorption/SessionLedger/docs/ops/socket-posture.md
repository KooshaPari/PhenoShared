# Socket.dev supply-chain posture

Status: **C06 L33** complement — documents how SessionLedger aligns with
[Socket.dev](https://socket.dev) dependency-risk telemetry **alongside** in-repo
blocking scans (`cargo deny`, `cargo audit`, gitleaks, TruffleHog). Machine
proof: `pwsh ./scripts/socket-posture-check.ps1 -SelfCheck`.

Policy manifest: [`socket-posture.json`](socket-posture.json).

Related: [`SECURITY.md`](../../SECURITY.md),
[`cve-feed-subscription.md`](cve-feed-subscription.md),
[`.github/workflows/security.yml`](../../.github/workflows/security.yml),
[`deny.toml`](../../deny.toml).

## Layered controls

| Layer                         | Role                                                                  | Evidence in this repo                                                             |
| ----------------------------- | --------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| **In-repo blocking**          | Primary PR gate for Rust advisories + secrets                         | `cargo-deny`, `cargo-audit`, gitleaks, TruffleHog in `security.yml`               |
| **GHSA/OSV/NVD feeds**        | Maintainer triage beyond a single bot                                 | [`cve-feed-subscription.md`](cve-feed-subscription.md)                            |
| **Socket.dev (optional org)** | Supply-chain behavior scoring on PRs when the GitHub App is installed | Expected check names in `socket-posture.json`; **not** enforced by this SelfCheck |

SessionLedger does **not** embed a Socket API token or run Socket CLI in CI.
When the org installs the Socket GitHub App, PRs may show **Socket Security: Pull Request Alerts** and **Project Report** checks (third-party; informational unless branch protection requires them).

## Maintainer process

### 1. Keep in-repo scans green (required)

Every PR / push to `main` runs [`.github/workflows/security.yml`](../../.github/workflows/security.yml):

- `cargo deny check` — advisory policy from [`deny.toml`](../../deny.toml)
- `cargo audit` — RustSec / GHSA-backed advisories
- gitleaks + TruffleHog — secret scanning

Triage failures before merging; do not rely on Socket alone to waive deny/audit hits.

### 2. Optional Socket.dev GitHub App (org)

1. Org admin installs **Socket Security for GitHub** on `KooshaPari/SessionLedger`.
2. Confirm PR checks include the names listed in [`socket-posture.json`](socket-posture.json).
3. Review Socket alerts as **supplementary** signal (typosquatting, install scripts,
   risky postinstall) — cross-check against `cargo deny` / `cargo audit` before merge.
4. Record org install date in a maintainer note if branch protection later requires Socket checks.

### 3. When Socket is absent

In-repo `cargo-deny`, `cargo-audit`, Renovate/Dependabot, and
[`cve-feed-subscription.md`](cve-feed-subscription.md) remain the authoritative
dependency-risk surface. Absence of Socket checks is **not** a merge blocker
unless org policy adds them to required checks.

## SelfCheck gate

| Check                                 | Status                                  |
| ------------------------------------- | --------------------------------------- |
| `socket-posture-check.ps1 -SelfCheck` | **done** — docs + `security.yml` anchor |
| Live Socket API / org install         | **NOT_VERIFIABLE_IN_REPO**              |

Hermetic SelfCheck validates policy doc anchors, `SECURITY.md` cross-link,
`security.yml` job wiring, and complementary scan evidence paths. No network,
no Socket API token, no false claim of live org install.

## Done / unpaid

| Item                                     | Status                      |
| ---------------------------------------- | --------------------------- |
| Policy SSOT + JSON manifest              | **done**                    |
| Blocking `security.yml` SelfCheck job    | **done**                    |
| `tests/socket_posture.rs` cargo wrapper  | **done**                    |
| Live Socket org API automation           | **unpaid** — creds / org    |
| Branch-protection required Socket checks | **unpaid** — human Settings |
