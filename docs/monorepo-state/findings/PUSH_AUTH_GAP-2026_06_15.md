# Push Auth Gap — re-auth as <REDACTED> done; structural issue confirmed (2026-06-15 18:42 PDT)

**Status update:** `gh auth switch --user <REDACTED>` re-auth completed 2026-06-15
18:40 PDT. The 4 previously-unreachable remotes (origin, github, worklogs, dmouse)
are now reachable from `<REDACTED>`'s account.

## Post-auth diagnosis (2026-06-15 18:42)

| Remote | URL | Pre-auth | Post-auth | Reach from <REDACTED> |
|---|---|---|---|---|
| `argis` | `git@github.com:<REDACTED>/argis-extensions.git` | ✅ | ✅ | ✅ (wrong repo) |
| `pheno` | `https://github.com/<REDACTED>/phenoShared.git` | ✅ | ✅ | ✅ (wrong repo) |
| `voxel` | `git@github.com:<REDACTED>/phenotype-voxel.git` | ✅ | ✅ | ✅ (wrong repo) |
| `dmouse` | `https://github.com/Dmouse92/AgilePlus.git` | ❌ 404 | ❌ 404 | ❌ (Dmouse92 is a CLIENT account; never push there) |
| `github` | `https://github.com/Phenotype/Phenotype.git` | ❌ 404 | ❌ 404 | ❌ (org doesn't exist) |
| `origin` | `https://github.com/<REDACTED>/FocalPoint.git` | ❌ 404 | ❌ 404 | ❌ (iOS app, wrong repo for monorepo changes) |
| `worklogs` | `https://github.com/<REDACTED>/worklogs.git` | ❌ 404 | ❌ 404 | ❌ (separate worklogs repo, not the monorepo) |

## Structural finding: the `repos/` directory has NO upstream remote

`Phenotype/Phenotype` org does not exist (404 from `gh api orgs/Phenotype`).
`<REDACTED>/Phenotype` does not exist (the `origin` URL is wrong — it points to
`<REDACTED>/FocalPoint`, which is the iOS app, not the monorepo).
`<REDACTED>/repos` does not exist (the directory name "repos" is a local
convention, not a GitHub repo name).

This means the **`repos/` directory is local-only**. It contains ~280 sub-repos
(submodules, worktrees, or just directories) that each have their own remote
(`<REDACTED>/AgilePlus`, `<REDACTED>/pheno`, `<REDACTED>/PhenoCompose`, etc.) —
but the `repos/` container itself is not on GitHub.

**Implication:** The 37 commits on `chore/w5-adrs-sota-2026-06-15` (worklogs,
findings, ADRs, in-monorepo fixes, status updates) **cannot be pushed to a
monorepo remote** because no such remote exists. They live in the local
working tree and can be:

1. **Reviewed locally** — `git log chore/w5-adrs-sota-2026-06-15`
2. **Patched to file** — `git format-patch main..HEAD > v5-sota-2026-06-15.patch`
3. **Bundled** — `git bundle create v5-sota-2026-06-15.bundle --all`
4. **Cherry-picked to sub-repos** — if a commit touches `pheno/` or
   `Phenotype/Phenotype`, the change can be re-applied to the appropriate
   sub-repo's own remote

## What the auth fix DOES unblock

The 4 GitHub API operations that were blocked:

| # | Operation | Status |
|---|---|---|
| 1 | NetScript DEPRECATED.md push (`<REDACTED>/NetScript`) | UNBLOCKED |
| 2 | NetScript GitHub archive flag | UNBLOCKED |
| 3 | Settly GitHub archive flag (ADR-012 PR-8) | UNBLOCKED |
| 4 | Any future pushes to sub-repos (AgilePlus, PhenoMCP, etc.) | UNBLOCKED |

These can now proceed from `<REDACTED>`'s account.

## Auth scope confirmation

```
$ gh auth status
github.com
  ✓ Logged in to github.com account <REDACTED> (keyring)
  - Active account: true
  - Token: gho_************************************
  - Token scopes: 'gist', 'read:org', 'repo', 'workflow'
  - Logged in to github.com account Dmouse92 (keyring)
  - Active account: false
```

**Active account is now `<REDACTED>`.** `Dmouse92` is a client account
that should never be pushed to (per the user's 2026-06-15 18:40 PDT
directive).

## Action items for the next 5 minutes

1. **Push NetScript `chore/adr-001-archive-2026-06-15`** to `<REDACTED>/NetScript`
2. **Archive `<REDACTED>/NetScript`** via `gh api -X PATCH ... -f archived=true`
3. **Archive `<REDACTED>/Settly`** (ADR-012 PR-8)
4. **Bundle the 37-commit W5 branch** to a `.bundle` file as a recovery artifact

## v6 + W5 commit trail (still local)

All commits reachable from `HEAD` on `chore/w5-adrs-sota-2026-06-15`:

- `0425f86e99` docs(findings): ADR-021 Profila migration status
- `0f370096cd` docs(findings): ADR-012/022 cross-reference
- `ec8b3e4961` chore(pheno-config): publish prep
- `9c114b88b7` chore(root): bump phenoShared to 944a8b9
- `4afc6061a1` docs(status): refresh STATUS.md
- `90cbfa053b` docs(pheno-config): README + twelve-factor
- `b3d215c889` feat(pheno-config): v0.2.0
- `c39437cf3d` docs(findings): ADR-012 PR-4 done
- `a5c03c6054` docs(health): L6 pheno-* evening delta
- `c542b210d4` chore(root): bump helios-router
- `d516bee625` chore: delete crates/phenotype-config (PR-4)
- `52bae896c5` chore(root): delete duplicate top-level pheno-tracing/
- `8765ceaad1` docs(findings): Track 5 closure L5-097..100
- `659781ee0f` docs(findings): v6 Track 4 verified
- `d037999bcc` docs(findings): v6 master status
- (and 22 more in the 37-commit W5 branch)

To export the full history as a bundle:

```bash
cd /Users/<REDACTED>/CodeProjects/Phenotype/repos
git bundle create /tmp/w5-sota-2026-06-15.bundle --all
```
