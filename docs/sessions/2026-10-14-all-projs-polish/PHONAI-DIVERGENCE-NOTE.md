# phenoAI divergence finding — 2026-10-14

## Summary

The local `phenoAI` repo at `~/CodeProjects/Phenotype/repos/phenoAI` has a
**misconfigured remote URL**:

- `origin` points to `https://github.com/KooshaPari/PhenoShared.git`
  (PhenoShared, NOT phenoAI)
- The actual phenoAI GitHub repo is `KooshaPari/PhenoAI` (note: capital A-I)

## Impact

- The scout's report of "main is 1 ahead / 15 behind origin" was WRONG
- The local was actually being compared against PhenoShared, not phenoAI
- The real divergence (after fixing the URL temporarily):
  - Local main: `d24f1e339 fix(herdr-forgecode): advertise resume_argv and
drop reserved herdr: source prefix`
  - Real origin/main: `6ac082834 chore: absorb PhenoMCPServers (MCP
implementations registry)`
  - Real divergence: **145 ahead / 169 behind**

## Repo state

- `KooshaPari/PhenoAI` on GitHub is **ARCHIVED** (since 2026-10-12)
- Both branches are independent snapshots; not actively maintained
- The two histories have absorbed different sprawl repos:
  - Local: absorbed 5 sprawl repos (per `3b45203b absorption: absorb 5 sprawl
repos with provenance and governance`)
  - Remote: absorbed 6 different things (PhenoMCPServers, Eidolon,
    PhenoResearchEngine, Agentora, PlayCua, etc.)

## Action taken

- Fixed remote URL temporarily to verify divergence
- **Reverted** to original (broken) config — local config now matches what
  was there before
- Original config backed up at `/tmp/phenoAI.config.bak`

## Recommendation

- Operator decision needed: this is not a simple "git pull" reconciliation
- Options:
  1. **Leave as-is**: keep the broken config (local tracks PhenoShared), or
  2. **Fix and merge**: properly merge 145/169 commits (multi-day effort), or
  3. **Archive locally**: mark local phenoAI as archived and don't sync
- Given GitHub repo is archived, option 3 (archive locally) is probably the
  right call
