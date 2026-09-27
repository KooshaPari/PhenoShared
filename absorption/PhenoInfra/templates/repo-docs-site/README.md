# repo-docs-site template

Reusable 4-quadrant docs site scaffold extracted from the OmniRoute pilot
(phenodocs-baseline pattern, 2026-09-02).

## Layout

- vitepress-config.mts.example — copy to <repo>/.vitepress/config.mts, edit title/base/nav
- demo/ — gui-walkthrough.ts, stress.ts, on-device.sh (copy to <repo>/demo/)

## Quadrants

- docs-site/getting-started/ (index, install, quickstart, on-device, deploy)
- docs-site/architecture/ (index, ADRs, repository map, cluster decisions)
- docs-site/reference/ (index, API, provider manifest, env, flags, CLI)
- docs-site/operations/ (index, runbook, incident response, perf, cost, threat model, backlog)
- docs-site/demo/ (index, GUI, stress test, on-device)

## Use

1. Copy docs-site/ quadrant dirs from a completed pilot (OmniRoute, CivicSurvival-public)
2. Copy .vitepress/config.mts and rewrite title/base/nav for the repo
3. Add package.json scripts: docs:dev, docs:build, demo:gui, demo:stress, demo:on-device
4. bun install vitepress, run bun run docs:dev, verify HTTP 200 on each quadrant root
