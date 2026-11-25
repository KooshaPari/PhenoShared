# AgilePlus UI Architecture

Status: Draft specification (architecture, interfaces, data flow — no implementation in this PR).
Owners: AgilePlus platform team.
Scope: in-tree Rust UI server, plugin/frontend surfaces, static single-file per-project
status generator, and the local multi-project dashboard app.

---

## 0. Why this document exists

AgilePlus today already ships a working dashboard (`crates/agileplus-dashboard`, Axum +
templates/, htmx + Alpine.js + SSE) and a Plane.so sync adapter
(`crates/agileplus-plane`). However, four requirements are not yet described as a
single, coherent architecture:

1. A **canonical server-rendered Rust UI** that all frontends plug into (templating
   engine, layout, asset pipeline, crate layout).
2. A **plugin/frontend contract** so that Tracera (traceability view), Planify
   (planning/roadmap view) and a Plane-clone (issue / project-management board) can
   be mounted as first-class surfaces in the same UI without forking it.
3. A **static, single-file per-project generator** that emits one `.html` with
   embedded JS, where the embedded JS re-reads the project's file/SQLite state on
   each refresh. No live server is required to view project status.
4. A **local server/app** that exposes the same view across every active
   AgilePlus-using project on the device (one dashboard over all of them).

This document specifies all four. It does not implement them.

---

## 1. Terminology

| Term              | Definition                                                                 |
|-------------------|----------------------------------------------------------------------------|
| Project           | A tracked codebase using AgilePlus (e.g. the `AgilePlus` repo itself).     |
| Active Project    | A project whose `agileplus.db` / `kitty-specs/` is currently registered.   |
| Session           | A live UI render (browser tab, Electron window, etc.).                     |
| Plugin            | A first-class UI surface (Tracera / Planify / Plane-clone) registered via `agileplus-plugin-core`. |
| Frontend Surface  | A UI page or partial contributed by a plugin.                              |
| Server-Render     | HTML produced by a Rust handler and sent complete to the browser (no SPA). |
| Static-Gen        | A pre-rendered `.html` artifact with no live backend dependency.           |
| Refresh-Driven    | State is fetched **at page load** (or F5) by JS reading local files/DB.    |

---

## 2. Current in-tree reality (baseline we extend)

This section grounds the spec in what already exists in this branch.

- `crates/agileplus-dashboard/` — Axum-based dashboard server.
  - `src/main.rs` — binds `127.0.0.1:3000` (configurable via `AGILEPLUS_DASHBOARD_PORT`),
    mounts `/static` from `templates/static`, exposes the routes in
    `src/routes/mod.rs` (e.g. `/dashboard`, `/api/dashboard/kanban`,
    `/api/dashboard/projects/{id}/activate`, `/api/stream`).
  - `src/templates.rs` — one Askama `#[derive(Template)]` struct per template file
    (`pages/home.html`, `pages/dashboard.html`, `partials/kanban.html`, …).
  - `Cargo.toml` declares `askama = "0.12"` and `axum = "0.8"`, with the askama
    template root pointing at `templates/` via `[package.metadata.askama]`.
- `templates/base.html` — global layout with nav, sidebar, SSE wrapper, htmx +
  Alpine.js + htmx-sse `<script>` includes from `/static/`.
- `templates/pages/`, `templates/partials/`, `templates/static/` — pages, reusable
  fragments, and shipped JS/CSS assets (htmx, htmx-sse, alpine, style.css).
- `crates/agileplus-plane/` — Plane.so bidirectional sync (issues ↔ AgilePlus
  features), webhook ingestion, state mapping, conflict detection, retry queue.
- `crates/agileplus-plugin-core/` — reserved crate for the plugin trait surface.
- `crates/agileplus-domain/` — domain entities (Feature, WorkPackage, Module,
  Cycle, Project, FeatureState).
- `crates/agileplus-sqlite/` — local SQLite repository (the project's source of
  truth for status).

The architecture below reuses every one of these.

---

## 3. Goals & non-goals

### 3.1 Goals

- One Rust crate owns UI server-render. Plugins mount into it.
- Templates are written in a **server-side templating language** (see §4.1 for
  the Handlebars vs Askama decision and migration path).
