# phenodocs Implementation Plan

**Status:** Active
**Stack:** VitePress, Node.js (bun), Python (scripts)

## Phase 1: Site Foundation

| Task | Description | Depends On |
|------|-------------|------------|
| P1.1 | VitePress config with keycap theme from @phenotype/design | done |
| P1.2 | Build script to fetch docs from source repos | -- |
| P1.3 | Auto-generated sidebar from directory structure | P1.2 |

## Phase 2: Federation

| Task | Description | Depends On |
|------|-------------|------------|
| P2.1 | Configure 10+ source repo fetch targets | P1.2 |
| P2.2 | Layered content routing (lab, docs, audit, kb) | P1.3 |
| P2.3 | Full-text search configuration | P1.1 |

## Phase 3: AI Integration

| Task | Description | Depends On |
|------|-------------|------------|
| P3.1 | .llms.txt generator script | P2.1 |
| P3.2 | Per-section structured summaries | P3.1 |

## Phase 4: CI/CD

| Task | Description | Depends On |
|------|-------------|------------|
| P4.1 | GitHub Actions deploy workflow | P1.1 |
| P4.2 | Automated rebuild on source repo changes | P4.1, P2.1 |
| P4.3 | Build failure handling for unreachable sources | P1.2 |
