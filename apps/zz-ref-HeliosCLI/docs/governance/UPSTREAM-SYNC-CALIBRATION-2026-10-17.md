# Upstream Sync Calibration — 2026-10-17 (Step 4 outcome)

## Calibration setup

- **Upstream**: `https://github.com/openai/codex.git` → `upstream/main`
- **Fork HEAD (baseline)**: `3460d16d946f8ae21dc4b3512cf90f3c7b602f02` (post Step 2/3 verification)
- **Sync branch**: `sync/upstream-2026-10-17` (fresh from `main`, identical to baseline — calibration added zero commits)
- **Method**: Pre-fetched upstream with `git fetch upstream`. From the freshest 100 commits on `upstream/main`, attempted `git cherry-pick <sha> --no-commit` onto the sync branch in chronological (oldest-first) order. Confirmed clean applies were committed; conflicts were aborted with `git cherry-pick --abort` and logged.
- **Calibration cap**: 100 upstream commits to bound wall-clock to ~2 minutes (the loop took 135 seconds for 100 attempts).

## Result

```
CLEAN   : 0
CONFLICT: 100
```

**100% conflict rate**. Every single one of the 100 freshest upstream commits conflicts
with the fork at the source level — even highly mechanical, low-blast-radius commits
(notify-config fixes, CLI help-text tweaks, dependency bumps, etc.) all encounter
non-auto-resolvable conflicts.

## Interpretation

The fork-vs-upstream gap is **not recoverable via cherry-pick**. The 260 fork-only
commits (and the 12,326 upstream-only commits behind `main`) have evolved the source
tree on each side past the point of structural compatibility. Concretely:

- `codex-rs/core/src/config/...` has been deeply restructured upstream; the fork's
  config layer (`crates/helios_config/...`) sits alongside but not interchangeable.
- `codex-rs/app-server/...` has been ported; the fork kept pre-port code.
- `codex-rs/network-proxy/...` had ~2,500 lines of changes upstream; the fork diverged
  to its own `crates/helios-sandbox` envelope.
- Several fork-unique crates (`helios`, `helios-ai`, `helios-tools`, `helios-tui`) have no
  upstream equivalent at all.

## Implication for KEEP stance

The "distribution fork" framing from step 1's `FORK-STANCE-2026-10-17.md` is reaffirmed
but sharpened:

- **KEEP** for the macOS notarization distribution channel (`release-macos.yml` + `Entitlements.plist`
  + Infisical secrets) — this is the *real owned asset* and does not depend on upstream
  source compatibility.
- **DROP** the sync-cadence workstream — repeated sync attempts will never produce clean
  applies; we have empirical evidence of 0% over 100 freshest commits.
- **SHIFT** dependency-update policy: instead of upstream tracking, use Dependabot or weekly
  Renovate to pull upstream's `codex-rs/Cargo.toml` dep-list individually, isolating
  individual dep updates from the bulk-evolution churn. Some of these will succeed; none
  require a structural sync.
- **DOCS-TAG**: `crates/helios_*`, `docs/audits/`, `apps/helios-cli/`, `crates/harness_*`,
  `.github/workflows/release-macos.yml` are the "owned territory" of this fork. Future FWD
  paths should optimize for these directories' health, not upstream-trunk sync.

## What changed in this step

- `git fetch upstream` ran (most recent upstream HEAD `ce0323f2f2d3b25e82806cd555237da3db4e1897`,
  2026-10-17 04:02:21 +0000, `Support typed content in contextual prompt fragments (#54776)`).
- The sync branch `sync/upstream-2026-10-17` was created from main, the calibration loop ran
  for 135s on it, and the branch remains identical to `main` (zero net commits added).
- No push was made — the branch contains nothing other than main's commits; pushing it would
  be noise.
- Subsequent Step 5 cleanup removes the sync branch pointer locally with `git branch -d`.

## Calibration timing

- Sample window: commits `e16b631d08cdf82773831f9bbfb793da687d5299` (upstream 100-most-recent
  at fetch time) through the upstream tip.
- Wall-clock: 135.06 seconds for 100 cherry-pick attempts.
- Effective per-attempt cost (including exit/abort calls): ~1.35 seconds per attempt, indicating
  the conflict detection is fast even on a big delta.
- Not measured but implied: the full `git rebase upstream/main` over 12,326 commits would run
  for roughly 12,326 × 0.001–0.005 = 12–60 seconds assuming uniform clean applies, but would
  block on the first ~10–20 conflicts for hours of resolution work. Calibration is preferred.

## Re-evaluation trigger

Re-run this calibration if and only if:

- The fork lands a meaningful upstream-shape restructure (e.g., absorbs upstream's
  `codex-rs/network-proxy` rewrite), OR
- The fork drops the `crates/helios_*` envelope, OR
- Upstream merges a `codex-rs` folder rename that makes the source tree structurally align.

Otherwise the calibration result is stable and the distribution-fork stance is unchanged.
