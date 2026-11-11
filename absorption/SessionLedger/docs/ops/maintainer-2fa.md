# Maintainer 2FA policy (org hygiene)

Status: **C04 L36** — maintainer SSOT for org/account **two-factor authentication**
(2FA) and hardware-key hygiene for everyone with merge or Settings access on
SessionLedger. This page records the **policy** and **human attestation** path;
it does **not** claim that org 2FA is machine-verifiable from repository contents.

Related: [`SECURITY.md`](../../SECURITY.md), [`CONTRIBUTING.md`](../../CONTRIBUTING.md),
[`branch-protection.md`](branch-protection.md), [`commit-signing.md`](commit-signing.md),
[`docs/adr/0004-commit-signing-policy.md`](../adr/0004-commit-signing-policy.md).

## Policy (org-level)

All maintainers listed in [`CODEOWNERS`](../../CODEOWNERS) and anyone with
**admin**, **maintain**, or **Settings write** on `KooshaPari/SessionLedger` must:

1. Enable **2FA** on their GitHub account (TOTP app or passkey).
2. Prefer a **hardware security key** (WebAuthn/FIDO2) as a registered 2FA factor
   or as GitHub's SAML/SSO second factor when the org adopts it.
3. Require **org-wide 2FA** under **Settings → Organizations → … → Authentication
   security** when the repo moves under a GitHub Organization (currently single-owner).

SessionLedger cannot prove these controls from a git checkout. GitHub does not
expose per-maintainer 2FA status to unprivileged API callers.

## What this repository can verify

| Control                           | Verifiable in-tree?            | Evidence                              |
| --------------------------------- | ------------------------------ | ------------------------------------- |
| Signed commits on `main`          | Partial (tip + history)        | `scripts/commit-signing-check.ps1`    |
| Branch protection                 | Partial (best-effort `gh api`) | `scripts/branch-protection-check.ps1` |
| Maintainer 2FA / org hardware-key | **No**                         | Human attestation only                |

## Human attestation process

When a maintainer confirms org/account 2FA (and hardware key where applicable):

1. Record **date**, **maintainer handle**, and **method** (TOTP + hardware key,
   passkey-only, org SAML + FIDO2, etc.) in your internal ops ledger (not in this
   public repo unless an audit package explicitly requests redacted evidence).
2. Org owner enables **Require two-factor authentication for everyone in the
   organization** before adding collaborators with Settings access.
3. Re-attest annually or when CODEOWNERS / admin roster changes.

Do **not** commit screenshots of 2FA settings or hardware-key serial numbers.

## Evidence checklist

| Gate                                        | Status                     | Evidence / prerequisite                                                                                                      |
| ------------------------------------------- | -------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Maintainer 2FA policy documented            | **done**                   | This page                                                                                                                    |
| Maintainer 2FA SelfCheck                    | **done**                   | `scripts/maintainer-2fa-check.ps1 -SelfCheck`                                                                                |
| SECURITY.md cross-link                      | **done**                   | [`SECURITY.md`](../../SECURITY.md) § Commit signing                                                                          |
| CONTRIBUTING.md cross-link                  | **done**                   | [`CONTRIBUTING.md`](../../CONTRIBUTING.md) § Maintainer 2FA                                                                  |
| Org 2FA + hardware-key enforcement          | **NOT_VERIFIABLE_IN_REPO** | Human attestation row — GitHub org/account 2FA cannot be confirmed from checkout; maintainer records attestation out-of-band |
| GitHub org "Require 2FA" toggle proof in CI | **unpaid**                 | No GitHub API exposes per-user 2FA to this repo's tokens                                                                     |

## SelfCheck (machine proof)

Docs + path anchors only — no network, no GitHub API, no false 2FA claims:

```powershell
pwsh ./scripts/maintainer-2fa-check.ps1 -SelfCheck
```

The script asserts:

- This page documents maintainer **2FA** + hardware-key **policy**
- Cross-links to `SECURITY.md` and `CONTRIBUTING.md`
- The evidence checklist includes a **NOT_VERIFIABLE_IN_REPO** human attestation row
- The script does **not** claim org 2FA is enforced from checkout

## Related

- [`branch-protection.md`](branch-protection.md) — PR + signed-commit machine verify (no 2FA claim)
- [`cve-feed-subscription.md`](cve-feed-subscription.md) — CVE feeds (2FA out of scope)
- [`sandbox-boundary.md`](sandbox-boundary.md) — process isolation (2FA out of scope)
<!-- Maintainer 2FA SelfCheck | **done** -->
