# Reconcile Sprint: CLIProxy++, thegent, agentapi++ (2026-02-26)

## Executive Status

- `cliproxyapi-plusplus`: enormous open-PR surface with stacked/cascading
  migration PRs and shared workflow failures (`CodeQL`, `Analyze (Go)`, `build`,
  `verify-required-check-names`, `CodeRabbit`, `Build Docs`).

- `thegent`: 8 open PRs with 7 blocked/dirty states and significant CI breakage
  concentrated in multi-platform/build/doc/gating jobs.

- `agentapi-plusplus`: 20+ open PRs, mostly `BLOCKED` or `DIRTY`, widespread
  check failures and many open review threads in #243 and #242.

## Repo-by-Repo Audit

### cliproxyapi-plusplus (open PRs observed: 60+ in this batch)

- Snapshot IDs checked: `616, 615, 614, 613, 612, 611, 610, 609, 608, 607` (same
  pattern continues through `557+`).

- Top sample check posture:

  - `616`: `Analyze (Go) (go)` failure, `build` failure,
    `verify-required-check-names` success.

  - `615-613`: same failing core checks + `verify-required-check-names`
    failures.

  - `612`: `Verify`/`build`/`Analyze` failures.

  - `611`: 6 failing checks with `CodeRabbit` success.

  - `610`: `Analyze` + `build` failures (Go lint/analyze area) plus neutral
    CodeQL.

  - `609/608`: `verify-required-check-names`, `Analyze`, `Build Docs` failures.

- Merge status spread:

  - Mostly `BLOCKED` or `DIRTY` with both `MERGEABLE` and `CONFLICTING`.

  - High churn means these are mostly wave-merged migration branches rather than
    isolated work.

- Review/action signal:

  - Many PRs have issue comments (`review_comments=0` for sampled IDs, with
    comments often attached as issue-level threads).

  - Several PRs show `verify-required-check-names` drift, indicating required
    check manifest and workflow naming mismatch.

### thegent

| PR | Branch | Merge state | Issue comments | Review comments | Failing checks | Key issue |
|---|---|---|---:|---:|---:|---|
| 498 | garden/release-framework | BLOCKED | 2 | 0 | 45 | Global infra stack fail (`Build wheels`, `Build Docs`, `Comprehensive Benchmark`, platform tests) |
| 497 | chore/cliproxyctl-auto-install | BLOCKED | 2 | 0 | 19 | Same infra stack as #498 |
| 496 | PR: fix/tests3 | DIRTY | 4 | 0 | 2 | Mergeability noise despite mostly green checks |
| 494 | fix/orjson-v2 | DIRTY | 11 | 1 | 1 | `CodeRabbit` only; comment debt |
| 493 | fix/tests-v4 | DIRTY | 2 | 0 | 0 | Mostly green, mergeability still dirty |
| 482 | no-litellm | BLOCKED | 2 | 2 | 26 | Unresolved + infra gates |
| 480 | fix/cli-test-fixes | BLOCKED | 2 | 2 | 17 | Unresolved review threads + test infra failures |
| 478 | fix/remove-broken-dag-files | DIRTY | 2 | 6 | 2 | 5+ unresolved review threads |

Notes:

- branch audit shows mixed mergeability metadata; treat as a **batch-first
  stabilization** where shared CI is fixed before per-PR conflict repair.

### agentapi-plusplus