- Static generation produces a **single self-contained `.html`** per project that
  renders fresh project status on every refresh.
- A **local server/app** lists every AgilePlus-using project on the device and
  surfaces the same view across all of them.

### 3.2 Non-goals (this spec)

- Replacing Askama in one step. Migration is incremental (§4.1).
- Building a full SPA. We deliberately stay server-rendered + htmx + Alpine.
- Adding a live WebSocket pipeline beyond the existing SSE channel.
- Changing SQLite schema or domain entities.
- Implementing any of the frontends. This spec only defines the contract.

---

## 4. AgilePlus's own Rust + server-render UI

### 4.1 Templating engine: Handlebars vs Askama

The existing in-tree UI uses **Askama 0.12** (Jinja-style, type-checked at compile
time, see `crates/agileplus-dashboard/Cargo.toml` line 16). The task brief
references "Handlebars." This spec therefore defines the architecture to be
**engine-agnostic at the template level** but commits to two implementations:

| Concern                | Askama (current)                                 | Handlebars (target)                                            |
|------------------------|--------------------------------------------------|----------------------------------------------------------------|
| Crate                  | `askama = "0.12"`                                | `handlebars = "6"` + `handlebars-rust` helpers                  |
| Syntax                 | `{% block %}`, `{{ field }}`, `{% for %}`        | `{{field}}`, `{{#each}}`, `{{#if}}`                            |
| Type checking          | Yes, via `#[derive(Template)]` + struct fields   | No — runtime context with JSON value                          |
| Helpers                | Methods on context struct, registered via `#[template]` | `handlebars.register_helper(...)`                       |
| Partials               | `{% include "partials/foo.html" %}`              | `{{> partials/foo }}`                                          |
| Existing use           | `templates/pages/*.html`, `templates/partials/*.html` | None yet — greenfield                                      |

**Decision.** We extend the **Askama** path for the existing dashboard
(because every existing page already uses it and Askama is type-checked). We
add a **Handlebars adapter** in `agileplus-dashboard` specifically for the
**plugin-rendered surfaces** (Tracera, Planify, Plane-clone), because those
plugins ship their own templates and need the engine-agnostic `{{var}}` /
`{{#each}}` syntax Handlebars is famous for. The shared template root for
plugins is `templates/plugins/<plugin-id>/`.

Both engines render into the same `base.html` shell so the plugin surfaces look
identical to the native ones.

### 4.2 Server-render approach

