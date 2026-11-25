# Cost — SOTA ({{PROJECT_NAME}})

## Use case

Total cost of ownership: infrastructure, API usage, CI minutes, maintainer time, and **duplicate governance** across repos.

## Requirements

| Requirement | Weight |
|-------------|--------|
| Minimize duplicate doc/CI copies across fleet | should |
| CI cost proportional to change type | must |
| Avoid N× Kit repo pattern without justification | must (Phenotype org) |

## Comparison model

| Model | Governance copies | CI / maintenance | Verdict |
|-------|-------------------|------------------|---------|
| {{ALT_MODEL_1 — e.g. per-domain Kit repos}} | N× charter/review/SOTA | N× workflows | rejected — audit drift |
| {{ALT_MODEL_2 — e.g. monolith everything}} | 1× | heavy coupling | rejected |
| **{{OUR_MODEL — e.g. genesis template + SDK split}}** | 1 template + product copies | targeted smoke | **chosen** |

Fill with real numbers where available:

| Cost driver | Monthly estimate | Notes |
|-------------|------------------|-------|
| GitHub Actions minutes | {{ESTIMATE}} | doc-only PRs use light jobs |
| Cloud / API | {{ESTIMATE}} | |
| Maintainer hours (governance) | {{ESTIMATE}} | scraper + synthesis cadence |

## Alternatives considered

| Alternative | Cost profile | Verdict |
|-------------|--------------|---------|
| Duplicate `*Kit` archived repos | High — 9× governance per audit | rejected |
| SaaS doc portal only | subscription + lock-in | rejected |
| **Shared HexaKit genesis + optional SDK monorepos** | Lower — single scrape/review standard | **chosen** |

## Chosen strategy

{{COST_RATIONALE — tie to charter boundary class and intent goals}}

Example (HexaKit genesis): consolidating templates and genesis docs into HexaKit while domain libraries move to SDK workspaces reduces duplicate CI and agent context size.

## Evolution triggers

- SDK monorepo exceeds ~30 packages → evaluate feature-group publishing (not new Kit repos)
- CI minutes exceed budget → tighten smoke matrix
- Fleet doubles → automate OKF validate in CI

Update [alternatives.md](alternatives.md) when cost model changes.
