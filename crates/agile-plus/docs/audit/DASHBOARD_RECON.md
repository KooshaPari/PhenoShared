# DASHBOARD_RECON — AgilePlus Rust Dashboard Inventory

**Date:** 2026-06-15  
**Scope:** Rust-based dashboard within `<REDACTED>/AgilePlus`  
**Branch examined (local):** `feat/agileplus-on-shared-core` (commit `19c5a551` — `wip: pre-consolidation checkpoint`)  
**Remote reference:** `main` branch (for template structure comparison)

---

## 1. Implementation Overview

The AgilePlus dashboard exists as **two parallel implementations** within the same crate (`crates/agileplus-dashboard/`):

| Layer | Tech | Target |
|-------|------|--------|
| **Server-rendered** | Rust + Axum + Askama + htmx | Full-featured kanban/plane/agent UI |
| **Client SPA** | React + TypeScript + Vite + Tailwind | Lightweight epic/story browser |

Both share the same backend state (`DashboardStore`) and API routes. The React SPA is served as a static asset alongside the Askama routes.

---

## 2. Local Checkout State

### Path
```
C:/Users/koosh/Dev/AgilePlus/crates/agileplus-dashboard/
```

### Rust Backend (Askama templates — all stubs)
All 21 template files exist at `C:/Users/koosh/Dev/AgilePlus/templates/{pages,partials}/` but contain only `<!-- placeholder -->`. The Askama structs in `templates.rs` define the full data model for all pages, but the HTML content has **not been committed** on this branch.

**Page templates (11):**
| Template | Struct | Purpose |
|----------|--------|---------|
| `pages/home.html` | `HomePage` | Workspace summary + project health |
| `pages/dashboard.html` | `DashboardPage` | **Kanban board** with health, projects, filter |
| `pages/feature-detail.html` | `FeatureDetailPage` | Feature detail: work packages, events, evidence bundles, media, reports |
| `pages/features.html` | `FeaturesPage` | Feature list |
| `pages/health.html` | `HealthPage` | Service health dashboard |
| `pages/events.html` | `EventsPage` | Event timeline |
| `pages/hub.html` | `HubPage` | Project hub/ecosystem browser |
| `pages/settings.html` | `SettingsPage` | General settings |
| `pages/settings-plane.html` | `PlaneSettingsPage` | **Plane.so sync configuration page** |
| `pages/settings-agents.html` | `AgentSettingsPage` | Agent pool/dispatch settings |
| `pages/settings-services.html` | `ServicesSettingsPage` | Service endpoint config |

**Partial templates (10):**
| Template | Struct | Purpose |
|----------|--------|---------|
| `partials/kanban.html` | `KanbanPartial` | **Kanban board** (HTMX-swappable) |
| `partials/wp-list.html` | `WpListPartial` | Work package list |
| `partials/feature-evidence.html` | `FeatureEvidencePartial` | Evidence gallery |
| `partials/feature-media.html` | `FeatureMediaPartial` | Media asset gallery |
| `partials/feature-reports.html` | `FeatureReportsPartial` | Coverage reports |
| `partials/health-panel.html` | `HealthPanelPartial` | Service health block |
| `partials/event-timeline.html` | `EventTimelinePartial` | Feature event timeline |
| `partials/agent-activity.html` | `AgentActivityPartial` | Real-time agent status |
| `partials/project-switcher.html` | `ProjectSwitcherPartial` | Multi-project selector |
| `partials/toast.html` | `ToastPartial` | Toast notification |

### Key Rust handlers (`src/routes/`)

| File | Routes | Features |
|------|--------|----------|
| `dashboard.rs` | `/dashboard`, `/kanban`, `/feature/{id}`, `/wp-list/{id}`, `/health`, `/events`, `/agent-activity`, `/project-switcher` | Working kanban via `build_kanban_cards()`, HTMX partial swaps, dynamic project switching |
| `pages.rs` | `/`, `/settings`, `/features`, `/events`, `/plane-settings`, `/agent-settings`, `/services-settings` | Full-page renders for all template views |
| `helpers.rs` | `build_kanban_cards()`, filters, project loading | Kanban card assembly by feature state |
| `pages.rs` | `plane_settings_page()` | Plane.so health check, sync mode, mapped coverage, config warnings |

### React SPA (`web/src/`)

| File | Purpose |
|------|---------|
| `web/src/main.tsx` | **Primary entry** — inline-styles, dark nav (`#1e293b`), white cards. Views: Dashboard, Epics, Stories, Evidence + Traceability. No kanban. |
| `web/src/App.tsx` | **Alternative entry** (not used by Vite) — Tailwind classes, `bg-gray-50` light background. Views: Dashboard, Epics, Stories, Evidence Gallery (PHASE2 stub). Uses Card/Badge/Pill components. Falls back to seed epic/story data. |
| `web/src/stores/agileplus.ts` | Zustand store for work packages |
| `web/src/hooks/useWorkPackages.ts` | Work package fetch hook |
| `web/src/components/` | Foundation (Button, Checkbox, Input, Radio, Select, Toggle) + Layout (Badge, Card, Modal, Pill, Toast) |
| `web/src/types/index.ts` | TypeScript type definitions (EvidenceItem, etc.) |
| `web/src/styles/globals.css` | Tailwind + CSS custom properties design tokens (neutral-50 background, not dark) |

---

## 3. Feature Assessment by Criteria