| PR | Branch | Merge state | Issue comments | Review comments | Failing checks | Key issue |
|---|---|---|---:|---:|---:|---|
| 263 | fix/test-msg-format | BLOCKED | 4 | 0 | 5 | CodeRabbit needed |
| 262 | fix/slash-commands | BLOCKED | 4 | 0 | 5 | CodeRabbit needed |
| 261 | garden/sdk-integration | DIRTY | 5 | 0 | 1 | Merge conflicts |
| 260 | fix/pr17 | DIRTY | 5 | 0 | 5 | CodeRabbit needed |
| 259 | fix/pr16 | DIRTY | 5 | 0 | 5 | CodeRabbit needed |
| 258 | fix/pr14 | DIRTY | 4 | 0 | 5 | CodeRabbit needed |
| 257 | fix/pr13 | DIRTY | 2 | 0 | 5 | CodeRabbit needed |
| 256 | garden/git-tightening | BLOCKED | 2 | 0 | 4 | Mix of infra and review queue |
| 255 | fix/pagination | DIRTY | 4 | 0 | 1 | CodeRabbit needed |
| 254 | fix/opencodescreen-diff | DIRTY | 5 | 0 | 5 | CodeRabbit needed |
| 253 | fix/initial-prompt-tests | DIRTY | 4 | 0 | 5 | CodeRabbit needed |
| 252 | fix/health-check | DIRTY | 5 | 0 | 5 | CodeRabbit needed |
| 251 | fix/first-line-trimmed | DIRTY | 5 | 0 | 1 | CodeRabbit needed |
| 250 | fix/feature18 | BLOCKED | 5 | 0 | 5 | CodeRabbit needed |
| 249 | fix/e2e-asciinema | BLOCKED | 4 | 0 | 5 | CodeRabbit needed |
| 248 | fix/askuser-input | DIRTY | 4 | 0 | 5 | CodeRabbit needed |
| 247 | fix/afero-walk | DIRTY | 4 | 0 | 5 | CodeRabbit needed |
| 246 | fix/add-agent-info | DIRTY | 2 | 0 | 5 | CodeRabbit needed |
| 243 | fix/voice-input | DIRTY | 4 | 3 | 1 | Unresolved threaded comments + bot review |
| 242 | chore/docs-scaffold-and-test-fix | DIRTY | 4 | 12 | 1 | Substantial threaded review backlog |

## Re-review Actions Executed

- `agentapi-plusplus`:

  - Posted `@coderabbitai full review` on PRs: `#263, #262, #260, #259, #258,
    #257, #256, #255, #254`.

- `thegent`:

  - Posted `@coderabbitai full review` on PR `#494`.

- `cliproxyapi-plusplus`:

  - Broad full-sweep trigger for all open PRs was attempted but API/CLI timed
    out during batch execution.

## Priority Plan

1. Run repo-wide workflow baseline fixes first (`verify-required-check-names`,
  `Build Docs`, `Build wheels`, shared `go analyze` failures).

2. For `thegent`, unblock infra gates then resolve threaded reviews in `#478 ->
  #480 -> #482`.

3. For `agentapi-plusplus`, clear `CodeRabbit`-failing PRs with targeted
  re-review then address `CONFLICTING` stacks in numeric order.

4. For `cliproxyapi-plusplus`, process as migration waves with root/replay
  branches (`fix-ci`, `migrated*`, `lane*`) and keep canonical `main` local
  branch clean.

## Immediate next commands

- `git -C /Users/kooshapari/CodeProjects/Phenotype/repos/cliproxyapi-plusplus
  status --short --branch`

- `git -C /Users/kooshapari/CodeProjects/Phenotype/repos/cliproxyapi-plusplus
  worktree list`

- `for n in $(gh pr list --repo KooshaPari/cliproxyapi-plusplus --state open

  --json number --jq '.[].number' --limit 60); do gh pr checks $n --repo
  KooshaPari/cliproxyapi-plusplus --json name,state; done` (chunked)

- `gh pr checks <PR> --repo KooshaPari/agentapi-plusplus --json name,state`

- `gh pr checks <PR> --repo KooshaPari/thegent --json name,state`

## Offline Reconcile Addendum (2026-02-26)

- `gh auth` is currently invalid in this environment; live PR check/query
  commands are blocked.

- `cliproxyapi++` canonical branch has been switched back to `main` and left
  there for safe staging.

- Local branch inventory snapshot:

  - `cliproxyapi++`: 6 merged-local, 64 non-merged locals

  - `cliproxyapi-plusplus`: 4 merged-local, 207 non-merged locals

  - `thegent`: 3 merged-local, 7 non-merged locals

  - `agentapi-plusplus`: 2 merged-local, 3 non-merged locals

