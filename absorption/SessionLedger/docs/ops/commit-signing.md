# Commit signing operations

SessionLedger requires **cryptographic Git commit signatures** (GPG or SSH) on
every commit that reaches `main`, in addition to DCO `Signed-off-by:` trailers.
See [ADR 0004](../adr/0004-commit-signing-policy.md) for rationale and scope
(maintainer 2FA is explicitly out of scope here).

## Policy summary

| Layer         | Requirement                                 | Enforcement                             |
| ------------- | ------------------------------------------- | --------------------------------------- |
| DCO           | `Signed-off-by:` on each commit             | PR template + review                    |
| GPG / SSH     | Signature block on each commit object       | GitHub branch protection + CI tip check |
| Merge commits | GitHub signs merges as `noreply@github.com` | Automatic on squash/merge               |

## Contributor setup

### GPG (traditional)

```bash
gpg --full-generate-key
gpg --list-secret-keys --keyid-format=long
git config --global user.signingkey <KEY_ID>
git config --global commit.gpgsign true
```

Export the public key to GitHub → Settings → SSH and GPG keys → New GPG key.

### SSH (Git ≥ 2.34)

```bash
ssh-keygen -t ed25519 -C "signing@example.com" -f ~/.ssh/id_ed25519_sign
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519_sign.pub
git config --global commit.gpgsign true
```

Add the **public** key as a **Signing key** on GitHub (not only as an auth key).

### Verify before push

```bash
git log -1 --show-signature
# or
git verify-commit HEAD
```

## Maintainer: GitHub branch protection

Branch protection cannot be asserted from a bare git clone. Maintainers must
configure the following in **Settings → Branches → Branch protection rules → `main`**:

- [ ] **Require signed commits**
- [ ] **Require a pull request before merging** (recommended)
- [ ] **Do not allow bypassing the above settings** (recommended for admins)

Record the date protection was enabled in an internal ops note. Dedicated
machine-verify (best-effort `gh api`, skip without token/admin scope):
[`branch-protection.md`](branch-protection.md) and
`scripts/branch-protection-check.ps1`. The commit-signing checklist below remains
a soft companion when `gh` has admin scope.

## Machine verification

Run locally or in CI:

```powershell
# Blocking tip check + recent-history report (default CI mode)
pwsh -NoProfile -File scripts/commit-signing-check.ps1

# Hermetic bounded header scanner + fixtures (no signed main required)
pwsh -NoProfile -File scripts/commit-signing-check.ps1 -SelfCheck

# Branch-protection checklist (soft-fail / docs-only without admin API)
pwsh -NoProfile -File scripts/commit-signing-check.ps1 -BranchProtectionChecklist

# Strict: fail if any commit in the window lacks a signature block
pwsh -NoProfile -File scripts/commit-signing-check.ps1 -Strict -Count 50
```

### What the script checks

1. **`main` tip** — commit object contains a `gpgsig` block (GPG or SSH).
2. **Recent history** — for each of the last _N_ commits (default 30), classify
   as `gpg`, `ssh`, or `unsigned`.
3. **When signatures are present** — run `git verify-commit` when a verifier is
   available; malformed `gpgsig` blocks fail even in soft mode.
4. **Branch protection** (optional `-BranchProtectionChecklist`) — if `gh api`
   succeeds with admin scope, assert `required_signatures` on `main`; otherwise
   print the checklist above and exit 0 (OSS fail-soft).

### CI workflow

[`.github/workflows/commit-signing.yml`](../../.github/workflows/commit-signing.yml)
checks out full history (`fetch-depth: 0`), runs the script on PRs and `main`
pushes, and uploads the text report as a job summary.

## Interpreting GitHub merge signatures

Squash and merge commits are signed by GitHub's bot key. Individual commits inside
a PR may be unsigned until branch protection rejects them; only the merge commit
on `main` must be signed for the tip check to pass today.

Long term, **Require signed commits** ensures every commit in a PR is signed
before merge, not only the merge commit.

## Related documents

- [CONTRIBUTING.md](../../CONTRIBUTING.md) — DCO + signing setup for contributors
- [SECURITY.md](../../SECURITY.md) — supply-chain controls index
- [ADR 0004](../adr/0004-commit-signing-policy.md) — policy decision record
