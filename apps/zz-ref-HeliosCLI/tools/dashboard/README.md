# Helios Dashboard

UI components for visualizing routing decisions in helios-cli.

**Migrated from:** `KooshaPari/helios-router/.archive/dashboard/` (2026-06-18)
**Status:** Reference / aspirational — not yet wired into helios-cli's runtime

## Components

- `src/components/RoutingTable.tsx` — Tabular view of routing decisions (provider, model, cost, latency)
- `src/components/ParetoChart.tsx` — Pareto frontier of cost vs quality
- `src/data/mockData.ts` — Mock data for development
- `src/data/mockData.test.ts` — Tests for mock data shape
- `src/App.tsx` — Root component
- `src/App.css` / `src/index.css` — Styling

## Dependencies (to add)

- React 18+
- Vite (or Next.js)
- A charting library (e.g. Recharts, D3)

## Integration Plan

These components are intended for the `helios route visualize` command (TBD). They were migrated here from helios-router before that repo was archived. The current shell is a static reference; wiring to a build system is a future task.