```
┌──────────────────────────────────────────────────────────────────────┐
│ Browser / desktop shell (htmx + Alpine.js + tiny CSS)                │
│                                                                      │
│   ┌───────────────┐    htmx GET/POST     ┌────────────────────────┐  │
│   │  Page         │ ───────────────────▶ │ Axum router            │  │
│   │  (HTML)       │ ◀─────────────────── │ agileplus-dashboard    │  │
│   └───────────────┘   HTML partials       │                        │  │
│                              + SSE        │  ┌──────────────────┐  │  │
│                                            │  │ Plugin registry  │  │  │
│                                            │  │  Tracera view    │  │  │
│                                            │  │  Planify view    │  │  │
│                                            │  │  Plane-clone     │  │  │
│                                            │  └──────────────────┘  │  │
│                                            │  ┌──────────────────┐  │  │
│                                            │  │ Askama + HB      │  │  │
│                                            │  │ renderers        │  │  │
│                                            │  └──────────────────┘  │  │
│                                            └────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

Rules:

- **Server-render is the source of truth.** Every full page and every partial is
  rendered server-side. The browser receives a complete HTML document (or a
  complete HTML fragment for htmx swaps).
- **htmx + Alpine.js are the only client-side frameworks.** No React/Vue/Svelte.
  This keeps the asset surface ≤ 4 JS files (`htmx.min.js`, `htmx-sse.js`,
  `alpine.min.js`, `app.js`).
- **Server-Sent Events** carry live updates (`/api/stream`) — already wired via
  `hx-ext="sse"` in `templates/base.html:63`.
- **Same handler, two outputs.** A request with `HX-Request: true` returns only
  the inner partial; otherwise the same handler returns a full page rendered
  into `base.html`. This is the existing helper pattern (`routes/helpers.rs`).
- **CSS is one file.** `templates/static/style.css` (Tailwind-flavoured utility
  classes; no build step required — utility classes are already hand-authored).
- **No client-side state store.** UI state is encoded in URLs (project id,
  filter, page) and re-read on every request. This is the foundation that makes
  static-gen (§6) trivially possible.

### 4.3 Crate layout

```
crates/
  agileplus-dashboard/                # server-render engine + UI shell
    src/
      main.rs                         # CLI: agileplus ui serve [--port 3000]
      app_state.rs                    # existing — SharedState, DashboardStore
      routes/
        mod.rs                        # existing router
        pages.rs                      # existing
        dashboard.rs                  # existing
        features.rs                   # existing
        evidence.rs                   # existing
        agents.rs                     # existing
        health.rs                     # existing
        settings.rs                   # existing
        plugins.rs                    # NEW: /plugins/{id}/* dispatch
      plugins/
        mod.rs                        # NEW: PluginRegistry + Plugin trait
        tracera.rs                    # NEW: Tracera adapter (read-only at first)
        planify.rs                    # NEW: Planify adapter
        plane_clone.rs                # NEW: Plane-clone adapter
      render/
        askama.rs                     # NEW: thin wrapper over existing Askama
        handlebars.rs                 # NEW: Handlebars context + helper registry
      static_gen/
        mod.rs                        # NEW: per-project static .html emitter
        embedded_js.rs                # NEW: JS that re-reads state at refresh
        sqlite_bridge.rs              # NEW: JS-callable snapshot index file
    Cargo.toml                        # + handlebars, + serde_json (already)
    web/                              # existing storybook/dev preview (kept)
    desktop-electrobun/               # existing desktop shell (kept)
    askama.toml                       # existing — template root

crates/agileplus-plugin-core/         # trait crate (stable surface for plugins)
  src/
    lib.rs                            # Plugin trait + PluginContext + Page
    context.rs                        # read-only view of SharedState + DB
    page.rs                           # Page descriptor (route, title, renderer)
    static_gen.rs                     # trait for static-gen contribution

crates/agileplus-plane/               # existing — keep, extended by Plane-clone
crates/agileplus-domain/              # existing — source of truth for entities
crates/agileplus-sqlite/              # existing — sole DB read/write path
crates/agileplus-trace-validator/     # existing — consumed by Tracera plugin
```

Cross-cutting dependencies:

- `agileplus-dashboard` depends on `agileplus-plugin-core`, `agileplus-domain`,
  `agileplus-sqlite`, `agileplus-plane` (existing) and **dynamically loads**
  plugin crates (built-in plugins are static-linked via `pub mod`; third-party
  plugins can be `dlopen`-ed in a later spec).
- `agileplus-plugin-core` depends on `agileplus-domain` only. No DB, no HTTP.
- Tracera, Planify and Plane-clone plugins **do not** depend on each other or
  on `agileplus-dashboard` internals — only on `agileplus-plugin-core`.

---

## 5. Plugin / frontend surfaces (Tracera, Planify, Plane-clone)

### 5.1 The plugin trait

```rust
// crates/agileplus-plugin-core/src/lib.rs
pub trait Plugin: Send + Sync {
    /// Stable id used in URLs: /plugins/{id}/...
    fn id(&self) -> &'static str;

    /// Human label shown in nav.
    fn label(&self) -> &'static str;

    /// Icons / nav ordering.
    fn nav(&self) -> PluginNav;

    /// Routes this plugin contributes. Each route is server-rendered.
    fn routes(&self) -> Vec<PluginRoute>;

    /// Optional static-gen contribution (see §6).
    fn static_gen(&self) -> Option<Box<dyn StaticGen>> { None }
}

pub struct PluginRoute {
    pub path: String,                 // e.g. "/tracera/feature/{slug}"
    pub method: Method,
    pub engine: TemplateEngine,       // Askama | Handlebars
    pub template: &'static str,       // "pages/tracera/feature.html"
    pub handler: fn(PluginContext) -> PluginResponse,
}

