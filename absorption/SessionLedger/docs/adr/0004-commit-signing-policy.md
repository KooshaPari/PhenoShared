# ADR 0004: Git commit signing policy (GPG / SSH)

- Status: Accepted
- Date: 2026-07-13
- Decision owners: SessionLedger maintainers
- Related: `docs/ops/commit-signing.md`, `CONTRIBUTING.md`, `SECURITY.md`, ADR 0003

## Context

SessionLedger is an open-source repository on GitHub. Supply-chain controls already
cover dependency advisories, secret scanning, SBOM emission, and signed Releases
(see ADR 0003). **Git commit signing** is a separate pillar: it binds each commit
object to a cryptographic identity so reviewers can detect tampering after push.

Today:

| Signal                                         | Status                                                   |
| ---------------------------------------------- | -------------------------------------------------------- |
| DCO `Signed-off-by:` trailers                  | Required in `CONTRIBUTING.md` (legal attestation)        |
| GitHub merge-commit PGP signatures             | Present on squash/merge commits via `noreply@github.com` |
| Contributor GPG/SSH signatures on every commit | **Not enforced in-repo**                                 |
| Branch protection "Require signed commits"     | **Not machine-verifiable without admin API access**      |

Maintainer **2FA** is an org/account control and is intentionally **out of scope**
for this ADR (see `SECURITY.md` maintainer hygiene, recorded separately).

OSS repositories cannot prove GitHub branch-protection settings from a checkout
alone. CI therefore combines:

1. **Machine checks** — inspect recent `main` history for GPG/SSH signature blocks
   and validate the tip commit is signed.
2. **Documented enforcement** — maintainers enable "Require signed commits" on
   `main` in GitHub Settings → Branches.
3. **Soft checklist** — `scripts/commit-signing-check.ps1 -BranchProtectionChecklist`
   prints required settings and queries the API only when `gh` + admin scope exist;
   otherwise it exits 0 with documentation pointers (fail-soft / docs-only).

## Decision

**All commits landing on `main` must carry a verifiable GPG or SSH signature.**
Enforcement is layered:

1. **Contributors** configure `git config commit.gpgsign true` (GPG) or
   `git config gpg.format ssh` + `user.signingkey` (SSH) before pushing.
2. **Maintainers** enable GitHub branch protection rule on `main`:
   - Require signed commits
   - (Recommended) Require pull request reviews before merging
3. **CI** runs `scripts/commit-signing-check.ps1` on PRs and `main` pushes:
   - **Blocking:** `main` tip commit must include a `gpgsig` block (GPG or SSH).
   - **Advisory:** recent-history coverage report; branch-protection checklist is
     soft-fail when the API is unreachable or lacks admin scope.

DCO sign-off (`git commit -s`) remains required and is **complementary** to
cryptographic signing — DCO is not a substitute for GPG/SSH.

### Accepted signature kinds

| Kind | Detection                                       | Notes                           |
| ---- | ----------------------------------------------- | ------------------------------- |
| GPG  | `gpgsig` block containing `BEGIN PGP SIGNATURE` | GitHub merge bot uses PGP       |
| SSH  | `gpgsig` block containing `BEGIN SSH SIGNATURE` | Git ≥ 2.34; no local gpg needed |

### Out of scope

- Maintainer 2FA / hardware-key attestation (org policy; not provable from git tree)
- Platform Authenticode / Apple notarization (ADR 0003)
- Re-signing historical unsigned commits (forward-only policy)

## Consequences

- `CONTRIBUTING.md` documents how contributors enable GPG or SSH signing.
- `SECURITY.md` cross-links commit-signing expectations for reporters and auditors.
- `docs/ops/commit-signing.md` is the operator runbook (setup, verification, checklist).
- CI provides auditable evidence without pretending branch protection is enforced
  when GitHub admin APIs are unavailable.

## Reconsider when

Revisit this policy if:

1. The project moves off GitHub or disables merge-queue signing, **or**
2. A verified incident shows unsigned commits reached `main` despite protection, **or**
3. GitHub ships a tokenless, read-only API to assert branch-protection flags for
   public repos (then tighten CI from soft checklist to hard gate).

Until then, treat merge-commit GitHub signatures plus documented branch protection
as the production baseline for L34 (signed commits).
