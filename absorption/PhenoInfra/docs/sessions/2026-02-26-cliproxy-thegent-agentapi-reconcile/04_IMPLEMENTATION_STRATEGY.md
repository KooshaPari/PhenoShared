# Implementation Strategy: PR Reconciliation Audit (v1)

## Technical Approach

Use the GitHub CLI (`gh`) to enumerate and classify open PRs across target repos.

## Architecture Decisions

| Decision | Rationale | Alternative Considered |
|----------|-----------|----------------------|
| Use `gh pr list` | Structured JSON output, easy to parse | Direct GitHub API via curl |
| Shell scripting | Sequential, simple, auditable | Python wrapper |

## Code Organization

Single-script approach using `gh` CLI for all PR enumeration and classification.

## Performance

- Sequential `gh pr list` calls per repo.
- No rate limiting expected for typical PR counts.
- Shell `grep`/`jq` for classification.
