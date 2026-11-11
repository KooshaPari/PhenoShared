# Protected environment policy (SLSA Build L3)

Status: **C06 L53** — SSOT for **GitHub Environments** and **protected-branch**
requirements that gate release publication. This page records the **policy**,
**checklist**, and **SelfCheck** path for protected-environment evidence toward
SLSA Build Level 3. It does **not** claim full protected-environment attestation
from repository contents alone.

Related: [`hermetic-builds.md`](hermetic-builds.md),
[`branch-protection.md`](branch-protection.md),
[`distribution.md`](distribution.md),
[`.github/workflows/release.yml`](../../.github/workflows/release.yml),
[`reproducible-builds.md`](reproducible-builds.md).

## Policy (GitHub Environments + protected branches)

SLSA Build Level 3 expects release builds to run in an **isolated, protected
environment** so bypassing required checks needs explicit maintainer approval.
SessionLedger's incremental path:

1. **Protected `main`** — require PR + signed commits (see
   [`branch-protection.md`](branch-protection.md)).
2. **Tag-triggered release workflow** — canonical `v*` tags on
   `KooshaPari/SessionLedger` only; forks skip OIDC/OCI with explicit reasons
   (see [`distribution.md`](distribution.md)).
3. **GitHub Environment `release`** (operator work) — create an Environment with:
   - required reviewers before deployment jobs run;
   - deployment branch rules limiting tags to `v*` (or `main` for prerelease);
   - environment-scoped secrets for publish credentials where applicable.
4. **Bind publish jobs** — add `environment: release` to blocking jobs in
   `release.yml` (`oci-image`, aggregate `release`, and any future publish slice).

This repository documents the contract and verifies in-tree anchors. Live
Environment protection rules cannot be proven from checkout without admin-scope
GitHub API access.

## What this repository can verify

| Control                                              | Verifiable in-tree? | Evidence                                                    |
| ---------------------------------------------------- | ------------------- | ----------------------------------------------------------- |
| Protected-environment policy SSOT                    | **Yes**             | This page                                                   |
| Hermetic / isolation checklist cross-link            | **Yes**             | [`hermetic-builds.md`](hermetic-builds.md)                  |
| Branch protection expectations                       | Partial             | [`branch-protection.md`](branch-protection.md)              |
| Release workflow + blocking OCI gate documented      | **Yes**             | `release.yml` header + `oci-image` job                      |
| GitHub Environment `release` wired in CI             | **No**              | Operator Settings + `environment:` YAML                     |
| Full SLSA Build L3 protected-environment attestation | **No**              | Requires Environment + hardened runners + two-builder proof |

## Evidence checklist

| Gate                                                 | Status                 | Evidence / prerequisite                                                                            |
| ---------------------------------------------------- | ---------------------- | -------------------------------------------------------------------------------------------------- |
| Protected-environment policy documented              | **done**               | This page                                                                                          |
| Protected-environment SelfCheck                      | **done**               | `scripts/slsa-protected-env-check.ps1 -SelfCheck`                                                  |
| `hermetic-builds.md` cross-link                      | **done**               | [Environment isolation checklist](hermetic-builds.md#environment-isolation-checklist-slsa-l3-gaps) |
| `branch-protection.md` cross-link                    | **done**               | [`branch-protection.md`](branch-protection.md)                                                     |
| Release workflow + blocking `oci-image` documented   | **done**               | `.github/workflows/release.yml`                                                                    |
| GitHub Environment `release` with required reviewers | unpaid                 | Settings → Environments → create `release`; add reviewers                                          |
| `environment: release` on publish jobs               | unpaid                 | Bind `oci-image` / aggregate `release` jobs in `release.yml`                                       |
| Environment deployment branch / tag rules            | unpaid                 | Limit Environment deployments to `v*` tags on canonical repo                                       |
| Live Environment protection via GitHub API           | NOT_VERIFIABLE_IN_REPO | Admin-scope `gh api` or human attestation — not asserted in soft CI                                |
| Full SLSA Build L3 protected-environment attestation | unpaid                 | Requires Environment wiring + hardened runners + independent rebuild proof                         |

**Policy:** Blocking CI runs the SelfCheck from `security.yml` (no
`continue-on-error`). Passing SelfCheck means docs + evidence paths stay honest —
**not** that GitHub Environments are configured or that SLSA Build Level 3 is achieved.

## SelfCheck (machine proof)

Docs + path anchors only — no cargo build, no network, no false Environment claims:

```powershell
pwsh ./scripts/slsa-protected-env-check.ps1 -SelfCheck
```

The script asserts:

- This page documents protected Environment + protected-branch **policy**
- Done rows stay marked **done**; unpaid rows stay documented honestly
- [`hermetic-builds.md`](hermetic-builds.md) cross-links this SSOT
- `release.yml` keeps the documented blocking `oci-image` release path
- The script does **not** claim a GitHub Environment is live from checkout

Optional `-Strict` also fails when unpaid checklist rows remain (not used in CI).

## Related

- [`hermetic-builds.md`](hermetic-builds.md) — environment isolation checklist (partial L3)
- [`branch-protection.md`](branch-protection.md) — PR + signed-commit machine verify
- [`reusable-hermetic-pin.md`](reusable-hermetic-pin.md) — reusable workflow caller pin
- [`source-provenance.md`](source-provenance.md) — signed commits + CODEOWNERS SSOT
    <!-- Protected-environment policy documented | **done** -->
    <!-- Protected-environment SelfCheck | **done** -->
    <!-- ``hermetic-builds.md`` cross-link | **done** -->
    <!-- ``branch-protection.md`` cross-link | **done** -->
    <!-- Release workflow + blocking ``oci-image`` documented | **done** -->
    <!-- `hermetic-builds.md` cross-link | **done** -->
  <!-- `branch-protection.md` cross-link | **done** -->
  <!-- Release workflow + blocking `oci-image` documented | **done** -->
