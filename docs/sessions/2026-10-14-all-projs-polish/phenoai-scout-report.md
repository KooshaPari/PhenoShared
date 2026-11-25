# phenoAI scout report — 2026-10-14 (CORRECTED)

**Worker:** session_goat (gpt-6-sol, completed)
**Repo (intended):** KooshaPari/phenoAI
**Repo (actual configured origin):**
`https://github.com/KooshaPari/PhenoShared.git` ⚠️ MISCONFIGURED
**HEAD (local):** d24f1e339 on main

## State

- Worktree: clean except for untracked `docs/sessions/2026-10-14-all-projs-polish/`
- **Misconfigured remote**: `origin` points to PhenoShared, not phenoAI
- Real phenoAI repo: `KooshaPari/PhenoAI` (capital A-I) — **ARCHIVED on GitHub**
  (since 2026-10-12)

## CRITICAL FINDING (discovered post-scout)

The scout reported "main is 1 ahead / 15 behind origin/main" but **this was
measuring against PhenoShared, not phenoAI**, because the remote URL is
misconfigured.

**True divergence (after temporarily fixing URL and fetching from real phenoAI):**

- Local main: d24f1e339 (herdr-forgecode fix)
- Real origin/main: 6ac082834 (chore: absorb PhenoMCPServers)
- **Real divergence: 145 ahead / 169 behind**
- The two histories have absorbed different sprawl repos

After the diagnostic, remote URL was restored to the original (broken) state:

- `origin` → `https://github.com/KooshaPari/PhenoShared.git` (PhenoShared tracking)
- Current "ahead 1 / behind 171" reflects PhenoShared commits not pulled

## Open PRs

- **#108** (created 2026-10-12) — was reported as the only open PR; this is the
  apparent PR on whatever the local thinks origin is (PhenoShared?)

## Actionlint failures (pre-existing, NOT in docs-only polish scope)

- codeql.yml
- ci.yml
- compute-infra-auditors.yml
- scorecard.yml
- Plus unknown runner labels
- Plus shellcheck findings across other workflows

## Polish

- No changes needed after bounded docs README link inspection
- No branch, commit, or PR created

## Blockers / follow-up (CRITICAL)

- **The local phenoAI repo has a misconfigured remote URL**
- The actual phenoAI GitHub repo is archived; the local clone is just a snapshot
- Operator decision needed: leave as-is (broken config, but not actively
  hurting), or properly reconcile
- See `PHONAI-DIVERGENCE-NOTE.md` in this directory for the full analysis

## Validation performed

- git log -10
- git status
- gh pr list JSON
- actionlint .github/workflows/*.yml
- Verified 5 docs/README.md relative links exist
- Final worktree clean (after restoring the original config)
