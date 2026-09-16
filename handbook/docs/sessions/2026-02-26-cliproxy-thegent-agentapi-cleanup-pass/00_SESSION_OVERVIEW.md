# Cleanup Pass: cliproxyapi-plusplus + thegent (2026-02-26)

## Execution result (live sweep completed)

- cliproxyapi-plusplus: 30 open PRs
- thegent: 8 open PRs
- All requested `@coderabbitai full review` comments for CodeRabbit-failing
  PRs were posted successfully.

## Failure clusters

- `cliproxyapi-plusplus`:
  - 21 PRs share `Analyze (Go) (go)`, `build`, `CodeRabbit`,
    `verify-required-check-names`
  - 2 PRs share `Analyze (Go) (go)`, `Build Docs`,
    `verify-required-check-names`
  - 2 PRs share `Analyze (Go) (go)`, `build` only
  - 3 CI-only PRs with `Analyze`, `build`,
    `verify-required-check-names` permutations
  - 1 CR-clean pass (`#618`)
- `thegent`:
  - 4 PRs with broad infra failures (`Build Docs`, `Build wheels`,
    `Comprehensive Benchmark`, multi-platform `Test`)
  - 2 PRs with CodeRabbit-only failures (`#478`, `#494`) now re-reviewed
  - 2 pass-state PRs (`#493`, `#496`)

## Deterministic action set

1. **Retry wave (immediate):** monitor `CR_ONLY_RETRY` PRs once Coderabbit
   drains.
2. **Cluster wave:** fix shared CI check manifest/gates for
   `cliproxyapi-plusplus` before touching per-feature logic.
3. **Hold/serialize:** thegent PRs with infra failures should be held until
   shared baseline gates are stable.
4. **Branch-risk guard:** avoid deleting local branches yet; no safe local
   prune candidates detected in current heuristic.

## Branch/reference health checks used

- `gh pr list -R <repo> --state open --json number,headRefName,title`
- `gh pr checks <n> -R <repo> --json name,state,bucket`
- `gh api repos/<repo>/branches/<url-encoded-branch>` for each open PR head
- local branch scan vs open PR heads with upstream-ref audit

## Output artifacts

- matrix CSV:
[/Users/kooshapari/CodeProjects/Phenotype/repos/phenodocs/docs/sessions/2026-02-26-cliproxy-thegent-agentapi-cleanup-pass/cleanup_matrix.csv]

## Next step

Run: `python` script or command sequence to resolve `CI_ONLY` clusters, then
return here for PR-by-PR re-queue after each successful green lane.