pub enum TemplateEngine { Askama, Handlebars }
```

`PluginContext` is a read-only view:

```rust
pub struct PluginContext {
    pub project: ProjectSnapshot,     // active project + path
    pub db: SqliteReadHandle,         // read-only handle to agileplus.db
    pub url_params: HashMap<String, String>,
    pub query: HashMap<String, String>,
    pub flash: Option<FlashMsg>,
}
```

This guarantees plugins cannot mutate DB state during a render. Mutations
require the existing POST handlers (`/api/features/{id}/transition`,
`/api/settings/*`, etc.).

### 5.2 Tracera view

**Purpose.** Visualise the trace graph for the active project: FRs → features →
work-packages → evidence bundles → commits/PRs/CI runs. Lives over the
existing `agileplus-trace-validator` crate.

**Surface.**

| Route                              | Engine     | Template                                |
|------------------------------------|------------|-----------------------------------------|
| `GET /plugins/tracera`             | Handlebars | `pages/tracera/index.html`              |
| `GET /plugins/tracera/feature/{slug}` | Handlebars | `pages/tracera/feature.html`         |
| `GET /plugins/tracera/graph.json`  | —          | (returns JSON of nodes/edges for SVG)   |

**Data flow.**

```
PluginContext.project
  → trace_validator::build_graph(project) -> TraceGraph { nodes, edges }
  → render Handlebars context with TraceGraphView
  → return PluginResponse::Html(...)
```

The graph is also exposed as JSON so that a small in-page SVG renderer (pure
DOM, no extra library) can re-draw the trace graph on the client. This is
still server-render first; SVG is a progressive enhancement.

**Plugin status.** Read-only at first. Static-gen (§6) emits a Tracera
snapshot embedded in the per-project `.html`.

### 5.3 Planify view

**Purpose.** A planning/roadmap surface: cycles, modules, upcoming features,
estimated vs. shipped. Lives over `agileplus-domain` Cycle + Module entities.

**Surface.**

| Route                          | Engine     | Template                              |
|--------------------------------|------------|---------------------------------------|
| `GET /plugins/planify`         | Handlebars | `pages/planify/index.html`            |
| `GET /plugins/planify/cycle/{n}` | Handlebars | `pages/planify/cycle.html`          |
| `GET /plugins/planify/roadmap.json` | —    | (returns JSON timeline)                |

**Data flow.**

```
PluginContext.db
  → cycles.list() + modules.list() + features.for_cycle(c)
  → render Handlebars timeline view (Gantt-ish bars via CSS grid)
  → return PluginResponse::Html(...)
```

Edits (creating a cycle, moving a feature) go through the existing
`agileplus-api` JSON endpoints; the Planify view itself is read-only.

### 5.4 Plane-clone (issue / PM board)

**Purpose.** A native AgilePlus issue / project-management board that mirrors
Plane.so's UX (cycles, modules, kanban, sub-issues) without depending on a
Plane.so account. Lives over `agileplus-plane`'s domain types but does **not**
require Plane connectivity.

**Surface.**

| Route                              | Engine     | Template                              |
|------------------------------------|------------|---------------------------------------|
| `GET /plugins/plane/board`         | Askama     | `pages/plane/board.html`              |
| `GET /plugins/plane/issue/{id}`    | Askama     | `pages/plane/issue.html`              |
| `POST /api/plane/issues/{id}/transition` | —    | existing feature transition handler   |
| `GET /plugins/plane/cycles.json`   | —          | JSON                                  |

**Data flow.**

```
Native:  AgilePlus features ↔ Plane-clone cards (one-to-one)
Sync:    if Plane sync is enabled → use agileplus-plane as the adapter
         if disabled             → purely local (Plane-clone becomes the surface)
```

`agileplus-plane` continues to be the adapter; the Plane-clone plugin reads
the same SQLite tables the adapter writes to, so the two stay consistent
without a new write path.

**Why Askama here.** The Plane-clone board is dense, type-checked, and lives
next to the existing kanban partial — using Askama reuses the existing
`KanbanPartial`/`FeatureView` types in `crates/agileplus-dashboard/src/templates.rs:67`.

### 5.5 How plugins mount into the shell

`agileplus-dashboard::plugins::mod.rs` exports a `PluginRegistry`:

```rust
pub struct PluginRegistry {
    plugins: Vec<Box<dyn Plugin>>,
}

impl PluginRegistry {
    pub fn builtins() -> Self { /* Tracera, Planify, Plane-clone */ }
    pub fn mount(&self, router: Router) -> Router { /* adds /plugins/{id}/* */ }
}
```

`main.rs` builds the registry, mounts it, and writes the nav entries into
`base.html` via a new `{% for plugin in registry.nav() %}` block that
iterates plugin nav descriptors.

Each plugin ships:

- Its templates under `templates/plugins/<id>/` (Handlebars) or
  `templates/pages/<id>/` (Askama).
- Its static assets under `templates/static/plugins/<id>/`.
- A README that lists the routes, the entities it reads, and the entities it
  mutates (only via existing API endpoints — never directly).

---

## 6. Static HTML generation per project

### 6.1 What this is

`agileplus ui static-gen --project <path>` produces a **single
`agileplus-status.html`** in the project root (or a path of choice). It is a
self-contained file: open it in any browser, no server, no network, no build
step. Every refresh re-reads the project's state (kitty-specs/, worklog,
SQLite if available) and re-renders.

This is "dynamic on refresh," not "dynamic live." It targets use cases like:

- Attaching the latest project status to a release artifact.
- Emailing `agileplus-status.html` to a stakeholder.
- Embedding a status pane in docs that should refresh when a reader hits F5.

### 6.2 What the embedded JS does

The generator emits one HTML document with:

1. **The full DOM tree of the status page**, rendered server-side at generation
   time as a *baseline*. This is what the user sees before any JS runs.
2. **A `<script type="application/json" id="agileplus-state-index">…</script>`
   block** describing where to fetch state from. Example:

   ```html
   <script type="application/json" id="agileplus-state-index">
   {
     "project_root": "../",
     "sqlite": { "path": "agileplus.db", "mode": "readonly" },
     "specs_dir": "kitty-specs",
     "worklog": "AgilePlus/.work-audit/worklog.md",
     "captured_at": "2026-06-25T10:00:00Z"
   }
   </script>
   ```

3. **A small `embedded.js`** (≈6 KB, no deps) that runs on `DOMContentLoaded`:

   ```
   fetch -> File System Access API (Chromium) OR
            input[type=file] fallback (Firefox/Safari) OR
            pre-baked snapshot if neither available
   parse -> JSON / sqlite via sql.js / frontmatter via yaml.js
   diff  -> last-known-state (in localStorage)
   apply -> mutate the DOM to reflect fresh state
   ```

   The diff/apply step uses `data-agp-key="feature:42"` attributes placed by
   the server renderer so the JS knows exactly which nodes to update without
   re-rendering the whole page.

### 6.3 Reading state without a server

Browsers cannot read arbitrary local files from a `file://` page by default.
We define three progressively richer modes:

