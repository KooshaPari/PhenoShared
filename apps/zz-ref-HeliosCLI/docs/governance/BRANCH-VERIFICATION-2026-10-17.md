# Branch Verification — Step 2 (security) + Step 3 (macOS signing)

Run 2026-10-17 as part of the FWD path for the helios-cli fork.

## Step 2 — security/quinn-proto-0.11.19-rustls-0.23.45

**Conclusion: MERGED (4e89e4559e95ce75091f8736b72b027af0670bb2).**
Branch tip's exact commit SHA was NOT on `main`, but the commit's *effect*
(`quinn-proto` 0.11.19, `rustls` 0.23.45 in `Cargo.lock`) was already present
on main via other paths. The merge nevertheless captures a Cargo.lock byte-level
re-resolution that wasn't on main before.

| Probe | Result |
|---|---|
| Branch tip SHA | `ebddf69943aca437085a580e9c8238346eda4ec0` |
| Branch tip subject | `fix(deps): bump quinn-proto 0.11.17→0.11.19, rustls 0.23.43→0.23.45` |
| Tip date | 2026-10-13 17:51:28 -0700 |
| Ancestor of `main`? | **NO** |
| Files unique to branch tip (vs merge-base `bd4ccad01`) | `Cargo.lock` only (binary, 112942 bytes) |
| `Cargo.lock` quinn-proto version (security branch) | `0.11.19` |
| `Cargo.lock` rustls version (security branch) | `0.23.45` |
| Same versions in pre-merge `main`? | YES (`quinn-proto 0.11.19`, `rustls 0.23.45`) |
| Same Cargo.lock bytes? | NO (md5 `19da3adf...` pre-merge vs `429af162...` on branch tip) |
| `git merge --no-ff` outcome | Real merge commit `4e89e4559`; `Cargo.lock` hash changed from `19da3adf...` → `4bd4766e...`; binary diff reports `Bin 122418 -> 122418 bytes` (size stable, content updated) |
| Audit premise | "currently stuck on a side branch" — partially incorrect: versions already on main, but the branch's exact `Cargo.lock` re-resolution was not |

The local security branch pointer is removed in step 5 with `git branch -d` now that the
branch tip is reachable through the merge commit.

## Step 3 — feat/helios-cli-macos-signing-infisical-20260902T0556Z-v3

**Conclusion: ALREADY on main via PR #658. Stale branch, no merge action.**

| Probe | Result |
|---|---|
| Branch tip SHA | `f15cf5f1cda6ee86d3b7e05ad0bb796ed8fc0f3c` |
| Branch tip subject | `feat(release): sign + notarize helios-cli (v3)` |
| Tip date | 2026-09-01 22:56:37 -0700 |
| Ancestor of `main`? | **NO** |
| Files unique to branch tip (vs merge-base `c757cee7`) | `.github/workflows/release-macos.yml` (+37), `apps/helios-cli/src-tauri/Entitlements.plist` (+42) |
| Same files in `main`? | YES — added by commit **`e98058ccc72`** `feat(release): sign + notarize helios-cli (v3) (#658)` on 2026-09-01 22:58:37 -0700 |
| Why different SHA? | GitHub PR-merge produced a non-fast-forward commit at the merge-base `c757cee7..main`; the local branch was created from a pre-PR state |
| `git merge --no-ff` outcome (attempted, then reset) | noise merge commit with no content delta between parents because the PR-merged `e98058ccc72` already added both files at byte-equivalent content |

The work landed on main via PR #658. The branch tip is a local-only ancestry artifact of
the pre-PR state. Stale branch pointer removed in step 5.

## Implication for KEEP stance

The KEEP decision is **stronger** because of these findings:

- Step 2 showed that even when a Dependabot advisory lands on a side branch as a Cargo.lock-only
  patch, the post-merge state is non-trivially different bytes-wise. The merge is real audit
  value, not a no-op.
- Step 3 confirmed the distribution channel (`release-macos.yml` + `Entitlements.plist`) is
  actually on `main`, contradicting the audit's "stuck on a side branch" framing.
- The fork has been disciplined about merging both CI/security and distribution-channel work
  back to `main` via PRs (#658); only branch pointers were left behind.

The 260-vs-10,242 upstream gap remains a sync-cadence issue (fork stopped tracking upstream
commits), not a "work trapped on side branches" issue. The "distribution fork" framing in
`docs/governance/FORK-STANCE-2026-10-17.md` holds.
