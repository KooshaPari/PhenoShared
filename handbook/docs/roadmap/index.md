# Roadmap

Rich roadmap: **themes**, **phases**, and **signals**—not a flat bullet list alone.

## Vision

PhenoDocs becomes the **federated cockpit** for plan / research / spec / work artifacts, plus **changelog**, **commit history**, and **WBS/DAG**—with data optionally generated from repos and CI.

## Horizon

| Horizon | Focus | Outcomes |
|---------|--------|----------|
| **Now** | IA + workspace views hub | [Views](/views/), [commit log](/views/commits), [plan](/planning/rich-workspace-views), build fixes (`audit-log`, `srcDir`) |
| **Next** | Generated JSON | `commit-log.json`, changelog slices, roadmap data from manifests |
| **Later** | Federation + graphs | Cross-repo plan/spec embeds, DAG visualization, richer search |

## Past (baseline)

- Initial federation hub and governance docs
- Stacked PRs / WBS documentation

## Current

- Documentation IA unification
- Rich workspace views ([spec](/planning/rich-workspace-views))
- API and SDK surface consolidation (see [API](/reference/api))

## Program themes (parallel tracks)

1. **Content:** Plan / research / spec / work **modules** tied to [document index](/index/) buckets.
2. **Shipping:** [Changelog](/views/changelog) + version story per federated package.
3. **Engineering:** [Commit log](/views/commits) + audit trail (`AuditTimeline`).
4. **Structure:** [WBS & DAG](/views/wbs) aligned with governance.

## Next milestones

- Cross-repo docs federation and richer search
- Automated doc index generation and freshness checks
- CI pipeline to refresh `commit-log.json` and changelog JSON on merge