- Highest-priority cleanup strategy:

  1) Re-auth GH and refresh authoritative PR/CI states
  2) Fix shared CI blockers in wave order (`CodeRabbit`, analyze/build/docs/checks)
  3) Resolve review-thread debt after core checks are stable
  4) Prune stale non-merged locals confirmed closed upstream

## Immediate Next Commands (run after `gh auth login`)

- `gh auth status`

- `for n in ...; do gh pr list -R KooshaPari/cliproxyapi-plusplus --state open;
  done`

- `gh pr checks <n> -R KooshaPari/cliproxyapi-plusplus --json name,state`

- `gh pr view <n> -R KooshaPari/cliproxyapi-plusplus --json
  reviewDecision,mergeStateStatus,comments,reviews`

- Repeat for `thegent` and `agentapi-plusplus` once online tokens are valid

## Execution Queue (Generated Locally, No GH Access)

### Wave A: branch baseline normalization (safe, local-only)

1. `cliproxyapi++`: stay on `main`
2. `cliproxyapi-plusplus`: keep `main`; defer pushing to upstream until auth restored
3. `thegent`: keep `main`
4. `agentapi-plusplus`: keep `main`

### Wave B: local branch backlog (high signal)

- `cliproxyapi-plusplus` local backlog count: 207 (`archive/*`, `ci/*`,
  `ci-fix/*`, `migrated/*`, many `tmp-*`)

- `cliproxyapi++` local backlog count: 64 (`ci/*`, `feat/*`, `migrated/*`, and
  `main-restore`)

- `thegent` local backlog count: 7

- `agentapi-plusplus` local backlog count: 3

### Suggested local cleanup command set (run only after GH validation)

- `gh pr list --repo KooshaPari/cliproxyapi-plusplus --state all --limit 500`
  and compare PR/head mapping

- `for b in $(git -C
  /Users/kooshapari/CodeProjects/Phenotype/repos/cliproxyapi-plusplus branch |
  sed 's/^* //'); do`\n `printf "%s\n" "$b"; done` -> map to PR heads

- stale-close sweep command pattern:

  - `git branch -D <branch>` for local branches confirmed closed/upstream merged

- keep worktree branches in `*-wtrees/*` untouched

### Review/CI debt priority (when GH is available)

1. `thegent`: unblock PR #478 first, then #480, #482, then PRs
  #494/#493/#493-like mergeability noise

2. `agentapi-plusplus`: fix check-blocked PRs first (`#263`,`#262`,`#260`...),
  then conflict-heavy (`#261,#260,#259...`)

3. `cliproxyapi-plusplus`: stabilize check-name drift + analyze/build, then lane
  replay from lowest PR first (`492..616` as archived ordering snapshot)

### Hard guardrails

- Do not force-delete or hard-rewrite `main` in any canonical repo.

- Avoid `git reset`/`git checkout` away from branch context for local canonicals
  except explicit requested merges.

## Live Local Snapshot (post-checkpoint, 2026-02-26)

### Canonical branch positions (verified)

- `cliproxyapi++`: `main` on `upstream/main`, `1` ahead.

- `cliproxyapi-plusplus`: `main` on `origin/chore/fix-gh-pages-workflow-gates`,
  `2` ahead.

- `thegent`: `main` on `upstream/main`, `4` ahead, local edits present.

- `agentapi-plusplus`: `main` on `upstream/main`, `1` ahead `74` behind.

### Non-merged branch pressure (local, `git branch --no-merged main`)

- `cliproxyapi++`: `64` branches

- `cliproxyapi-plusplus`: `207` branches

- `thegent`: `8` branches

- `agentapi-plusplus`: `3` branches

### Current priority queue (local-only planning, GH auth still invalid)

1. **Fix shared CI check-name / lint-gate template drift first** (historically
  blocked across `cliproxy*` and `thegent` batches).

2. **Resolve review-comment debt** where bot/PR review comments are still
  blocking mergeability.

3. **Run PR check refresh once `gh` auth is restored**, then map each local
  branch to PR heads before deleting.

4. **Close stale locals only after upstream confirmation** for:

   - stale PR branch deletion

   - stale migration/capture branches that never had open PRs