| Mode              | Browser support       | What it reads                                                       |
|-------------------|-----------------------|---------------------------------------------------------------------|
| **Snapshot**      | All                   | Only the JSON snapshot inlined at generation time. **Default.**     |
| **Manifest-pick** | All                   | User clicks a button; file picker reads `agileplus.db` and a chosen specs dir. |
| **FS Access**     | Chromium-based        | Auto-reads `agileplus.db`, `kitty-specs/`, `worklog.md` from the path in the state index. |

**Snapshot mode** is the always-works baseline — the HTML is a frozen picture.
**Manifest-pick** and **FS Access** are progressive enhancements; the JS
detects support and silently upgrades.

### 6.4 Reading SQLite from the browser

For Manifest-pick and FS Access modes we ship `sql.js` (Mozilla, asm.js) inlined
into `embedded.js` so there is no extra asset. The DB file is read as
`ArrayBuffer`, opened with `initDbArrayBuffer`, and queried with the same SQL
the Rust server uses (e.g. `SELECT id, slug, title, state FROM features`).

We deliberately **do not bundle a live JSON dump**. The JS queries SQLite
directly so the page refresh always reflects the actual DB the user has on
disk — there is no stale JSON to maintain.

### 6.5 Reading kitty-specs/ and worklog

The state index declares the directory layout. For each spec under
`kitty-specs/<feature>/` we read the `spec.md` frontmatter via a tiny
embedded YAML parser. For `worklog.md` we read it as text and surface the
last N lines.

