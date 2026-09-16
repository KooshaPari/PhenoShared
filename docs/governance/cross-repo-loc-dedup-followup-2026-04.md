# Cross-Repo LOC Dedup Followup — 2026-04-25

Followup verification of the duplications flagged in the 2026-03-29 LOC audit
(see `MEMORY.md` → "Lines of Code (LOC) Audit & Optimization"). Worktree state
changes constantly; this doc captures **current** counts and recommends action.

## TL;DR

The original audit reported ~35K LOC of duplication. Today the apparent count
is **higher**, but ~99% of it lives in legitimate git worktrees of `thegent`
(`thegent-wtrees/*`, `.worktrees/*`). Per the workspace policy in
`Phenotype/CLAUDE.md`, worktree files are scratch space and **must not be
deduped** — they share a single git object database with the canonical clone
and exist precisely to give agents independent working copies.

**Recommendation: take no dedup action.** The 2026-03-29 audit overcounted by
treating worktree copies as duplication. The single legitimate cross-project
duplication (`lib/api.ts` between `portage/viewer` and `hwLedger/apps/windows`)
is too small and too divergent in domain to justify extraction.

## Verification (2026-04-25)

Find commands run from `/Users/kooshapari/CodeProjects/Phenotype/repos/`,
excluding `target/`, `.git/`, `node_modules/`, `.next/`.

### Pattern 1: `test_phench_runtime.py` (2,111 LOC each)

- **Old audit:** 5 copies, ~8,480 LOC.
- **Now:** **30 copies** found. Breakdown:
  - 1 canonical: `thegent/tests/`
  - 1 alt-canonical: `pheno/tests/` (separate repo, intentional fork target)
  - 1 archived: `.archive/PhenoLang-actual/tests/` (archive — leave)
  - 1 in `PhenoKits/HexaKit/tests/` (separate repo)
  - **26 in worktrees** (`thegent-wtrees/*` ×12, `.worktrees/*` ×13,
    `repos-wtrees/dep-nkeys/HexaKit/` ×1)
- **Action:** None. Worktrees are not duplication. The
  `pheno`/`PhenoKits/HexaKit` copies are separate repos that may eventually
  consume from a shared `phenotype-test-fixtures` crate, but that's a
  cross-project extraction (see Phase 2 of original plan), not a quick fix.

### Pattern 2: `test_unit_cli_coverage_*.py` (~2,465 LOC each, var c only)

- **Old audit:** "main + worktrees", ~12,000 LOC.
- **Now:** **15 copies** of `test_unit_cli_coverage_c.py`.
  - 1 canonical: `thegent/tests/`
  - 14 worktree copies (`thegent-wtrees/*` ×12, `.worktrees/thegent-pr908-policy-fix/`,
    `thegent/thegent-wtrees/ruff-fix/`).
- **Action:** None. 100% of duplication is worktree scratch.

### Pattern 3: `docs/page.tsx` and `lib/api.ts`

#### `app/(dashboard)/docs/page.tsx` (953 LOC)

- **Old audit:** ~8,000 LOC across main + worktrees.
- **Now:** **22 copies** of the byteport variant. All but one are worktrees.
  Canonical: `thegent/apps/byteport/frontend/web-next/app/(dashboard)/docs/page.tsx`.
- Three other files matching the glob are unrelated (`cloud/src/app/admin/credit-categories/docs/page.tsx`,
  Tracera, omniroute) — different applications with different content.
- **Action:** None. Worktree-only duplication.

#### `lib/api.ts` (805 LOC for byteport variant)

- **Now:** 30 hits, but they belong to **at least 4 distinct apps**:
  - `thegent/apps/byteport/frontend/web-next/lib/api.ts` (byteport — 18 worktree copies)
  - `portage/viewer/app/lib/api.ts` (portage — 4 worktree copies)
  - `hwLedger/apps/windows/hwledger-tauri/src/lib/api.ts` (hwLedger — 5 worktree copies)
  - `Tracera-recovered/frontend/apps/web/scripts/lib/api.ts` (Tracera, recovered)
- **Action:** None for worktree copies. The cross-project resemblance
  (byteport ↔ portage ↔ hwLedger) is **name-only**; the files implement
  different API clients against different backends. Not extraction candidates.

### Pattern 4: `sidebar-auto.ts` (6,764 LOC each)

- **Old audit:** 6,764 LOC duplicated (main + worktree).
- **Now:** **16 copies**. All belong to the thegent VitePress docsite.
  - 1 canonical: `thegent/docs/.vitepress/sidebar-auto.ts`
  - 15 worktree copies.
- **Note:** This file is *generator output* (`sidebar-auto.ts`, distinct from a
  hand-written `sidebar.ts`) — regeneratable from the docs tree. Worktrees
  inherit the file because it's committed.
- **Action:** None. Worktree scratch. A separate-but-related improvement would
  be to `.gitignore` the generated sidebar and produce it at build time, but
  that is a thegent-internal concern out of scope for cross-repo dedup.

## Why the count went *up*, not down

Between 2026-03-29 and today, several worktrees were added (the
`thegent-wtrees/dependabot-*` set, the `m1`–`m6` modules worktrees, and the
`Metron`/`Portalis`/`PhenoKits-tracera-fr-scaffold` paths). Each new worktree
materializes the canonical files in its working copy, so apparent duplication
grows linearly with worktree count. **None of this is real duplication on
disk-of-record** — git stores objects once in `.git/`, the working copies are
checkouts.

## Cross-project duplication that *is* real

After filtering worktrees, the only meaningful cross-repo similarity is:

| File | Repos | Status |
|------|-------|--------|
| `test_phench_runtime.py` | `thegent`, `pheno`, `PhenoKits/HexaKit` | Candidate for `phenotype-test-fixtures` extraction (already in Phase 2 plan from 2026-03-29; gated on cross-repo migration cost). |
| `lib/api.ts` (name only) | `byteport`, `portage`, `hwLedger`, `Tracera` | **Not duplication.** Different domains, different content, only file name shared. |

**Recommendation:** Defer the `phenotype-test-fixtures` extraction until the
fixtures actually drift between `thegent` and `pheno`/`HexaKit`. Premature
extraction here would introduce a hard dependency for a small-LOC win.

## Process correction

The 2026-03-29 LOC audit conflated *file-system duplication* with
*git-tracked duplication*. Future audits should:

1. Run `git worktree list` for each repo first.
2. Exclude all worktree paths from `find`/`tokei`/`scc` runs.
3. Treat `pheno` ↔ `thegent` ↔ `PhenoKits` cross-pollination as
   *cross-repo*, not *intra-repo* duplication.

## Disk

`df -h /System/Volumes/Data` at audit time: **17 GiB free of 926 GiB**. Above
the 15 GiB floor but below the 20 GiB pre-dispatch threshold. Do not launch
parallel cargo builds without `target-pruner --prune` first.

## Decision

**No dedup PRs filed. No code changed.** This audit document supersedes the
"~35K LOC duplication" line item in the 2026-03-29 memory entry; the corrected
figure for *real* (non-worktree) duplication is closer to ~5K LOC (the
`test_phench_runtime.py` cross-repo case) and is not currently worth
extracting.
