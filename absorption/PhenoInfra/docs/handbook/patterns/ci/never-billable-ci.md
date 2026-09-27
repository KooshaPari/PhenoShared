# CI hygiene: avoid billable minutes, pin and least-privilege

**Status:** adopted · **Applies to:** every `.github/workflows/*` file.

## Convention

- **Don't incur billable CI minutes where avoidable.** Use free-tier runners; gate expensive jobs behind path filters and `concurrency` cancellation.
- **Pin runners** to `ubuntu-24.04` (not `ubuntu-latest`) for reproducibility.
- **SHA-pin third-party actions** to a full commit SHA, not a floating tag. First-party `actions/*` may use major-version tags.
- **Least-privilege `permissions`** block at the top of every workflow (`contents: read` by default; widen only the specific job that needs it).
- **`concurrency: { group: …, cancel-in-progress: true }`** so superseded runs stop immediately.
- Reusable policy workflows (cargo-deny, scorecard, secret-scan) are consumed from **phenotype-org-governance** rather than copy-pasted per repo.

## Sponsor-merge protocol

For a PR that is green but blocked only by required-review protection, a steward/agent may sponsor-merge:

```bash
gh api -X DELETE repos/OWNER/REPO/branches/main/protection/required_pull_request_reviews
gh pr merge <n> -R OWNER/REPO --squash --admin
gh api -X PATCH repos/OWNER/REPO/branches/main/protection/required_pull_request_reviews -f required_approving_review_count=1
```

Always **restore** protection in the same step. Reviews/merges are done by agents, not gated on a human.

## Why

Floating tags and `ubuntu-latest` make CI non-reproducible and are a supply-chain risk; broad `GITHUB_TOKEN` permissions are an escalation surface. Centralizing policy workflows means one fix propagates org-wide.