### 6.6 Generator CLI surface

```
agileplus ui static-gen
  --project <path>          # required, defaults to cwd
  --out <path>              # default: <project>/agileplus-status.html
  --plugins tracera,planify # default: all built-ins
  --snapshot-only           # skip embedded JS DB reads
  --no-embedded-js          # pure snapshot, no JS at all
```

The generator lives in `crates/agileplus-dashboard/src/static_gen/`:

| File              | Responsibility                                                  |
|-------------------|-----------------------------------------------------------------|
| `mod.rs`          | CLI subcommand, orchestrates plugins, writes the file.          |
| `embedded_js.rs`  | Inlines `embedded.js` (compiled at build time via `include_str!`). |
| `sqlite_bridge.rs`| Generates the `state-index` JSON for the embedded JS.           |

### 6.7 What static-gen is **not**

- It is not a substitute for the live server when the user wants to **mutate**
  state. Mutating flows always go through the live server or the CLI.
- It is not a build artefact of a release. Each refresh is independent.

---

## 7. Local server / app: dashboard across all active projects

### 7.1 What "active project" means

An **active project** is a directory on the device that contains:

- `agileplus.db` (SQLite), **or**
- `kitty-specs/` (markdown spec tree), **or**
- `.agileplus/config.toml` with `[project] id = "..."`.

The local server discovers projects by scanning a configurable set of roots:

```
~/.agileplus/active-projects.toml
# example
[[projects]]
id = "agileplus-core"
path = "C:/Users/koosh/Dev/AgilePlus"

[[projects]]
id = "tracera"
path = "C:/Users/koosh/Dev/_wt3/tracera"

[[projects]]
id = "planify"
path = "C:/Users/koosh/Dev/_wt3/planify"
```

If the file is absent, the server falls back to a recursive scan of
`AGILEPLUS_PROJECT_ROOTS` (env var, `;`-separated on Windows, `:`-separated
elsewhere), capped at depth 4 to stay fast.

### 7.2 Server responsibilities

`agileplus ui serve` (the existing dashboard binary, with the new flag set)
adds:

- `GET /hub` — already exists (`templates/pages/hub.html` via `routes/pages.rs`).
  Now shows the **active projects table**: id, path, last-refresh,
  feature count, current cycle.
- `GET /projects` — JSON list of active projects + their current
  `ProjectSnapshot`.
- `GET /projects/{id}/status` — JSON snapshot of one project, suitable for
  the global dashboard widgets.
- `POST /projects/{id}/activate` — sets the active project (already exists at
  `/api/dashboard/projects/{id}/activate`).
- `GET /projects/{id}/static/agileplus-status.html` — re-generates and serves
  the per-project static file on the fly (so the same HTML the CLI generates
  is reachable through the dashboard).

### 7.3 Local app (desktop wrapper)

The existing `crates/agileplus-dashboard/desktop-electrobun/` is the desktop
shell. The local app contract:

- Launch the dashboard server on a free port (`AGILEPLUS_DASHBOARD_PORT=0`
  then read back the bound port).
- Open a native window pointing at `http://127.0.0.1:<port>/hub`.
- On window close: keep the server running in the background so the next
  launch is instant; expose a tray icon for `Quit`.
- Refresh the project list every 60 s and on FS-watcher events from each
  project's root.

This is intentionally thin: the same Rust handlers power both the browser
session and the desktop window. No Electron-style fork.

### 7.4 Data flow (multi-project)

```
File-system watcher (notify-rs) on each active project root
  │
  ▼
ProjectWatcher::on_change(project_id, event)
  │
  ├── re-read SQLite change counter (PRAGMA data_version)
  ├── diff against last snapshot (in-memory, moka cache)
  └── publish Event::ProjectUpdated { id, delta }
         │
         ▼
SSE channel /api/stream → browser subscribers
         │
         ▼
DashboardStore updates active_project_id, re-renders hub & kanban partials
```

