# Alternatives index — {{PROJECT_NAME}}

Master comparison index across SOTA dimensions. PRs that change strategic choices must update the relevant dimension file **and** this index.

## Dimension decisions

| Dimension | File | Decision (one line) | Confidence |
|-----------|------|---------------------|------------|
| Technical | [technical.md](technical.md) | {{TECH_DECISION}} | {{H/M/L}} |
| DX | [dx.md](dx.md) | {{DX_DECISION}} | {{H/M/L}} |
| UX | [ux.md](ux.md) | {{UX_DECISION or N/A}} | {{H/M/L}} |
| AX | [ax.md](ax.md) | Genesis doc set + OKF + scraper | {{H/M/L}} |
| Security | [security.md](security.md) | Kilo Code Stand + template scanners | {{H/M/L}} |
| Ops | [ops.md](ops.md) | Targeted template smoke | {{H/M/L}} |
| Cost | [cost.md](cost.md) | {{COST_DECISION}} | {{H/M/L}} |

Executive summary: [../../../SOTA.md](../../../SOTA.md)

## Cross-cutting alternatives

| Decision | Alternatives rejected | Primary reason | ADR link |
|----------|----------------------|----------------|----------|
| {{DECISION_1}} | {{ALT_A}}, {{ALT_B}} | {{REASON}} | {{ADR or "—"}} |
| {{DECISION_2}} | … | … | … |

## Fork repos

If this project is a fork, maintain detailed upstream comparison in [fork-rationale.md](fork-rationale.md) and add a row here:

| vs upstream | Our fork wins when… | Upstream wins when… |
|-------------|---------------------|---------------------|
| {{UPSTREAM_NAME}} | {{FORK_WINS}} | {{UPSTREAM_WINS}} |

## Research refresh log

| Date | Researcher | Dimensions updated | Notes |
|------|------------|-------------------|-------|
| {{DATE}} | {{AUTHOR}} | all (bootstrap) | Initial genesis template |

## Enforcement

[review.md](../../../review.md) Block tier: new dependencies or architectural shifts without updating this index or an linked ADR → fail PR.
