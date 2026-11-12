# Frontend ↔ Backend route contract (static analysis)

**Date:** 2026-09-19
**Repo:** `/Users/kooshapari/CodeProjects/Phenotype/repos/wt-byteport-tauri-20260911`
**Observed git state at analysis time:** branch `deps/storybook-10-without-ts7`, HEAD `20e79cc3`
(*the session context header claimed `main`; the branch actually checked out is the one above — reported as observed.*)
**Canonical backend under analysis:** `backend/byteport/` (module `byteport`). `backend/` (module `github.com/byteport/api`, `/api/v1`) is **out of scope** — `backend/README.md` records that nothing in the app calls it, and a live grep confirms the live frontend has **zero** references to `/api/v1`.
**Method:** static only. No process was started, no backend was run, no request was made. Nothing was fixed.
**Builds on:** [`docs/sessions/20260919-endpoint-coverage/COVERAGE.md`](../20260919-endpoint-coverage/COVERAGE.md) — the measured (live-probe) report. That document answers *"what does the server return"*. This document answers *"do the two sides agree on the shape of the surface"*, and it is the only one of the two that enumerates call sites, methods, and URL-construction paths exhaustively.
**Evidence class:** static/observed source. This is **not** local validation and **not** hosted — no route was executed here.

---

## 0. TL;DR

| Direction checked | Result |
|---|---|
| **Frontend calls a path the backend does not register** (live tree) | **NONE.** All 13 distinct method+path pairs the live SvelteKit app issues are registered. Confirms COVERAGE.md §5 independently. |
| **Frontend calls an unregistered path** (git-tracked stale `.history`) | **4 instances**, incl. `GET /github/status` on port **8080**. Tracked, but not built and not reachable. |
| **Backend registers a path nothing calls** | 2: `/metrics`, `/api/github/callback`. Both correct by design (monitoring / external OAuth redirect). |
| **Path matches but HTTP method differs** | **NONE.** Empty table, and deliberately so. |
| **Frontend builds URLs inconsistently** | **Real, and this is the actual finding of this report.** 3 independent base-URL resolvers exist; 2 are live, 1 is dead; exactly 1 of 13 paths carries an `/api` prefix while the other 12 do not; the GitHub family is registered under `/api/github/*` but the commented-out sibling and the documented family are `/github/*`. |

**The headline is negative but load-bearing:** there is no 404-class bug in the live app. The defects are in *how the surface is addressed*, not in *which addresses exist* — which means they will not show up as a user-visible 404, and will only bite on the next refactor, port change, or GitHub-scope change.

**Visual state of the app: UNKNOWN.** No screenshots were taken (shared cockpit contract). Nothing about rendering is asserted. Hosted and delivered readiness: **UNKNOWN**.

---

## 1. Extraction method (exact commands)

### 1.1 Backend route surface

Only `setupRouter()` in `backend/byteport/main.go` registers routes. Verified there is no second registration site:

```bash
grep -rnE '\.(GET|POST|PUT|DELETE|PATCH|Any|HEAD|OPTIONS)\("' backend/byteport --include=*.go | grep -v _test.go
grep -rnE 'gin\.(New|Default|Engine)|RouterGroup|\.Group\(|r\.(GET|POST|PUT|DELETE|Any)|router\.' \
  backend/byteport --include=*.go | grep -v _test.go | grep -v '^backend/byteport/main.go'
# -> no output: main.go is the sole registration point
```

Result in §2. `backend/byteport/` contains no `cmd/` directory and no second `gin.Default()`; `routes/*.go` define handlers only, never path strings.

### 1.2 Frontend call surface

```bash
# explicit call sites
grep -rnE "apiUrl\(|apiFetch\(|fetch\(|axios|localhost:8081|127\.0\.0\.1:8081|API_PORT|API_BASE|window\.open" \
  frontend/web/src frontend/web/src-tauri/src

# every path-shaped string literal
grep -rnoE "['\"\`]/[a-zA-Z][a-zA-Z0-9_./\$\{\}-]*['\"\`]" frontend/web/src
```

`axios` appears nowhere. Result in §3.

---

## 2. Canonical backend surface (authoritative)

