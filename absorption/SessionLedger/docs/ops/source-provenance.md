# Source code provenance policy

Status: **C06 L59** — SSOT for **signed commits**, [`CODEOWNERS`](../../CODEOWNERS)
review gates, and **human org controls** (branch protection, maintainer 2FA) that
bind who may change SessionLedger source. This page records policy and
machine-verifiable anchors; it does **not** claim that GitHub org Settings are
provable from a git checkout alone.

Related: [`commit-signing.md`](commit-signing.md), [`branch-protection.md`](branch-protection.md),
[`CONTRIBUTING.md`](../../CONTRIBUTING.md), [`SECURITY.md`](../../SECURITY.md),
[`docs/adr/0004-commit-signing-policy.md`](../adr/0004-commit-signing-policy.md).

## Policy layers

| Layer             | Requirement                                            | In-repo evidence                                   |
| ----------------- | ------------------------------------------------------ | -------------------------------------------------- |
| DCO               | `Signed-off-by:` on each commit                        | [`CONTRIBUTING.md`](../../CONTRIBUTING.md)         |
| GPG / SSH         | Cryptographic signature on each commit reaching `main` | [`commit-signing.md`](commit-signing.md), ADR 0004 |
| CODEOWNERS        | Review from listed owners on owned paths               | [`CODEOWNERS`](../../CODEOWNERS)                   |
| Branch discipline | Feature branches + PRs; no direct push to `main`       | [`CONTRIBUTING.md`](../../CONTRIBUTING.md)         |
| Branch protection | Require signed commits + PR before merge on `main`     | Human org gate (see below)                         |
| Maintainer 2FA    | Org/account 2FA for Settings / merge access            | Human org gate (see below)                         |

Contributors must configure `commit.gpgsign` (GPG or SSH) **before** pushing.
DCO sign-off is complementary — it is **not** a substitute for GPG/SSH signatures.

## CODEOWNERS review gates

[`CODEOWNERS`](../../CODEOWNERS) assigns default ownership for the tree and
crate-specific paths. GitHub uses CODEOWNERS to request reviews from listed
handles when matching files change.

Maintainers should enable **Require review from Code Owners** on `main` when the
repository settings allow it. That toggle is a **human org gate** — this
repository documents the expectation but cannot assert the toggle from checkout.

## Signed commits (contributor + maintainer)

Operator setup, tip verification, and CI evidence live in
[`commit-signing.md`](commit-signing.md). Local checks:

```powershell
pwsh ./scripts/commit-signing-check.ps1 -Ref HEAD -Count 5
pwsh ./scripts/branch-protection-check.ps1 -PolicyOnly
```

Branch protection machine-verify (best-effort `gh api`, soft-skip without admin
scope): [`branch-protection.md`](branch-protection.md) +
[`scripts/branch-protection-check.ps1`](../../scripts/branch-protection-check.ps1).

## Human org gates (Settings)

These controls are **required policy** but **not** machine-verifiable from
repository contents:

| Control                                   | Why not in-tree?                                 | Maintainer action                        |
| ----------------------------------------- | ------------------------------------------------ | ---------------------------------------- |
| **Require signed commits** on `main`      | GitHub branch protection API needs admin scope   | Settings → Branches → `main`             |
| **Require a pull request before merging** | Same                                             | Same                                     |
| **Require review from Code Owners**       | Same                                             | Same (when CODEOWNERS is active)         |
| **Maintainer 2FA / hardware keys**        | GitHub does not expose per-user 2FA to this repo | Org/account Settings (human attestation) |

Record the date branch protection was enabled in an internal ops note. Do **not**
commit screenshots of GitHub Settings or 2FA enrollment.

## What this repository can verify

| Control                             | Verifiable in-tree?       | Evidence                                                 |
| ----------------------------------- | ------------------------- | -------------------------------------------------------- |
| Signed-commit policy SSOT           | **Yes**                   | This page + ADR 0004                                     |
| CODEOWNERS file present             | **Yes**                   | [`CODEOWNERS`](../../CODEOWNERS)                         |
| Recent `main` tip signature         | Partial                   | `scripts/commit-signing-check.ps1`                       |
| Branch protection doc anchors       | **Yes**                   | `scripts/branch-protection-check.ps1 -PolicyOnly`        |
| GitHub branch protection live state | Partial (best-effort API) | `scripts/branch-protection-check.ps1` (no `-PolicyOnly`) |
| Org 2FA / hardware-key enrollment   | **No**                    | Human attestation only                                   |

## Evidence checklist

| Gate                                         | Status                     | Evidence / prerequisite                                                                                  |
| -------------------------------------------- | -------------------------- | -------------------------------------------------------------------------------------------------------- |
| Source provenance policy documented          | **done**                   | This page                                                                                                |
| Source provenance SelfCheck                  | **done**                   | `scripts/source-provenance-check.ps1 -SelfCheck`                                                         |
| Branch protection PolicyOnly hook            | **done**                   | `scripts/branch-protection-check.ps1 -PolicyOnly`                                                        |
| CONTRIBUTING.md cross-link                   | **done**                   | [`CONTRIBUTING.md`](../../CONTRIBUTING.md) § Source provenance                                           |
| CODEOWNERS present                           | **done**                   | [`CODEOWNERS`](../../CODEOWNERS)                                                                         |
| GitHub **Require signed commits** live proof | **NOT_VERIFIABLE_IN_REPO** | Human org gate — enable in Settings; optional `gh api` via branch-protection-check without `-PolicyOnly` |
| Maintainer 2FA live proof                    | **NOT_VERIFIABLE_IN_REPO** | Human org gate — org/account 2FA attestation out-of-band                                                 |

## SelfCheck (machine proof)

Docs + path anchors only — no network, no GitHub API, no false org-gate claims:

```powershell
pwsh ./scripts/source-provenance-check.ps1 -SelfCheck
```

The script asserts:

- This page documents **signed commits**, **CODEOWNERS**, and **human org gates**
- Cross-links to `CONTRIBUTING.md`, `commit-signing.md`, and `branch-protection.md`
- The evidence checklist includes **NOT_VERIFIABLE_IN_REPO** human org rows
- `scripts/branch-protection-check.ps1` exposes `-PolicyOnly` for hermetic policy hooks

## Related

- [`branch-protection.md`](branch-protection.md) — PR + signed-commit machine verify
- [`commit-signing.md`](commit-signing.md) — contributor GPG/SSH setup + CI tip check
- [`docs/adr/0004-commit-signing-policy.md`](../adr/0004-commit-signing-policy.md) — decision record
  <!-- Source provenance SelfCheck | **done** -->
  <!-- Branch protection PolicyOnly hook | **done** -->
