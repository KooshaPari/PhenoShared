# SOTA dimensional research — {{PROJECT_NAME}}

Each file documents **why our approach wins** against alternatives for one dimension.

| File | Dimension |
|------|-----------|
| [technical.md](technical.md) | Architecture, algorithms, performance |
| [dx.md](dx.md) | Developer experience, CLI, local dev |
| [ux.md](ux.md) | End-user experience (if applicable) |
| [ax.md](ax.md) | Agent experience (Cursor, forge, Codex, Claude) |
| [security.md](security.md) | Threat model, compliance |
| [ops.md](ops.md) | Deploy, observe, maintain |
| [cost.md](cost.md) | Infra, API, maintenance cost |
| [alternatives.md](alternatives.md) | Master comparison index |
| [fork-rationale.md](fork-rationale.md) | Required if fork |

## Research standard

Each dimension file must include:

1. Weighted requirements
2. ≥3 alternatives (OSS + closed where relevant)
3. Verdict table with rejection reasons
4. Evolution triggers

PRs that introduce new dependencies must update the relevant dimension or add an ADR linked from [alternatives.md](alternatives.md).
