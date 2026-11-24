# Branch protection verification

SessionLedger expects GitHub **branch protection** (or equivalent rulesets) on
`main` so merges require a pull request and signed commits. This document covers
the **machine-verify** path only.

Maintainer **2FA** / org hardware-key policy is **not** asserted here and cannot
be proven from repository contents or this script.

## Maintainer checklist (Settings)

Configure **Settings → Branches → Branch protection rules → `main`** (or a
repository ruleset targeting `main`):

- [ ] **Require a pull request before merging**
- [ ] **Require signed commits**
- [ ] **Do not allow bypassing the above settings** (recommended)
- [ ] **Require status checks to pass** (recommended; pin required jobs)

## Machine verification

[`scripts/branch-protection-check.ps1`](../../scripts/branch-protection-check.ps1)
queries the GitHub REST API via `gh api`:

```text
GET /repos/{owner}/{repo}/branches/{branch}/protection
```

Run locally:

```powershell
# Best-effort: skip (exit 0) when gh/token/admin scope is unavailable
pwsh -NoProfile -File scripts/branch-protection-check.ps1

# Optional: fail when the API is readable but core controls are missing
pwsh -NoProfile -File scripts/branch-protection-check.ps1 -Strict
```

### Soft-fail behavior

| Condition                                            | Default exit              | Notes                                        |
| ---------------------------------------------------- | ------------------------- | -------------------------------------------- |
| `gh` missing                                         | 0 (SKIP)                  | Install GitHub CLI or use CI job             |
| No `GH_TOKEN` / `GITHUB_TOKEN` and `gh auth` missing | 0 (SKIP)                  | Export a token with admin read on protection |
| HTTP 401/403 (insufficient scope)                    | 0 (SKIP)                  | Classic protection API needs admin           |
| HTTP 404 "Branch not protected"                      | 0 (SKIP)                  | Enable protection; `-Strict` exits 1         |
| API OK, core controls present                        | 0 (PASS)                  | Signatures + PR reviews required             |
| API OK, core controls missing                        | 0 soft / 1 with `-Strict` | Docs-only soft path for OSS CI               |

Core controls for PASS: **required signatures** and **required pull request
reviews**. `enforce_admins` and required status checks are reported but not
required for the soft PASS.

## CI workflow

[`.github/workflows/branch-protection.yml`](../../.github/workflows/branch-protection.yml)
runs the script on path-filtered PRs/pushes and `workflow_dispatch`. The job uses
`continue-on-error` for fork pull requests so missing tokens do not block
contributor CI. On the canonical repo the script itself remains best-effort
unless maintainers pass `-Strict` manually.

`GITHUB_TOKEN` in Actions usually **cannot** read classic branch protection
without elevated permissions; treat CI as advisory evidence that the script runs,
not as proof that Settings are correct.

## PolicyOnly (hermetic hook)

[`scripts/branch-protection-check.ps1`](../../scripts/branch-protection-check.ps1)
`-PolicyOnly` validates in-repo source-provenance policy anchors (signed commits,
CODEOWNERS, human org gate rows) without calling the GitHub API. Use it in CI or
local smoke when tokens are unavailable:

```powershell
pwsh ./scripts/branch-protection-check.ps1 -PolicyOnly
```

See [`source-provenance.md`](source-provenance.md) (C06 L59 SSOT).

## Related

- [Protected environment policy (SLSA Build L3)](slsa-protected-environment.md) — GitHub Environments + release gate SSOT (C06 L53)
- [Source provenance policy](source-provenance.md) — signed commits + CODEOWNERS + org gates SSOT
- [Commit signing ops](commit-signing.md) — tip signature check + soft checklist
- [ADR 0004](../adr/0004-commit-signing-policy.md) — signed-commit policy
- [SECURITY.md](../../SECURITY.md) — supply-chain index
