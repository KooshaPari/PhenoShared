# DESIGN.md — phenotype-org-audits

## Overview

**phenotype-org-audits** is the organization-level audit and governance repository for the phenotype ecosystem. It tracks audit scores, pillar coverage metrics, and maintains the work-DAG for cross-repo coordination.

## Architecture

```
phenotype-org-audits/
├── audits/                # Audit results and scoring data
├── audit-30-pillar/       # 30-pillar audit framework
├── audit-v38/             # Audit version 38 data
├── findings/              # Identified issues and remediation
├── plans/                 # Remediation and migration plans
├── imports/               # Cross-repo audit data imports
├── docs/                  # Audit methodology documentation
├── work-dag*.md           # Work DAG files (DAG-based task scheduling)
├── worklog.md             # Audit work log
└── *.py                   # Audit utility scripts
```

## Key Design Decisions

1. **30-pillar framework** — comprehensive scoring across 30 quality dimensions per repo
2. **Work-DAG model** — tasks represented as directed acyclic graphs for dependency-aware execution
3. **Scorecard-driven** — quantitative quality gates enforced across the polyrepo
4. **Audits-as-data** — machine-readable audit results for automated remediation

## Data Flow

```
Repo Scan → Audit Script → Score Calculation → Scorecard (JSON) → Findings → Work-DAG → Remediation Plan
```

## Non-Goals

- Individual repo code quality enforcement (each repo has its own gates)
- Security vulnerability scanning (handled by Trivy/Gitleaks per repo)
- Business logic auditing (strictly code quality and governance)

## Status

- Multiple audit versions (v38 active)
- Monitoring dashboards for ongoing audit coverage
- Secret rotation policies tracked

## References

- [AGENTS.md](./AGENTS.md) — LLM contributor guidelines
- [SSOT.md](./SSOT.md) — Single source of truth for audit methodology
- [MONITORING.md](./MONITORING.md) — Monitoring and alerting configuration