### ✅ Dark geist-y flat theme
**NOT PRESENT** in either implementation. 
- React `main.tsx`: Dark nav (`#1e293b`) but white card bodies on white page background.
- React `App.tsx`: `bg-gray-50` light theme with cyan-400 accent.
- Askama templates: All stubs, no CSS theme committed.
- **Brand visual concepts** (`assets/brand/src/agileplus-*-v6.html`) have dark-theme mockups but are not production templates.
- The term "geist" does not appear anywhere in the repo.

### ✅ Agent features
**PRESENT** in Askama layer:
- `AgentSettingsPage` template + `agent_settings_page()` handler: pool size (6), retry budget (3), dispatch mode ("balanced").
- `AgentActivityPartial` template + `agent_activity()` handler: lists agents (`spec-agent`, `impl-agent`) with status, task, last action.
- `process_detector.rs`: Real-time agent process detection (worktree, PID, uptime).
- `templates.rs`: `AgentView` struct with name, status, current_task, last_action, pid, worktree.
- Agent port trait in `agileplus-domain/src/ports/agent.rs`.

### ✅ Plane-sync UI page
**PRESENT** in Askama layer:
- `pages/settings-plane.html` template → `PlaneSettingsPage` struct (17 fields).
- `plane_settings_page()` handler: reads `PLANE_API_KEY`, `PLANE_WORKSPACE`, `PLANE_PROJECT`, `PLANE_API_URL`, `PLANE_WEB_URL`.
- Shows: workspace name/slug, API URL, web URL, API key hint, sync enabled/disabled, sync mode (bidirectional/one-way), connection status, health endpoints, feature/WP mapped coverage, config warnings.
- The `crates/agileplus-plane/` crate (24+ source files) provides the full Plane.so sync adapter (client, webhook inbound, outbound sync, state mapper, content hash, label sync, runtime, sync queue).

### ✅ Working kanban
**PRESENT** in Askama layer:
- `build_kanban_cards()` in `helpers.rs` — groups features by state into kanban columns.
- `KanbanPartial` template → HTMX-swappable kanban board.
- `DashboardPage` template → dashboard with embedded kanban.
- Route `/kanban` returns partial for HTMX or full page for direct navigation.
- Kanban route tests exist in both `routes/tests.rs` and `routes_tests.rs` (assert `kanban-board` in HTML).
- Note: The templates are stubs — the route logic and data structures are complete, but the HTML rendering layer is uncommitted.
- The `agileplus-api` crate also has a `cycle_kanban.html` template with a separate cycle-based kanban.

---

## 4. Per-Session / Card-Grid View

**NOT FOUND.** No occurrence of "per-session", "card-grid", "card_grid", or "session card" terminology exists anywhere in the repository (searched via `gh search code` across all branches). The `FeatureDetailPage` template has the closest equivalent — a detail view showing work packages, evidence bundles, media assets, and reports for a single feature, but it is not described as "per-session".

---

## 5. Branches Containing Dashboard Code

| Branch | Dashboard State |
|--------|----------------|
| **`feat/agileplus-on-shared-core`** (local) | Full Rust route + template struct layer, all templates are stubs. React SPA has inline-style light UI. |
| **`main`** | Same template listing (all stubs). Same Rust route layer. |
| **`snapshot-2026-06-07`** | Likely similar — not specifically checked. |
| **`forge/a-impl-graph`** | Contains `cycle_kanban.html` in `agileplus-api` crate (separate kanban board at `/cycles`). |
| **All other branches (~27 total)** | May contain partial work; the kanban route/struct layer is consistently present across branches since it's in `main`. |

---

## 6. Inventory Summary

| Component | Status | Implementation |
|-----------|--------|----------------|
| Dashboard overview page | Stub (routes + struct complete) | Askama |
| Kanban board (card layout) | **Route + logic complete**, template is stub | Askama + htmx |
| Feature detail (cards/grid) | Stub (routes + struct complete) | Askama |
| Plane.so settings page | **Route + struct complete**, template is stub | Askama |
| Agent settings page | Stub (routes + struct complete) | Askama |
| Agent status panel (live) | Stub (route + struct complete) | Askama |
| Service health page | Stub (routes + struct complete) | Askama |
| React SPA (light theme) | Functional but no kanban, no plane UI | React/TS |
| Brand concepts (dark theme) | Visual mockups only, not production | HTML/JS |
| per-session / card-grid view | **Not present anywhere** | — |
| Dark geist-y flat theme | **Not present** | — |

---

## 7. Conclusion & Recommendation

The `feat/agileplus-on-shared-core` branch on the local checkout at `C:/Users/koosh/Dev/AgilePlus/crates/agileplus-dashboard/` contains the **most complete Rust dashboard route layer** but:

1. **All Askama templates are stubs** (`<!-- placeholder -->`) — the dark-theme HTML content has not been committed.
2. **The React SPA is functional** but uses a light theme with inline styles, no kanban, and no Plane-sync UI.
3. **No dark geist-y flat theme** exists in committed code anywhere in the repo (only in brand concept HTML mockups in `assets/brand/src/`).
4. **No per-session or card-grid view** exists by any naming convention.
5. **The Plane-so UI page and agent features are structurally complete** on the Rust side (template structs, route handlers, data models) but lack the committed template HTML to render.

To get a working dark-themed dashboard, the Askama templates need to be authored (drawing from the brand concept designs), or the React SPA needs to be extended with a full dark theme, kanban board, and Plane-settings page.