Sole source: `backend/byteport/main.go`, `setupRouter()` (lines 35–102). Group + line:

| # | Method | Path | Handler | Registration site | Auth |
|---|---|---|---|---|---|
| 1 | GET | `/link` | `routes.LinkHandler` | `main.go:81` | protected |
| 2 | POST | `/link` | `routes.ValidateLink` | `main.go:82` | protected |
| 3 | GET | `/authenticate` | `routes.Authenticate` | `main.go:83` | protected |
| 4 | GET | `/instances` | `routes.GetInstances` | `main.go:84` | protected |
| 5 | GET | `/projects` | `routes.GetProjects` | `main.go:85` | protected |
| 6 | GET | `/api/github/repositories` | `routes.RetrieveRepositories` | `main.go:86` | protected |
| 7 | POST | `/deploy` | `routes.DeployProject` | `main.go:87` | protected |
| 8 | POST | `/terminate` | `routes.TerminateInstance` | `main.go:88` | protected |
| 9 | GET | `/user/:id/creds` | `routes.UpdateLink` | `main.go:89` | protected |
| 10 | PUT | `/user/:id/creds` | `routes.UpdateUser` | `main.go:90` | protected |
| 11 | POST | `/login` | `routes.Login` | `main.go:93` | public |
| 12 | POST | `/signup` | `routes.Signup` | `main.go:94` | public |
| 13 | GET | `/api/github/callback` | `routes.HandleCallback` | `main.go:95` | public |
| 14 | GET | `/health` | `routes.HealthHandler` | `main.go:96` | public |
| 15 | GET | `/metrics` | `routes.MetricsHandler` | `main.go:97` | public |
| — | GET | `/github/status` | `routes.GitHubStatusHandler` | **commented out, `main.go:91`** | — |

**15 registered method+path pairs across 14 distinct paths** (`/link` is the one path with two methods). This matches the gin debug table in COVERAGE.md §3 exactly — that report captured the same surface from a live boot, so §2 here is independently confirmed by observation, not merely by reading.

Two non-route strings in `main.go` are comments, not registrations: `// gh webhook at /api/github/auth/webhook` (`main.go:99`) and the disabled `//protected.GET("/github/status", ...)` (`main.go:91`). Neither path is registered.

---

## 3. Frontend call surface (live tree)

All live call sites. `apiFetch`/`apiUrl` from `lib/api.ts`; base is `http://localhost:8081` (`API_PORT = 8081`, `lib/api.ts:16`).

| # | Method | Path | Call site(s) | Via |
|---|---|---|---|---|
| 1 | GET | `/authenticate` | `stores/user.ts:60` (from 10 `initializeUser` call sites, §4.4) | raw `fetch` |
| 2 | GET | `/health` | `lib/api.ts:119` → `lib/components/shell/health.ts:45` → `AppShell.svelte:17`, `BackendStatus.svelte:15,51` | `apiFetch` |
| 3 | GET | `/api/github/repositories` | `components/gitSearch.svelte:80` | `apiFetch` |
| 4 | GET | `/projects` | `components/projectData.ts:393`; `routes/home/monitor/+page.svelte:224` | `apiFetch` |
| 5 | GET | `/instances` | `components/projectData.ts:399`; `routes/home/monitor/+page.svelte:223` | `apiFetch` |
| 6 | POST | `/deploy` | `components/projectData.ts:417` (from `addProjectDialog.svelte:139`) | `apiFetch` |
| 7 | POST | `/terminate` | `components/projectData.ts:439` (from `projectPopup.svelte:61`) | `apiFetch` |
| 8 | GET | `/user/{uuid}/creds` | `routes/home/settings/integrations/+page.svelte:126` | `apiFetch` |
| 9 | PUT | `/user/{uuid}/creds` | `routes/home/settings/profile/+page.svelte:86` | `apiFetch` |
| 10 | POST | `/link` | `routes/home/settings/integrations/+page.svelte:222`; `routes/fts/+page.svelte:197` | `apiFetch` |
| 11 | GET | `/link` | `window.open`: `integrations/+page.svelte:253`, `fts/+page.svelte:169`; `href`: `fts/+page.svelte:271` | `apiUrl` in popup/href |
| 12 | POST | `/signup` | `routes/signup/+page.svelte:109` | `apiFetch` |
| 13 | POST | `/login` | `routes/login/+page.svelte:88` | `apiFetch` |