The hub view itself is server-rendered HTML, refreshed on a 30 s timer
(htmx `every 30s`). Per-project drill-downs use the existing kanban routes
filtered by `active_project_id`.

### 7.5 What stays local

- **No remote sync** is performed by the local server. It only reads.
- **No telemetry** is sent. The watcher is local-only.
- **No new auth surface.** Localhost binding only (`127.0.0.1`).

---

## 8. End-to-end data flow (composite view)

A single user session rendering Tracera on a different project's snapshot:

```
┌──────────────────────────┐         ┌─────────────────────────────────┐
│ Browser tab              │         │ agileplus-dashboard (Axum)      │
│  /plugins/tracera        │ ──────▶ │  router::plugins::tracera       │
│  ?project=tracera        │ ◀────── │   ├─ PluginContext::new(...)    │
│                          │  HTML   │   ├─ trace_validator.graph()    │
│  htmx partial swaps      │         │   ├─ Handlebars::render(...)    │
│  SSE /api/stream         │         │   └─ PluginResponse::Html(...)  │
└──────────────────────────┘         └─────────────────────────────────┘
                                                       │
                                            ┌──────────┴──────────┐
                                            ▼                     ▼
                              agileplus-sqlite (read)   File watcher (notify)
                                            │
                                            ▼
                                  agileplus.db (each project)
```

For the static case the same handlers run during `static-gen`, but the
output is written to a single `.html` file with embedded JS instead of
streamed to a browser.

---

## 9. Crate-by-crate deliverable summary

| Crate                         | Spec impact                                                     |
|-------------------------------|-----------------------------------------------------------------|
| `agileplus-dashboard`         | Add `plugins/`, `render/`, `static_gen/`, plugin routes, hub multi-project. |
| `agileplus-plugin-core`       | New trait crate (Plugin, PluginContext, PluginRoute, StaticGen).|
| `agileplus-plane`             | Unchanged. Becomes the optional sync backend for the Plane-clone. |
| `agileplus-domain`            | Unchanged.                                                       |
| `agileplus-sqlite`            | Unchanged.                                                       |
| `agileplus-trace-validator`   | Unchanged. Consumed by Tracera plugin.                          |
| `agileplus-cli`               | Wire `agileplus ui serve`, `agileplus ui static-gen`, `agileplus ui hub`. |
| `agileplus-trace-validator`   | Add optional JSON export (already produced by validator core).  |

---

## 10. Acceptance criteria (architecture)

This spec is "done" once every item below is true **at design level** (no
implementation in this PR):

- [x] Server-render approach defined (§4.2).
- [x] Crate layout finalised (§4.3).
- [x] Plugin trait, routes, and engine policy defined (§5.1).
- [x] Tracera view routes + data flow defined (§5.2).
- [x] Planify view routes + data flow defined (§5.3).
- [x] Plane-clone view routes + data flow defined (§5.4).
- [x] Static HTML generation flow + embedded JS contract defined (§6).
- [x] Embedded JS state-read modes (Snapshot / Manifest-pick / FS Access) defined (§6.3).
- [x] SQLite-from-browser approach defined (§6.4).
- [x] Active-project discovery + watcher + multi-project data flow defined (§7).
- [x] Local app shell behaviour defined (§7.3).
- [x] No mutation surface is added that bypasses existing API/CLI endpoints.

---

## 11. Open questions (for follow-up PRs)

- Do we ship `sql.js` or move to a thin custom SQLite parser for embedded JS?
  (sql.js is ~1 MB; custom parser would shrink the file by ~80% but is more
  maintenance. Default: ship `sql.js`.)
- Should Planify get its own SQLite tables, or stay read-only over
  `agileplus-domain`? (Default: read-only at first.)
- Should the local server discover projects from the Git remote
  (`git config --get remote.origin.url`)? (Defer.)
- Handlebars helpers we need: `eq`, `json`, `date`, `truncate`, `graph-node`
  (for Tracera SVG).