### Commands to run after auth recovery

```
gh auth login
for repo in cliproxyapi++ cliproxyapi-plusplus thegent agentapi-plusplus; do
gh pr list --repo KooshaPari/$repo --state open --json
number,headRefName,mergeStateStatus,reviewDecision,isDraft,updatedAt
done
```

For known comment debt on `agentapi-plusplus` and `thegent`:

```
for n in 263 262 260 259 258 257 256 255 254; do
gh pr comment KooshaPari/agentapi-plusplus $n --body "@coderabbitai full review"
|| true
done
gh pr comment KooshaPari/thegent 494 --body "@coderabbitai full review" || true
```

## Recheck (2026-02-26, after latest run)

- `gh auth status` is still invalid for `KooshaPari` and `Dmouse92`; no live PR
  operations possible.

- `cliproxyapi++`: `main` clean of branch changes, still `64` non-merged, plus
  untracked `.airlock`.

- `cliproxyapi-plusplus`: `main` plus untracked `cli-proxy-api-plus` and
  `server` binaries and `.airlock`.

- `thegent`: on `main`, still with in-repo doc edits from prior governance work;
  `8` non-merged.

- `agentapi-plusplus`: on `main`, `3` non-merged, plus untracked `.airlock`.

### Immediate offline-safe next step set

1. Consolidate all `.airlock`, `cli-proxy-api-plus`, `server` artifacts via
  repo-specific `.gitignore` rules in each canonical repo before any future
  pushes.

2. Keep canonical branches on `main`.

3. After auth restoration, execute PR sync:

   - `gh pr list --state open` for each repo,

   - `gh pr checks` for current failures,

   - `@coderabbitai full review` on CodeRabbit-blocked PRs,

   - close-only branches confirmed upstream-closed.

## Repo Branch Closure Matrix (local audit, deterministic)

### 1) cliproxyapi++

- total non-merged: 64

- candidate cleanup classes:

  - `tmp-`: 1 (`tmp-sign-test`, plus any other temp prefixed)

  - `ci/`: 23

  - `migrated/`: 27

  - `feat/`: 7

  - `chore/`: 1

  - `garden/`: 3

- first-pass local-prune candidates (only after upstream confirmation):

  - `tmp-*`

  - likely duplicated `main-restore` snapshots and `a`

  - stale `ci/*`/`migrated/*` that are fully represented as completed PR stacks

### 2) cliproxyapi-plusplus

- total non-merged: 207

- candidate cleanup classes:

  - `tmp-`: 13

  - `ci-fix`: 13

  - `ci/`: 22

  - `migrated/`: 13

  - `feature/`: 17

  - `feat/`: 5

  - `chore/`: 5

  - `replay/`: 39

  - `reintegrate/`: 6

  - `fix/`: 2

  - `garden/`: 1

- first-pass local-prune candidates:

  - `tmp-*`

  - `ci-fix-tmp-*`

  - `replay/*` and `reintegrate/*` after PR mapping check

### 3) thegent

- total non-merged: 8

- candidate cleanup classes:

  - `fix/`: 4

  - `garden/`: 3

- focus sequence:
  1. `fix/remove-broken-dag-files`
  2. `fix/cli-test-fixes`
  3. `fix/flash-agent-graceful-fallback`
  4. `fix/cliproxyctl-empty-response-error`
  5. `no-litellm`
  6. remaining garden branches

### 4) agentapi-plusplus

- total non-merged: 3

- candidate cleanup classes:

  - `garden/`: 1 (`garden/release-framework`)

  - `stack/`: 2

- focus sequence:
  1. stack branches
  2. garden/release-framework

### Live execution workflow (when `gh` auth is valid)

- `gh pr list -R KooshaPari/<repo> --state open --json
  number,headRefName,mergeStateStatus,reviewDecision,isDraft,updatedAt`

- map each `headRefName` to local non-merged branches

- remove branch only if one of:

  - PR closed/merged

  - branch appears to be temp/replay/capture and no longer mapped to open PR

- use `git branch -D <branch>` only after mapping and only within `...-wtrees/*`
  scoped local sets
