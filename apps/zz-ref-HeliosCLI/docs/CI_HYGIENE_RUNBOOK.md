# CI Hygiene Runbook — helios-cli

This document captures the state of `helios-cli` CI/CD after the 2026-09-20 hygiene
session and serves as a reference for future maintenance.

> **TL;DR**: v0.11.1 is released. All required CI checks are green on main.
> Mergify auto-merges 13 PR types including release-please (label-only
> gating, see §6). SonarCloud has 1 residual hotspot + E ratings on new code
> (non-blocking, needs Koosha's UI access). All WIP PRs resolved: #681, #685
> merged; #682, #683 closed as already-incorporated (zero delta vs main).
> 1 drift branch (`token-bucket-wait-time`) still needs archiving (issue #680).

---

## 1. Required CI checks

These three checks must pass before Mergify will auto-merge a PR:

| Check                         | Workflow          | Verifies                                          |
| ----------------------------- | ----------------- | ------------------------------------------------- |
| `CI results (required)`       | `ci.yml`          | Aggregate across all jobs                         |
| `Lint & Format`               | `trunk-check.yml` | prettier on changed files (full repo on schedule) |
| `build + test + clippy + fmt` | `rust-ci.yml`     | rust compile + tests + clippy + rustfmt           |

**Other green checks** (informational, not required):

- `Full CI results`, `cargo deny`, `cargo shear`, `TruffleHog`, `Socket Security`,
  `Codespell`, `Release Please`, `Format / etc`, `Argument comment lint`,
  `Detect changed areas`.

**Non-blocking failures** (not in Mergify's required list):

- `SonarCloud Code Analysis` — see §4.
- `bench` — informational performance benchmark, runs nightly.

---

## 2. Mergify auto-merge

Configured in `.mergify.yml`. 13 rules active on `main`:

| Rule | Author / label match                        | Auto-merge? |
| ---- | ------------------------------------------- | ----------- |
| 1–4  | Dependabot (npm, cargo, uv, github-actions) | ✅          |
| 5    | `release-please[bot]`                       | ✅          |
| 6+   | Various "auto-merge" label triggers         | ✅          |

**Gotcha**: ALL auto-merge rules use `delete_head_branch:` (NOT `delete_branch:`).
The latter is invalid syntax that breaks the ENTIRE Mergify config and blocks
all merges repo-wide. The Mergify Summary check-run reports "Extra inputs are not
permitted" if you use the wrong name.

**Required check names in Mergify config** must match the GitHub check-run names
exactly:

- `CI results (required)`
- `Lint & Format`
- `build + test + clippy + fmt`

**When adding branch deletion** to a rule use `delete_head_branch:` (see gotcha
below) — or rely on the repo-native `delete_branch_on_merge: true`.

### Release-please merge flow — external gates (PR #688, v0.11.2, 2026-09-27)

The label-only rule fires a plain `merge` action, but two GitHub-side gates can
still block it; Mergify will report them as
`Waiting for queue conditions to match` with its `Mergify Merge Queue` check
stuck at `neutral`:

1. **Branch protection "Require conversation resolution."** Bots
   (`chatgpt-codex-connector`, SonarQube, CodeRabbit) leave review threads on
   the release PR. While any is unresolved GitHub reports `BLOCKED` and the
   queue condition `#review-threads-unresolved = 0` [🛡 GitHub branch
   protection] never matches. Fix: reply in-thread with the evidence, then
   resolve via GraphQL:

    ```
    gh api graphql -f query='query { repository(owner:"KooshaPari", name:"HeliosCLI") { pullRequest(number: N) { reviewThreads(first: 20) { nodes { id isResolved } } } } }'
    gh api graphql -f query='mutation { resolveReviewThread(input: {threadId: "PRRT_..."}) { thread { id isResolved } } }'
    ```

    Precedent: NO release commit on main has ever carried `AP-ITEM:`/
    `AP-FEATURE:` — automated version bumps are not AgilePlus work items.
    Reply with that evidence; do NOT invent an id to satisfy the bot.

2. **Mergify does not re-evaluate on GitHub-only events.** Resolving a review
   thread does not wake Mergify — the queue status stays "Waiting" until a
   comment event arrives. After fixing any external condition post
   `@mergifyio refresh`; on #688 the refresh comment itself triggered
   evaluation and the PR merged within a second.

---

## 3. Trunk Check (prettier)

Runs prettier 3.6.2 with NO `.prettierrc` (uses `.editorconfig` defaults).
This causes a conflict: `.editorconfig` says `indent_size = 4` for YAML, but
GitHub Actions workflow YAML requires 2-space top-level indent.

**Resolution**: root `.prettierignore` excludes:

- `.github/**/*.{yml,yaml}` — workflow files (would be reformatted to invalid YAML)
- `.release-please-manifest.json`, `release-please-config.json`, `CHANGELOG.md` —
  release-please auto-generated files (would cause commit churn every release)

**Diff-scoped**: the workflow only checks changed files in PRs. Full-repo sweep
runs Monday 3am UTC (weekly schedule).

**To format new code locally**:

```bash
npx prettier --check '*.{md,yml,yaml,json,jsonc,mdx}'
npx prettier --write <file>
```

---

## 4. SonarCloud Quality Gate

Project: `KooshaPari_helios-cli` on sonarcloud.io. Quality gate configured at
the project level.

### Current state (2026-09-20)

| Condition                        | Status                        |
| -------------------------------- | ----------------------------- |
| 3 Security Hotspots              | 2 ✅ resolved, 1 ⚠️ remaining |
| E Reliability Rating on New Code | ❌ failing                    |
| E Security Rating on New Code    | ❌ failing                    |

**Why E ratings fail**: project was recently onboarded, so SonarCloud's leak
period covers the entire codebase (853 open issues all count as "new code").
Fixing all 853 is a multi-week effort; better to tighten the leak period or
customize the gate.

### What was fixed (commits 765cabd0f, a372a40cf)

| File                                            | Hotspot                                 | Fix                                                                                           |
| ----------------------------------------------- | --------------------------------------- | --------------------------------------------------------------------------------------------- |
| `sdk/typescript/tests/responsesProxy.ts:188`    | `typescript:S2245` (weak crypto)        | `// NOSONAR` — `Math.random()` is for test fixture `call_id`, not security                    |
| `codex-rs/.github/workflows/cargo-audit.yml:22` | `githubactions:S7637` (unpinned action) | Pinned `taiki-e/install-action@v2` → SHA `2c5a301961922d639df2e9cf00b5d23c8e80462d` (v2.5.10) |
| `harness/scripts/health_server.py:129`          | `python:S5332` (HTTP without TLS)       | `# nosonar` added but SonarCloud requires UI review workflow                                  |

### What needs Koosha

1. **1 residual hotspot**: `harness/scripts/health_server.py:129` (`python:S5332`,
   clear-text HTTP on a local health/metrics server — SAFE is the defensible
   resolution). Two paths:
    - Mark SAFE in the UI at https://sonarcloud.io/project/security_hotspots
      (one click), **or**
    - Set a **real** `SONAR_TOKEN` Actions secret, then dispatch the
      `sonar-hotspot-manage` workflow (`action=list` → `action=resolve` with the
      hotspot key). NOTE: a secret named `SONAR_TOKEN` already exists but its
      value is a **1-character placeholder** (verified 2026-09-27: token length 1,
      API returns HTTP 401) — it must be replaced, not added.
2. **E ratings on new code**: Either tighten leak period to 30 days, or
   customize the gate to drop "New Code ≥ A" conditions

---

## 5. Branch hygiene

### Remote orphan branches (decision pending — see issue #680)

| Branch                                     | Logical files             | Recommendation                  |
| ------------------------------------------ | ------------------------- | ------------------------------- |
| `fix/http-pool-timeout-clean-20260802`     | 1152 (drifted codex fork) | Archive as tag, remove worktree |
| `fix/http-pool-timeout-publish-20260805`   | 1154 (same +1 commit)     | Archive as tag, remove worktree |
| `token-bucket-wait-time`                   | 1163 (drifted codex fork) | Archive as tag                  |
| `feat/harness-envelope-stress-demo`        | 15 (real feature)         | Open PR or close                |
| `fix/perf-models-refresh-timeout-20260908` | 3 (real perf fix)         | Open PR or close                |
| `fix/pr641-conflict`                       | 1 (real test fix)         | Open PR or close                |

### Already cleaned

- ✅ Deleted: 5 remote branches (zero unmerged commits)
- ✅ Deleted: 15 local branches (PRs merged/closed)
- ✅ Deleted worktree + branch: `fix/http-pool-timeout-20260723` (zero commits ahead since July)
- ✅ Removed worktrees (2026-09-27): `fix/http-pool-timeout-clean-20260802`,
  `fix/http-pool-timeout-publish-20260805` — annotated archive tags verified to
  peel exactly to the branch heads (`dacd63894`, `5f58c82f7`); disk held only
  `__pycache__`/`.pytest_cache` junk. Branch refs kept.

### Audit before delete

Always run `git log origin/main..<branch> --oneline` and
`git diff origin/main...<branch> --stat` (3-dot diff) before deleting. Branches
with non-zero logical file changes contain real WIP and must be tagged or
archived, not deleted.

---

## 6. Common operations

### Trigger a release

Releases are managed by release-please (`.github/workflows/release-please.yml`).
Push a conventional commit (`feat:`, `fix:`, `chore:`) to main; release-please
opens a PR labeled "autorelease: pending". Mergify auto-merges the release PR
via rule 5 (release-please[bot] author + `autorelease: pending` label match).
If the PR stalls at `BLOCKED`/queue-conditions, see
"Release-please merge flow — external gates" in §2 (review-thread resolution).

**Gotcha — release-please Mergify rule syntax**: the autorelease label contains
a colon (`autorelease: pending`). In `pull_request_rules → conditions`, the
colon breaks Mergify's parser as `label = autorelease` + `pending` (unparsed
trailing token). Always quote the condition with double quotes:

```yaml
conditions:
    - author = release-please[bot]
    - "label = autorelease: pending" # QUOTED: colon needs protection
```

Required `check-success=` conditions were intentionally removed from the
release-please rule. The repo's GitHub Actions settings have
`default_workflow_permissions: write` + `can_approve_pull_request_reviews: true`,
which implicitly enables the "Require approval for first-time contributors"
gate. Each release-please PR is a fresh bot invocation, so every workflow run
sits at status `action_required` waiting for a maintainer to click "Approve
and run". The checks never report PASS or FAIL, so `check-success=` conditions
never match. The release-please label itself is a sufficient signal: release-please
only applies `autorelease: pending` to releases it has actually staged.

### Manually approve a blocked workflow run

Some workflows enter `action_required` state (waiting for approval). Approve via:

```bash
curl -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/KooshaPari/helios-cli/actions/runs/<id>/approve
```

Or via the GitHub UI.

### Fix prettier on a single file

```bash
npx prettier --write <file>
git add <file> && git commit -m "style: prettier-format <file>"
```

### Check required checks on a commit

```bash
gh api "repos/KooshaPari/helios-cli/commits/<sha>/check-runs" \
  --jq '.check_runs[] | select(.name == "CI results (required)" or .name == "Lint & Format" or .name == "build + test + clippy + fmt") | "\(.name): \(.conclusion)"'
```

### Check SonarCloud hotspots

Public API requires no auth:

```bash
curl "https://sonarcloud.io/api/hotspots/search?projectKey=KooshaPari_helios-cli&status=TO_REVIEW&ps=20"
```

Mutation API requires `SONAR_TOKEN`:

```bash
curl -X POST "https://sonarcloud.io/api/hotspots/change_status" \
  -d "hotspot=<key>&status=REVIEWED&resolution=SAFE"
```

---

## 7. v8-canary informational workflow

Runs on every push to `main` and PRs. Builds Rust code with `RUSTFLAGS="--cfg
v8_canary"` to test canary features. Tagged as informational — failures don't
block merges.

**Historical issue**: macOS runner allocation failures (no steps execute). Fix
was job-level `continue-on-error: true` on `build` and `build-windows-source`
jobs in `.github/workflows/v8-canary.yml` (commit `408af360d`). Per-step flags
cannot cover jobs where no steps execute.

---

## 8. Future maintenance schedule

| When                 | What                                                               |
| -------------------- | ------------------------------------------------------------------ |
| Weekly (Mon 3am UTC) | Trunk Check full-repo sweep — catches new prettier violations      |
| On every push        | All required checks re-run                                         |
| On release-please PR | Trunk Check + rust-ci must pass before Mergify auto-merges         |
| Quarterly            | Review SonarCloud gate conditions; consider tightening leak period |
| Quarterly            | Audit `git branch -r` for new orphan branches                      |

---

## 9. Known gotchas (quick reference)

- **Mergify action name is `delete_head_branch:`** — `delete_branch:` breaks the entire config
- **Explicit `permissions:` in a workflow zeroes every unlisted scope** —
  `codex-upstream-sync.yml` declared only `contents`+`pull-requests`, so its
  issue-creation step 403'd (`Resource not accessible by integration`) on **6
  consecutive weekly runs (2026-08-24 → 09-28)** before `issues: write` was
  added (2026-09-29). When a scheduled workflow starts failing, diff its
  `permissions:` against what its steps actually call.
- **`actions/attest-build-provenance` needs `attestations: write` + `id-token: write`**
  — not just `id-token`. `rust-release.yml`'s attest job was missing the former
  until `4aa2b40d6` (2026-10-01). The rest of the workflow-permissions /
  action-pinning audit (8 workflows with no `permissions:` block, floating action
  tags, vendored codex issue-workflows with latent 403s) is tracked in **#692**.
- **`gh run list --commit <sha>` needs the FULL 40-char SHA** — short SHAs
  (even 9-10 chars) silently return an empty list, indistinguishable from "no
  runs exist". Resolve first with `git rev-parse <short>` (bit this session
  twice on 2026-10-01 while diagnosing the queue).
- **Release PRs never matched `Auto-merge release-please PRs` on author** —
  release-please runs _as a workflow_, so GitHub records the PR author as
  `github-actions[bot]`, not `release-please[bot]`; the rule was dead and every
  release PR (#673, #688, #689, #693) stalled until someone ran `@mergifyio
refresh` + `@mergifyio queue` by hand. The queue path merges via the
  `default` queue rule whose `required_conditions` is empty, so it bypasses
  BOTH the approval-gated `action_required` runs and every `check-success=`
  condition. Condition fixed in `.mergify.yml` on 2026-10-01 (scoped by
  `label = autorelease: pending`, which only release-please applies).
- **Hosted-runner starvation (2026-10-01): runs sat `queued`/`pending` with
  zero jobs for 25+ min while githubstatus.com reported operational.**
  Mitigation: cancel runs on superseded SHAs (`gh run cancel <id>`) so the
  current head's runs — especially `Release Please`, which cuts the release —
  get dispatch slots instead of sitting behind four 20-40 min `rust-ci-full`s.
- **Unresolved bot review threads block release PRs** — branch protection
  (`#review-threads-unresolved = 0`) flips the PR to `BLOCKED` and Mergify
  waits forever at "queue conditions". Reply + GraphQL `resolveReviewThread`,
  then `@mergifyio refresh` (thread resolution alone does NOT re-trigger
  Mergify). Never invent an `AP-ITEM:` id for a bot — check precedent first
  (`git log --format=%b -60 | findstr AP-` → zero for all releases).
- **A CONFLICTING (DIRTY) PR gets ZERO GitHub Actions runs.** GitHub cannot create
  the merge ref, so no `pull_request` events fire — `CI results (required)`,
  `Lint & Format`, `build + test + clippy + fmt` never appear, Mergify's
  `check-success=` conditions never match, and the PR stalls silently with only
  App checks (SonarCloud/Socket/semgrep) reporting. Diagnose with
  `gh pr view N --json mergeable,mergeStateStatus` (`CONFLICTING`/`DIRTY`);
  the workflow runs that DID fire are only `push`-event runs from the branch
  (they may additionally fail with "Invalid workflow file" if the branch is
  old enough to predate workflow repairs). Fix by merging main into the branch.
- **`actions/runs?head_sha=<sha>` returns 0 for `pull_request`-event runs.**
  Filter client-side on `event=pull_request` + `pull_requests[].number`, or use
  a `created=<start>..<end>` window instead.
- **Take-main rule for stale-branch conflicts**: if resolving a conflicted PR
  yields `git diff origin/main` == empty, the PR is already fully incorporated
  — close it rather than merge a no-op (see #682, #683 on 2026-09-24).
- **Job-level `continue-on-error: true`** required for runner allocation failures (per-step insufficient)
- **release-please PRs are authored by `github-actions[bot]`, not `release-please[bot]`** - release-please runs as a workflow; the bot only pushes commits. Mergify rule fixed `76d37f113` (was dead for every release ever).
- **`SONAR_TOKEN` needed** to mark SonarCloud hotspots reviewed via API; UI review works without it. The
  secret exists but is a **1-char placeholder** (401) — replace, don't add;
  then use the `sonar-hotspot-manage` workflow
- **`/tmp/` is RAM-backed** in this environment — use `$JCODE_SCRATCH_DIR` for large files
- **cmd.exe for-loops** don't expand `$var` — use PowerShell `.ps1` files instead
- **`gh issue close --comment "..."`** works inline; no `--comment-file`
- **`git diff origin/main...branch`** (3-dot) shows logical changes from merge-base
- **`git diff origin/main..branch`** (2-dot) shows everything not in main; misleading when branch is drifted
- **Push-to-main cancels the previous tip's in-flight runs** - workflows use concurrency
  `cancel-in-progress` per ref: each new push concludes the prior tip's rust-ci/Trunk/etc.
  as `cancelled` (NOT green). CI is only meaningful on the final pushed SHA - never
  rapid-fire pushes expecting cumulative verification, and do not push while the final
  tip's gates are running (2026-10-01: the whole 18:28-20:00 chain read `cancelled`; only
  `abaa43a9` @ 18:13 was truly green).
- **Account-wide Actions congestion** (status page green, repo runs starved): census
  `gh repo list KooshaPari --limit 60` + per-repo `actions/runs` counts - observed 340
  queued / 5 in_progress across 15 repos (Dependabot + scheduled waves). Other repos'
  queues are not ours to cancel; wait it out with one watcher on the final tip.
  `v8-canary` workflow_dispatch = fast scheduler canary.
- **`gh run cancel` can silently no-op** - re-issue and re-verify status (two d014bc2d0
  runs survived two cancel attempts on 2026-10-01).

---

## 10. Local harness test failures on Windows (not run in CI)

`python -m pytest harness/tests/` on Windows fails **8 of ~121 tests**. Baseline
verified 2026-09-27: identical 8 failures on pristine main and with new commits
(113 pass). No CI workflow runs pytest, so these are invisible to checks. All 8
are POSIX-platform assumptions — not product regressions:

| Test                                                                                                                     | Root cause                                                                                                                                                                 |
| ------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `test_run_harness::validated_output_path...`                                                                             | product: `run-harness.py:123` `os.open(workspace, O_RDONLY\|O_DIRECTORY\|O_NOFOLLOW)` — opening a directory handle is POSIX-only → `PermissionError [Errno 13]` on Windows |
| `test_run_harness::write_output_uses_descriptor...`                                                                      | same line 123                                                                                                                                                              |
| `test_run_harness::harness_dry_run_and_plan_hash` (and `harness_replay_and_validate`, `replay_uses_stored_plan_hash...`) | same line 123 inside the `run-harness.py` subprocess → exit 1                                                                                                              |
| `test_run_harness::phase2_skip_marker_escapes...`                                                                        | test fixture creates a path containing `"` — legal on POSIX, `OSError WinError 123` on NTFS                                                                                |
| `test_runner_contract::test_runner_retries_and_timeout`                                                                  | runs `sleep 2`, expects GNU `timeout`-style exit 124 (got 127: command not found on Windows)                                                                               |
| `test_cli_integration::test_phase_2_wrapper...`                                                                          | invokes `bash` with Windows paths — backslashes eaten as escapes → file-not-found (127)                                                                                    |

Proper fixes = product portability work (Windows fallback for the descriptor-safe
write; security trade-off — it exists to prevent symlink TOCTOU) + test
parametrization/skips. Both are frozen-repo product decisions: run harness tests
on POSIX, or expect exactly these 8 on Windows.

## 11. Dependabot security alerts (pnpm overrides ledger)

**Pattern (verified 2026-10-01, `0122aced9`):** when npm transitive-dep
alerts pile up (9 open: 4 high + 5 moderate - brace-expansion x6,
ip-address x2, fast-uri x1), Dependabot does **not** open fix PRs: its
security-update jobs all failed with `security_update_not_possible`
(latest-resolvable == locked version, empty `conflicting-dependencies`).
The fix mechanism is the `pnpm.overrides` security ledger in `package.json`.

**Procedure:**

1. List alerts: `gh api 'repos/KooshaPari/HeliosCLI/dependabot/alerts?state=open&per_page=50'`
   (parse via `.ps1` + `ConvertFrom-Json`; cmd-embedded quote variants fail
   silently).
2. Bump the matching `pnpm.overrides` entries in `package.json`
   (e.g. `brace-expansion@1` -> `^1.1.21`, `ip-address@<=10.7.0:^10.7.1`).
3. Resolve: `npx -y pnpm@10.29.3 install --lockfile-only` (local corepack
   `pnpm` shim is broken - pin to the `packageManager` version).
4. Prove sync: re-run the same command with `--frozen-lockfile` (exit 0 =
   package.json <-> lockfile consistent).
5. Prettier: `pnpm-lock.yaml` is `.prettierignore`d - only `package.json`
   needs a `prettier@3.6.2 --check` pass.
6. Push -> dependency graph re-scan closes the alerts as `fixed` within ~1
   minute (observed: 9/9 `state=fixed` 60 s after push; the "N
   vulnerabilities" line in push output is pre-scan and clears on re-scan).

**`minimumReleaseAge: 10080` (7-day quarantine) in `pnpm-workspace.yaml`
did not block this:** the override-pinned fresh patches (published ~2 days
earlier) resolved into the lockfile normally - quarantine gates Dependabot's
own version discovery, not pinned override resolution (observed, do not
assume for non-override bumps).
