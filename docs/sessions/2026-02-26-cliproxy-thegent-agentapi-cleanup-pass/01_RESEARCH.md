# Research: Cleanup Pass (cliproxyapi-plusplus + thegent)

## Repository State at Session Time

### cliproxyapi-plusplus
- **Open PRs**: 30
- **Failure clusters**:
  - 21 PRs share: `Analyze (Go)`, `build`, `CodeRabbit`, `verify-required-check-names`
  - 2 PRs share: `Analyze (Go)`, `Build Docs`, `verify-required-check-names`
  - 2 PRs share: `Analyze (Go)`, `build` only
  - 3 CI-only PRs with permutation failures
  - 1 CR-clean pass (`#618`)

### thegent
- **Open PRs**: 8
- **Failure clusters**:
  - 4 PRs with broad infra failures (Build Docs, Build wheels, Comprehensive Benchmark, multi-platform Test)
  - 2 PRs with CodeRabbit-only failures (`#478`, `#494`) — re-reviewed
  - 2 pass-state PRs (`#493`, `#496`)

## GitHub CLI Commands Used

- `gh pr list -R <repo> --state open --json number,headRefName,title`
- `gh pr checks <n> -R <repo> --json name,state,bucket`
- `gh api repos/<repo>/branches/<url-encoded-branch>` for each open PR head
- Local branch scan vs open PR heads with upstream-ref audit