Not API calls (excluded, listed to bound the search): `window.open(project.accessUrl)` at `projectPopup.svelte:47` and `routes/home/projects/+page.svelte:107` (data-driven external URL, not a backend route), SvelteKit client-side navigations (`/home`, `/login`, `/fts`, `/home/settings/*`), and static asset paths (`/src/assets/img/byte.png`).

Tauri shell: `frontend/web/src-tauri/src/lib.rs:146,149` — `http://localhost:8081` + `HEALTH_PATH = "/health"`, overridable via `BYTEPORT_BACKEND_URL` (`lib.rs:142,228`). CSP allowlist at `tauri.conf.json:31-32` admits `http://localhost:8081` and `http://127.0.0.1:8081`.

There is **no dev proxy**: `vite.config.ts` defines no `server.proxy`, so no path is rewritten in flight. `frontend/web/` contains no `.env*` file, so `VITE_API_URL` is unset in this checkout and every resolver falls back to `http://localhost:8081`.

---

## 4. Mismatch tables

### 4.1 Frontend calls a path the backend does NOT register — live tree

**Empty.** All 13 pairs in §3 map onto §2 registrations 1:1. This independently reproduces COVERAGE.md §5 Direction 1.

### 4.1b Frontend calls a path the backend does NOT register — git-tracked stale history

`frontend/web/.history/` is **git-tracked** (`git ls-files frontend/web/.history | wc -l` → **2765** files; `git check-ignore` → not ignored). It is VS Code Local History snapshots from 2024-11, not built by SvelteKit (which reads `src/` only) and not reachable.

| Path called | Where | Registered? | Backend port implied |
|---|---|---|---|
| `GET /github/status` | `.history/src/routes/fts/+page_20241125224528.svelte:166` | **no** (commented out, `main.go:91`; handler absent) | 8080 |
| `GET /validate` | `.history` (unique-path scan of `fetch(\`${SERVER_URL}/…\`)`) | **no** | 8080 |
| `GET /validate-token` | `.history` (same scan) | **no** | 8080 |
| `GET /authenticate`, `GET /link`, `POST /login`, `POST /signup` | `.history` | yes | 8080 (`const SERVER_URL = 'http://localhost:8080'`, e.g. `.history/src/stores/user_20241124145356.ts:2`) |

Severity **low** (not compiled, not served, not reachable) but governance-relevant: a tracked directory containing callers of non-existent endpoints, on a superseded port, is what answers the "where is `/github/status` referenced" question. See finding **RC-1** / **RC-9**.

### 4.2 Backend registers a path nothing calls (dead surface)

| Path | Called by live frontend? | Verdict |
|---|---|---|
| `GET /metrics` | No | **Correct as designed.** Prometheus scrape target; `DEPLOYMENT.md:24,47,66,92`. Not a defect. |
| `GET /api/github/callback` | No | **Correct as designed.** GitHub redirects the OAuth popup here after `GET /link` issues a 302 to `github.com/login/oauth/authorize` (`lib/git.go:63-65`). External entry point; the app is the *initiator*, never the caller. Not a defect. |

No other registered path is uncalled. In particular `/terminate` (only caller `projectData.ts:439`) and `/deploy` (only caller `projectData.ts:417`) are **called**, so neither is dead — despite appearing uncalled to a grep that only looks at `.svelte` files.

### 4.3 Path matches but the HTTP method differs

**Empty.** Table stated explicitly because its emptiness is the point:

