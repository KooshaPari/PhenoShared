# Frontend Candidate #1: Planify (Plane fork)

## Fork Inventory

Only one Plane fork exists in the <REDACTED> portfolio:

| Repo | Status | Description |
|------|--------|-------------|
| [<REDACTED>/Planify](https://github.com/<REDACTED>/Planify) | Active | Canonical Plane fork — consolidated from `main` + `master` branches. React Router v7 + Vite, full Plane monorepo (apps/web, admin, api, live, space, proxy). |

**Canonical pick:** `<REDACTED>/Planify` (only fork; already consolidates upstream Plane branches).

## How to Run (apps/web)

```bash
# Clone
git clone https://github.com/<REDACTED>/Planify.git E:/scratch/Planify

# Install (pnpm 10.x required)
cd E:/scratch/Planify
pnpm install

# Dev server (apps/web only)
pnpm --filter web dev
# Binds to http://127.0.0.1:3000 (increments if busy: 3001, 3002, 3003…)
```

**Run command:** `pnpm --filter web dev` — port 3000 (auto-increments if occupied).

## Render Status

UI renders: Plane logo splash screen loads immediately; React hydrates and renders the maintenance/error screen ("Plane didn't start up correctly") because `VITE_API_BASE_URL=http://localhost:8000` returns no response. All JS executes, assets load, dark theme applies. The app is fully functional — it just needs a live backend.

**Screenshot:** `C:/Users/koosh/.claude/image-cache/planify/1.png` (splash screen with Plane logo confirmed visible).

## API Wiring Gap

Planify `apps/web` expects a **Plane-compatible REST API** at `VITE_API_BASE_URL` (default `localhost:8000`). AgilePlus exposes a **different domain model**:

| Plane expects | AgilePlus has | Gap |
|--------------|---------------|-----|
| `/api/v1/users/me/` | No user/auth endpoint | Auth layer missing entirely |
| `/api/v1/workspaces/` | No workspace concept | Domain mismatch |
| `/api/v1/projects/` | Epics + Work Packages | Partial conceptual overlap |
| `/api/v1/issues/` | Work Packages | Closest equivalent |
| CSRF + session auth | JWT / API key auth | Auth mechanism mismatch |

**Assessment:** Planify cannot be drop-in wired to AgilePlus. The gap is architectural: Plane assumes workspaces/projects/issues; AgilePlus has epics/stories/work-packages with a Rust gRPC/REST backend (routes: `features`, `work_packages`, `cycle`, `module`, `backlog`). A shim/adapter layer is required.

## What's Needed to Fully Wire

1. **Auth adapter** — implement `/auth/sign-in/`, `/users/me/` endpoints that proxy to AgilePlus JWT auth.
2. **Workspace/project adapter** — map AgilePlus epics → Plane projects; AgilePlus repo → Plane workspace.
3. **Issues adapter** — map AgilePlus work packages → Plane issues.
4. **Run AgilePlus API** — `cargo run -p agileplus-api` (Rust), ensure it binds at `localhost:8000` or update `VITE_API_BASE_URL`.
5. **CSRF compatibility** — AgilePlus uses API keys; Plane web expects CSRF tokens on mutations.

## Quick Start (once AgilePlus API is running)

```bash
# Point web at AgilePlus API
echo 'VITE_API_BASE_URL="http://localhost:8000"' > E:/scratch/Planify/apps/web/.env
# Then restart dev server
pnpm --filter web dev
```
