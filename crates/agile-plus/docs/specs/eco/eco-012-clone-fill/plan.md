# eco-012: Clone Fill — Plan

## Objective

Restore canonical-fleet baseline parity for the <REDACTED> org by cloning the 9 oldest non-archived repos that currently have no local checkout, using a shallow (`--depth 50`) `gh repo clone` into the standard repos path.

## Scope

**In scope**
- 9 repos from `worklogs/oldest-<REDACTED>-20260605.json`: kmobile, KWatch, phenotype-postfx, Eventra, phenotype-water, phenotype-terrain, KaskMan, Apisync, Pyron.
- Per-repo outcome recording in `clone-results.md`.
- Free-space guard against the disk-budget policy floor (20 GB).

**Out of scope**
- Worktree creation or branch discipline.
- Quality gates (`cargo`, `npm`, `pytest`).
- Renaming or re-organizing the repos tree.
- Re-cloning repos that already exist locally.

## Implementation Steps

1. **Preflight (1 tool call)**
   - Verify `gh auth status` reports a valid token.
   - Verify `df -k /Users/<REDACTED>/CodeProjects/Phenotype/repos` shows ≥ 20 GB free; abort with a documented reason if not.
   - Read `worklogs/oldest-<REDACTED>-20260605.json` to confirm the 9-repo list (in case the snapshot has shifted since spec authoring).

2. **Sequential clone loop (9 tool calls, 1 per repo)**
   - For each name in the list:
     a. If `/Users/<REDACTED>/CodeProjects/Phenotype/repos/<name>` exists and contains `.git/`, record `present`.
     b. Else run `gh repo clone <REDACTED>/<name> /Users/<REDACTED>/CodeProjects/Phenotype/repos/<name> -- --depth 50`.
     c. Capture exit status; on success record `cloned`, on failure record `skipped: <stderr reason>`.

3. **Verify (1 tool call)**
   - For each `cloned` repo, run `git -C <path> rev-parse HEAD` to confirm a valid HEAD.

4. **Persist results (1 Write tool call)**
   - Write `kitty-specs/eco-012-clone-fill/clone-results.md` with the per-repo table.
   - Mark spec `DONE` in frontmatter once 9/9 outcomes are recorded.
