# Ops — SOTA ({{PROJECT_NAME}})

## Use case

How this repo is built, tested, deployed, observed, and maintained in CI/CD and production (if applicable).

## Requirements

| Requirement | Weight |
|-------------|--------|
| PR CI completes in acceptable time budget | must |
| Default branch always green or explicitly quarantined | must |
| Template/doc changes have proportionate gates | must (genesis repos) |
| Runbooks for on-call (if production) | should |

## CI strategy (chosen)

| Change class | Gate |
|--------------|------|
| Docs / genesis markdown only | Link check; OKF validate (planned); **no full workspace build** |
| Language template change | Targeted smoke: `scripts/scaffold-smoke.sh`, per-lang `task quality` |
| Runtime code change | Full test matrix for affected packages |
| Governance doc change | Review agent charter/SOTA alignment |

```bash
# Example genesis-repo smoke — customize paths
./scripts/scaffold-smoke.sh --template {{LANG}}
```

## Alternatives considered

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| Full `cargo build` / monorepo test on every PR | thorough | HDD/lock cost; doc PR friction | rejected for genesis |
| No CI on templates | fast | silent breakage | rejected |
| Nightly only CI | cheap | broken main until next day | rejected |
| **Targeted smoke per changed template** | proportional signal | requires smoke script maintenance | **chosen** |

## Observability (if applicable)

| Signal | Tool | Owner |
|--------|------|-------|
| CI failures | GitHub Actions | repo maintainers |
| {{PROD_METRIC}} | {{TOOL}} | {{TEAM}} |

## Evolution triggers

- Smoke script false negatives → expand matrix row
- New language template added → register in smoke script + this doc
- Production SLO breach → add ops runbook section

Update [../../../SOTA.md](../../../SOTA.md) Ops row when strategy changes.