| Path | Registered method(s) | Method(s) the frontend uses | Match? |
|---|---|---|---|
| `/link` | GET, POST | GET (§3 #11), POST (§3 #10) | yes, both |
| `/user/:id/creds` | GET, PUT | GET (§3 #8), PUT (§3 #9) | yes, both |
| `/deploy`, `/terminate`, `/login`, `/signup` | POST | POST | yes |
| `/authenticate`, `/instances`, `/projects`, `/health`, `/api/github/repositories`, `/api/github/callback`, `/metrics` | GET | GET | yes |

Every one of the 5 mutating endpoints has exactly one registered method, and that is the method the frontend uses. No frontend `DELETE`/`PATCH` exists anywhere (`grep` for `method: 'DELETE'|'PATCH'` → no hits), and the backend registers neither verb.

One handler-to-verb oddity (not a method mismatch, flagged for the reader): **`GET /user/:id/creds` is served by `routes.UpdateLink` (`main.go:89`)** and **`PUT /user/:id/creds` by `routes.UpdateUser` (`main.go:90`)**. The GET is named as a write. This is the same handler whose 500-on-fresh-user behaviour is COVERAGE.md finding **F3**, so the naming smell and the defect coincide on one line.

### 4.4 Frontend builds URLs inconsistently — the real findings

Three distinct base-URL resolvers exist in `frontend/web/src`:

| Resolver | Location | Live? | Consumers |
|---|---|---|---|
| `getApiBaseUrl()` / `apiUrl()` | `lib/api.ts:28-53` | **yes** | `apiFetch` (`api.ts:84`), all 11 `apiFetch` call sites, 3 `window.open`/`href`, 10 `initializeUser` call sites |
| `config.api.baseUrl` + `apiHelpers.getApiUrl()` | `lib/config.ts:6,101-105` | **no — zero consumers** | none (`grep -rn "apiHelpers\|config\.api" frontend/web/src` → only its own definition) |
| `initializeUser(SERVER_URL)` — base **passed in as a parameter** | `stores/user.ts:56,60` | yes | 10 call sites, all passing `getApiBaseUrl()` |

Sub-findings:

**(a) `/api` prefix inconsistency inside a single helper's caller set.** 12 of the 13 paths handed to `apiUrl`/`apiFetch` are root-level (`/projects`, `/link`, `/user/...`, `/login`, …). Exactly one is namespaced: `/api/github/repositories` (`gitSearch.svelte:80`). Same helper, same base, inconsistent namespacing — the reader cannot tell from the call site whether the backend mounts under a prefix.

**(b) The GitHub family is split across two prefixes.** Registered: `/api/github/repositories` (`main.go:86`), `/api/github/callback` (`main.go:95`). Disabled sibling: `/github/status` (`main.go:91`). Documented family: `/github/*`. Three spellings for one family. See §5.

**(c) `initializeUser` bypasses the shared helper.** `stores/user.ts:60` does a raw `fetch(\`${SERVER_URL}/authenticate\`)` with hand-rolled `credentials: 'include'`, duplicating `apiFetch`'s credential/timeout/typed-error behaviour instead of calling it. All 10 callers pass `getApiBaseUrl()` today, so there is **no live mismatch** — but the injection point accepts any string with no validation, and a value carrying a path or trailing slash changes the target silently. Call sites: `projectData.ts:462`, `routes/+page.svelte:36`, `routes/fts/+page.svelte:79`, `routes/login/+page.svelte:94`, `routes/signup/+page.svelte:120`, `routes/home/settings/+page.svelte:55`, `routes/home/settings/integrations/+page.svelte:282`, `routes/home/settings/profile/+page.svelte:132`, `routes/home/monitor/+page.svelte:253`.

**(d) The port is hardcoded in 5 places with no single owner** (the split is *documented* at `main.go:104-111` but not *enforced*): `lib/api.ts:16` (`API_PORT = 8081`), `lib/config.ts:6` and `lib/config.ts:21`, `lib/components/shell/health.ts:4` (comment), `src-tauri/src/lib.rs:146` (`BACKEND_URL_DEFAULT`), `tauri.conf.json:31-32` (CSP). The Tauri shell is the only one that is env-overridable (`BYTEPORT_BACKEND_URL`, `lib.rs:142`); the web app's only override is `VITE_API_URL`, and `lib/api.ts:29` reads it as `import.meta.env?.VITE_API_URL` while `lib/config.ts:6` reads it as `import.meta.env.VITE_API_URL`.

**(e) Dead duplicate config with a conflicting upstream default.** `lib/config.ts:7` sets `nvmsUrl: import.meta.env.VITE_NVMS_URL || 'http://localhost:3000'`, while the backend's `nvmsURL()` returns `http://localhost:8443` (`routes/deployment.go:22`). Two different defaults for the same upstream. Dead code, so no live effect — but if `apiHelpers` is ever revived, the frontend would address NanoVMS on the wrong port.

**(f) One dead HTTP caller.** `lib/utils.ts:121 populateLists()` issues `GET /projects` (`utils.ts:125`) and has **zero call sites** (`grep -rn populateLists frontend/web/src` → definition only). This is a fourth independent URL builder (`utils.ts:124` → `getBaseUrl()`, which now delegates to `getApiBaseUrl()` at `utils.ts:116`) that is dead.

---

## 5. `/github/status` — where it is referenced, and the prefix inconsistency

**Confirmed: `GET /github/status` is registered nowhere.** The only registration line in the repository is commented out:

- `backend/byteport/main.go:91` — `//protected.GET("/github/status", routes.GitHubStatusHandler)`
- `routes.GitHubStatusHandler` does not exist — `grep -rn "GitHubStatusHandler" backend/byteport` returns **only** the commented line. The package would not compile if the comment were uncommented.

Where it is referenced (complete list, repository-wide, excluding `node_modules`/`target`/`vendor`/`.git`):

| Location | Kind | Tracked? | Built? |
|---|---|---|---|
| `backend/byteport/main.go:91` | disabled registration (comment) | yes | no-op |
| `frontend/web/.history/src/routes/fts/+page_20241125224528.svelte:166` — `await fetch(\`${SERVER_URL}/github/status\`, { credentials: 'include' })` inside `checkGitHubLinkStatus()` | **stale caller in tracked history** | **yes** (2765 files tracked) | **no** (`.history/` outside `src/`) |
| `docs/sessions/20260919-endpoint-coverage/COVERAGE.md` | prior report | yes | n/a |

**Does the live frontend call it? No.** The live `routes/fts/+page.svelte` links GitHub through `apiUrl('/link')` (`:169`, `:197`, `:271`) and the live integrations page through `apiUrl('/link')` (`:222`, `:253`). The live GitHub-state read is `githubLinked` derived from the token returned by `GET /user/{uuid}/creds` (`integrations/+page.svelte:132`, `:68`) — the old `checkGitHubLinkStatus()` poll-on-`/github/status` pattern is gone from the live tree.

**Prefix inconsistency — confirmed, and it is three-way:**

| Spelling | Where | Registered? |
|---|---|---|
| `/api/github/*` | `main.go:86` `/api/github/repositories`, `main.go:95` `/api/github/callback` | **yes** |
| `/github/status` | `main.go:91` (disabled) | no |
| `/github/*` (documented route family) | `backend/README.md:14` route table: `` … `/metrics`, `/github/*` `` | **no such prefix exists** |
| `/api/github/auth/webhook` | `main.go:99` (comment only) | no |

So the `/github/*` family named in `backend/README.md`'s route table is not what the server binds; the bound family is `/api/github/*`. A reader trusting the README would probe `/github/...` and get 404. `docs/operations/two-backends.md:58,268` and `API_REFERENCE.md:192` spell it correctly as `/api/github/*`, so the README is the outlier.

---

## 6. Findings

Severity is about consequence if nothing changes. "User-reachable" means a live user action can reach the code path.

**RC-1 — `GET /github/status` is documented/referenced but never registered. Severity: low. User-reachable: no.**
Disabled at `main.go:91`; handler `routes.GitHubStatusHandler` does not exist; there is **no live caller**. The only caller anywhere is a git-tracked `.history` snapshot. Answer to the task's question: **it is referenced in exactly one tracked file that is not built, and the live frontend does not call it.** Nothing is broken today; the residue is a dead comment plus a stale tracked file. COVERAGE.md F2 measured the same endpoint returning 404 — consistent.

**RC-2 — the `/github` route family has three spellings. Severity: low (docs/contract). User-reachable: no.**
Registered `/api/github/*`; disabled `/github/status`; documented `/github/*` in `backend/README.md:14`. Fix belongs in documentation and, when the status route is finally implemented, on a prefix decided once — not fixed here.

**RC-3 — three base-URL resolvers, one of them dead, with divergent env reads. Severity: low now, medium as drift risk. User-reachable: no.**
`lib/api.ts:28` (live) vs `lib/config.ts:101` (zero consumers) vs `stores/user.ts:56` (parameter-injected). `lib/api.ts:29` reads `import.meta.env?.VITE_API_URL`; `lib/config.ts:6` reads `import.meta.env.VITE_API_URL`. A single override variable with two read styles and three consumers-of-record is the classic setup for "works in dev, fails in a packaged build".

**RC-4 — one path in thirteen carries an `/api` prefix. Severity: low (maintainability). User-reachable: yes, and it works.**
`/api/github/repositories` (`gitSearch.svelte:80`) is the only namespaced path among 12 root-level siblings. No functional impact; it removes any signal about whether a prefix is in play.

**RC-5 — `initializeUser` duplicates `apiFetch`'s transport instead of using it. Severity: low-medium. User-reachable: yes (every authenticated view).**
`stores/user.ts:60` raw `fetch`, no timeout (unlike `apiFetch`'s 30 s AbortController, `lib/api.ts:80-81`), no `ApiError`, and a base URL accepted as an unvalidated parameter across 10 call sites. Note the asymmetry: `apiFetch` will abort a hung backend; `initializeUser` will not — and it is the call that decides `authenticated` vs `unauthenticated` for every gated page. `populateLists`' comment (`utils.ts:116-119`) records that exactly this class of unguarded call previously caused views to stay permanently empty.

**RC-6 — dead URL-building code left in place. Severity: low. User-reachable: no.**
`lib/config.ts` `apiHelpers`/`config.api.*` (zero consumers), `lib/utils.ts:121 populateLists()` (zero callers, issues `GET /projects`). Two independent, now-orphaned copies of the base-URL logic.

**RC-7 — conflicting NanoVMS defaults between the two sides. Severity: low (dead code) but a latent wrong-port bug. User-reachable: no.**
Frontend dead config `http://localhost:3000` (`lib/config.ts:7`) vs backend live default `http://localhost:8443` (`routes/deployment.go:22`).

**RC-8 — the link-callback `postMessage` contract has no receiver. Severity: low. User-reachable: yes, harmlessly.**
`routes/git.go:95` emits `window.opener.postMessage('github-linked', '*')` and closes the popup. `grep -rn "github-linked|addEventListener('message'|onmessage|postMessage" frontend/web/src` → **no matches**. Both live pages track completion differently: `integrations/+page.svelte:262-267` polls `popup.closed`, and `fts/+page.svelte:211` sets `linked = true` immediately after opening the popup. So the backend implements a completion signal no client consumes — and the `fts` page's optimistic `linked = true` is unaffected by whether GitHub actually completed. Worth recording as the *opposite* of a 404: a coordinated no-op.

**RC-9 — 2765 git-tracked Local History files, several calling endpoints that do not exist, on a retired port. Severity: low (not built). User-reachable: no.**
`frontend/web/.history/` is tracked and not ignored. It contains callers of `/github/status`, `/validate`, `/validate-token` (none registered) and `const SERVER_URL = 'http://localhost:8080'` (backend now serves 8081). This is stale generated history in version control; it makes every "which paths does the frontend call" question return false positives unless the directory is excluded.

**RC-10 — port `8081` has no single source of truth across 6 sites. Severity: low. User-reachable: indirect.**
`lib/api.ts:16`, `lib/config.ts:6,21`, `lib/components/shell/health.ts:4`, `src-tauri/src/lib.rs:146`, `tauri.conf.json:31-32` (CSP). `main.go:104-111` lists the consumers as documentation but nothing enforces agreement, and the CSP would silently block the fetch if the port moved without it.

---

## 7. Explicit negatives (things that are NOT mismatches)

Recording these so the report cannot be read as incomplete:

- Every path the live frontend calls is registered, with the method the frontend uses. (§4.1, §4.3 — both empty.)
- The live frontend has **zero** references to `/api/v1`; the `backend/` module is confirmed unused by grep, independently of `backend/README.md`'s assertion.
- No `axios` anywhere; no `DELETE`/`PATCH`; no dev proxy in `vite.config.ts`; no `.env*` in `frontend/web/`, so `VITE_API_URL` is not intervening in this checkout.
- `GET /link` really is a 302 to GitHub (`lib/git.go:63-65`), so opening it in a popup is the correct use of a GET, and `POST /link` (`ValidateLink`) is the separate credential write. The two methods on one path are not a collision.
- The Tauri shell's `/health` probe matches `main.go:96`, and its CSP admits the backend origin.
- `PUT /user/:id/creds` body shape matches: frontend sends `{name, email, password}` (`profile/+page.svelte:88`) and `UpdateUser` binds `models.User` with optional-field guards (`auth.go:205-219`). Go's case-insensitive decoding covers the casing.

---

## 8. What is UNKNOWN and is not claimed

- **Runtime behaviour of any of these paths: not tested here.** COVERAGE.md measured the status codes with a live process (and found F3/F4/F5). This report asserts only source-level agreement. Where the two overlap (§2 route table, §5 `/github/status`), this report agrees with that measurement.
- **GitHub OAuth app configuration — UNKNOWN.** Whether GitHub is configured to redirect to `http://localhost:8081/api/github/callback` is external state and was not inspected. If it is configured with the `/github/...` spelling of RC-2, the callback would 404 — that is the one way RC-2 could become user-visible, and it cannot be resolved statically.
- **Visual state of the app: UNKNOWN.** No screenshots; nothing about rendering, error surfacing, or layout is asserted.
- **Hosted / delivered readiness: UNKNOWN.** Nothing was deployed or observed remotely.
- **Packaged-build behaviour of `VITE_API_URL`: UNKNOWN.** No `.env*` exists in this checkout, so the override path is unexercised; the two read styles (RC-3) would only diverge under a build that sets it.
- **Whether the dead helpers are intentionally retained: UNKNOWN.** `lib/config.ts` and `utils.ts:populateLists` may be kept for a planned feature; not determinable from the repository.
- **Untracked/other agents' work was not analysed.** At analysis time `frontend/web/package-lock.json`, `package.json`, `yarn.lock` were modified and `frontend/web/scratch-dead-classes.mjs` was untracked. None of it was read, touched, or staged.

---

## 9. Reproduction

```bash
cd /Users/kooshapari/CodeProjects/Phenotype/repos/wt-byteport-tauri-20260911

# 1. Registered route surface — main.go is the only registration site
grep -rnE '\.(GET|POST|PUT|DELETE|PATCH|Any)\("' backend/byteport --include=*.go | grep -v _test.go

# 2. Confirm no second router
grep -rnE 'gin\.(New|Default|Engine)|RouterGroup|\.Group\(' backend/byteport --include=*.go \
  | grep -v _test.go | grep -v '^backend/byteport/main.go'   # expect: no output

# 3. All live frontend call sites
grep -rnE "apiUrl\(|apiFetch\(|fetch\(|axios|localhost:8081|window\.open" frontend/web/src frontend/web/src-tauri/src

# 4. Every path-shaped literal in the live tree
grep -rnoE "['\"\`]/[a-zA-Z][a-zA-Z0-9_./\$\{\}-]*['\"\`]" frontend/web/src

# 5. /github/status, repo-wide
grep -rn "github/status\|GitHubStatusHandler" . --exclude-dir=node_modules --exclude-dir=target \
  --exclude-dir=vendor --exclude-dir=.git

# 6. .history is tracked (RC-9)
git ls-files frontend/web/.history | wc -l     # 2765
git check-ignore -v frontend/web/.history      # no output => not ignored

# 7. Dead-code confirmations
grep -rn "apiHelpers\|config\.api" frontend/web/src   # only lib/config.ts itself
grep -rn "populateLists" frontend/web/src             # only the definition
grep -rn "github-linked\|addEventListener('message'\|postMessage" frontend/web/src  # no listener
grep -rn "api/v1" frontend/web/src                    # none

# 8. Competing NanoVMS defaults
grep -rn "localhost:3000" frontend/web/src ; grep -n "localhost:8443" backend/byteport/routes/deployment.go
```

No process was started for this report. No repository file was modified. The only file added is this document.
