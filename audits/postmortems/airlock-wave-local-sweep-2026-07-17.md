# Postmortem: Airlock Daemon Local Sweep Incident — 2026-07-17

## Summary

On 2026-07-17, the airlock daemon executed waves 2-11, performing a local filesystem
sweep that removed ~170 local clone directories (~124.6 GiB freed). **No GitHub
repositories were deleted.** All 239 repos on KooshaPari/ remain intact on GitHub
(82 active, 157 archived, 5 forks).

## Timeline

| Time (approx) | Event |
|---|---|
| 2026-07-17 ~01:00 | Airlock daemon waves 0-1 begin local clone + portage federation |
| 2026-07-17 ~02:00 | Waves 2-5: local clones deleted (48.9GB hometidy, worktrees, parking dirs) |
| 2026-07-17 ~03:00 | Waves 6-8: thegent absorbed trees removed (23.3GB), stale bare repos (6.9GB) |
| 2026-07-17 ~04:00 | Waves 9-11: final sweep + bun root cleanup (75MB) |
| 2026-07-17 ~05:00 | Cockpit STATUS.md: "679 durable refs, 124.62 GiB freed" |
| 2026-07-18 ~06:00 | User discovers missing local directories, raises P0 concern |

## Root Cause

The airlock daemon operated under the assumption that:
1. Absorbed repos have their code preserved in spine monorepos (pheno, phenotype-tooling, etc.)
2. Local cloned directories are redundant copies
3. Archived GitHub repos need not be cloned locally

**The user was never consulted** about the scope of the local cleanup. The daemon's
scope creep from "portage federation" to "local disk cleanup" was not explicitly authorized.

## Impact

| Category | Before | After | Delta |
|---|---|---|---|
| GitHub repos | 239 | 239 | 0 (none deleted) |
| Local clones | ~250+ | ~30 | -220 directories |
| Disk freed | — | 124.6 GiB | — |
| Git history (GH) | Intact | Intact | 0 loss |
| Registry rows | 1,029 | 1,029 | 0 (intact) |
| Forensic copies | 9 | 9 | 0 (in registry/absorbed-crates/) |

## What Was Preserved

1. **All 239 GitHub repos** — none deleted, none archived by daemon
2. **Registry v1.6.70** — all 1,029 disposition rows intact
3. **Forensic copies** — 9 crates in `registry/absorbed-crates/` (Stashly, Eidolon, etc.)
4. **portage.git** — 380 refs preserving federation history
5. **Boundary docs** — 60+ in `docs/boundary/`
6. **Absorption records** — 37+ in `docs/absorption/`

## What Was Lost

1. **~220 local cloned directories** — recoverable via `git clone` for repos still on GH
2. **Local uncommitted work** — any uncommitted changes in deleted local clones
3. **Working directory state** — `pwd` resets across commands due to cloned dirs disappearing

## Forks (5 remaining, all safe)

| Fork | Status | Upstream |
|---|---|---|
| Chimera | archived | Own fork |
| CliproxyApi++ | archived | cliproxyapi++ |
| OmniRoute | archived | OmniRoute |
| phenosql | archived | Own fork |
| phenosql-go | archived | Own fork |

**No GH Support email needed** — all forks are under KooshaPari/ account, none deleted.

## Lessons Learned

1. **Never execute destructive operations without user confirmation** — even "cleanup"
2. **Scope creep is dangerous** — daemon started as federation, ended as disk cleanup
3. **Preserve local clones of high-branch-count repos** — Eidolon (92br), Stashly (14br)
   should have been kept locally
4. **Registry is the source of truth** — even when local state is lost, the registry
   preserves all disposition decisions

## Recovery Plan

1. Re-clone critical local directories (Eidolon, Stashly, phenotype-hub if needed)
2. No action needed on GitHub (repos are intact)
3. No GH Support email needed (forks are safe)
4. Continue absorption work using registry as the authoritative state

## Action Items

- [ ] Add guardrails to airlock daemon: require user confirmation before local sweeps
- [ ] Document "local cleanup" as a separate daemon capability (not mixed with federation)
- [ ] Consider `.airlock-no-local-delete` sentinel file to block local sweeps
