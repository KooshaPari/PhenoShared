# Two Go backends under `backend/` — reconciliation analysis

**Status:** RESOLVED 2026-09-20. The `github.com/byteport/api` module
(`backend/{main.go,handlers.go,server.go,types.go,models/,internal/,lib/,testhelpers/,go.mod,go.sum,bytebridge/}`)
was retired. Only `backend/byteport/` (Go module `byteport`) remains.
See issue #382 and the resolution commit on `main`.

**Original status:** analysis only at the time of writing. Nothing was deleted,
moved, or refactored. This document is the deliverable for the historical analysis
that motivated the eventual consolidation.
**Date:** 2026-09-19
**Repo:** `/Users/kooshapari/CodeProjects/Phenotype/repos/wt-byteport-tauri-20260911`
**HEAD at end of run:** `2940412a` (`docs(coverage): measure the backend endpoint surface instead of assuming it`)
**HEAD at start of run:** `4f821689`. The tree moved under this analysis (a separate
agent landed the PII-redaction sweep and two hygiene/doc commits mid-run). Evidence
below states the commit it was observed at where that matters.

**Evidence classes used below** (per the shared cockpit contract):
`observed inventory` — read from the repo or a live process; `local validation` —
a locally built binary or test run on this host; `candidate` — a proposal, not a fact;
`hosted` readiness — **UNKNOWN**, nothing here is deployed or served anywhere;
`delivered` acceptance — **UNKNOWN**, no end-user workflow was accepted.
No screenshots were taken; any visual state is **UNKNOWN** by contract.

---

## 0. Answer first

1. **`backend/byteport/` (Go module `byteport`) is canonical.** Seven independent
   signals agree: the app's HTTP contract, the Tauri shell, the dev orchestrators,
   the container build, PR-gated CI, the active commit history, and the repo's own
   `Taskfile.yml` label "primary backend". §3.
2. **`backend/` (Go module `github.com/byteport/api`) is a WorkOS AuthKit rewrite
   that no consumer in this repository reaches.** It is not dead code — it builds,
   vets and tests clean — it is *unshipped* code with a different identity system
   and an incompatible data model. §4, §5.
3. **Recommendation: keep both for now, but make `backend/` non-canonical by
   construction** — distinct port, an ownership label in-tree, and fix the release
   target that currently packages the wrong module. Then gate the WorkOS direction
   on a product decision. §8. This is option **C** in §7.
4. **Do not cut the frontend over to `backend/` now (option A)** and **do not delete
   `backend/` now (option B)**. Both are decidable, but not from repository evidence:
   the missing input is a product decision about whether BytePort adopts WorkOS
   AuthKit, plus an implementation of the app's consumed route set. §9 states the
   exact evidence that would flip each.
5. **Leaving it as-is has already caused one real mis-test and one shipping defect,
   and I reproduced both.** §10. The mis-test is documented in-tree at
   `docs/sessions/20260918-byteport-handoff/HANDOFF.md:421`, and the shipping defect
   is real today: `.goreleaser.yml:5` builds `./backend` on every `v*` tag, so the
   released artifact cannot serve the desktop app.

---

## 1. Verified inventory

Everything in this table is `observed inventory` unless labelled otherwise.

| | `backend/` | `backend/byteport/` |
|---|---|---|
| Go module | `github.com/byteport/api` (`backend/go.mod:1`) | `byteport` (`backend/byteport/go.mod:1`) |
| Go directive | `go 1.26.0` (`backend/go.mod:3`) | `go 1.25.0` (`backend/byteport/go.mod:3`) |
| Entry point | `main.go` → `NewAPIServer` in `server.go` (`backend/main.go:61`) | `main.go` → `setupRouter` (`backend/byteport/main.go:35`) |
| Route root | `/api/v1` only (`backend/server.go:49`) | `/` — root-level paths (`backend/byteport/main.go:76-96`) |
| Registered routes | 9 groups: health, `auth/workos/callback`, `user/:id`, deployment handler, `legacy/deployments/*`, detect, estimate-cost, validate-config, docs, containers/status (`backend/server.go:49-110`) | `/link` GET+POST, `/authenticate`, `/instances`, `/projects`, `/api/github/repositories`, `/deploy`, `/terminate`, `/user/:id/creds` GET+PUT, `/login`, `/signup`, `/api/github/callback`, `/health`, `/metrics` (`backend/byteport/main.go:80-96`) |
| Default port | `defaultPort = "8081"` (`backend/main.go:19`) | `canonicalPort = "8081"` (`backend/byteport/main.go:110`) |
| Port resolution | `PORT`, else `8081` (`backend/main.go:47-50`) | `PORT` → `BYTEPORT_API_PORT` → `8081` (`backend/byteport/main.go:114-121`) |
| Bind address | `:PORT` on all interfaces (`backend/main.go:63`) | `0.0.0.0:PORT` (`backend/byteport/main.go:164`) |
| Auth system | WorkOS AuthKit. `backend/lib/auth.go:45-56` uses full WorkOS JWT validation when `WORKOS_API_KEY` is set; service at `internal/infrastructure/auth/workos_service.go:20-21`; callback handler `backend/handlers.go:390` | Own session/password flow: PASETO v4 local tokens in the OS keyring (`backend/byteport/lib/auth.go:70-91`), `POST /login` (`routes/auth.go:50`), `POST /signup` (`routes/auth.go:84`), cookie `authToken` (`lib/auth.go:189`) |
| Identity model | `User` + `WorkOSUser` (`backend/models/users.go:5`, `users_workos.go:7`, table `workos_users:20`) | `User` only (`backend/byteport/models/users.go:9`) |
| Models package | `backend/models/` — 21 `.go` files (11 non-test, 10 test) | `backend/byteport/models/` — 9 `.go` files (7 non-test, 2 test) |
| Tracked `.go` files | 104 total (53 non-test, 51 test). Breakdown: `models` 21, `lib/cloud` 14, `lib` 1, `internal/...` 63, `testhelpers` 1, top-level `backend/` 4 | 35 total (20 non-test, 15 test) |
| Commits touching path | 53, first `8454a74f` 2024-09-22 ("Initial Foundations"), last functional `4f821689` 2026-09-18 | 52, first `4f088064` 2024-11-23 ("Basic Login Scheme"), still active |
| Per-file commit depth | **74 of 104 files touched in exactly 1 commit**, 27 in 2, 3 in 3. Max depth 3. | 14 files ≥ 8 commits, max 19 (deep maintenance) |
| Tests (this host) | `go build`, `go vet`, `go test ./...` — all pass; 12 test packages `ok`, 0 `FAIL` (`local validation`) | `go build`, `go vet` pass. `go test ./...` **FAILs**: `byteport/internal/routes` hangs to the 600 s test timeout (`local validation`) |
| Runtime DB | default `file:./byteport.db` (`backend/models/data.go:18`) | `DATABASE_URL`, else `file:./byteport.db`, else keeps an existing `../database.db` (`backend/byteport/models/data.go:16,21,68-79`) |
| Container image | not used (`Dockerfile:4` builds `backend/byteport`) | root `Dockerfile:4` `cd backend/byteport && go build -o /byteport-server`; `docker-compose.yml:6-7` publishes `8081:8081` |
| PR-gated CI | **none** (see §6) | `.github/workflows/ci.yml:81`, `tier-0-gate.yml:46`, `lint.yml:14`, `deny.yml:77`, `audit.yml:171` |
| Release path | `.goreleaser.yml:5` `main: ./backend`; `.github/workflows/release-go.yml:49` `cd backend` | nothing (release packages the other module — §6) |
| Consumed by the desktop app | **no** | **yes** (§3, §4) |

---

## 2. Reconciliation against the briefing's facts

The briefing's framing held. Four numeric/dated details did not, and I state the
measured value instead:

| Briefing claim | Measured | Note |
|---|---|---|
| `backend/` = 44 go files | **104** tracked `.go` files (53 non-test). 53 if you count non-test under a narrower scope | The briefing undercounted; the module also owns `internal/` (64 files) and `lib/cloud` (14) |
| `backend/byteport/` = 32 go files | **35** tracked `.go` files (20 non-test) | Close; `backend/byteport/internal/routes/routes_test.go` is the extra surface |
| `backend/` first commit 2026-05-31 | `8454a74f` **2024-09-22** | 2026-05-31 is when **`server.go`** landed (`cb81ebe5`, "port hexagonal API + multi-cloud providers onto main (layer-C rescue)") — i.e. when the WorkOS rewrite was folded onto `main`, not when `backend/` appeared |
| "only 2-4 commits per path" | 74/104 files at exactly 1 commit, 27 at 2, 3 at 3 | Consistent in spirit, harsher in detail |

Everything else in the briefing reproduced exactly: module names, entry points,
`/api/v1`, the route lists, the WorkOS-only registration and the literal "AuthKit
only" comment (`backend/server.go:56-57`), both ports defaulting to 8081, the two
`models/` packages having drifted, and the api_key casing bug being byteport-only.

On that last point I confirmed the brief's distinction rather than restating it:
`backend/models/` has **no provider-map resolution at all**. Its `providers.go:9`
declares a `ProviderConfig` table (system-level cloud-provider metadata) with no
`ProviderEntry`/`ProviderKey` and no `providers[key]` lookup anywhere in the package,
whereas the bug lived in `backend/byteport/models/users.go:31-40` (`ProviderEntry`)
and `users.go:24` (`Providers map[string]AIProvider`). So a fix in one genuinely
cannot cover the other — the packages do not share the concept.

---

## 3. Why `backend/byteport/` is canonical

Seven independent signals, none of which reference the other module:

1. **The app's bootstrap call.** `frontend/web/src/stores/user.ts:56-66` fetches
   `${SERVER_URL}/authenticate` with `credentials: 'include'`. Only `byteport`
   routes `/authenticate` (`backend/byteport/main.go:82`). The outer module answers
   404 (measured, §10).
2. **The port contract.** `frontend/web/src/lib/api.ts:16` `export const API_PORT = 8081`
   with the docstring "Port the backend actually listens on (see
   backend/byteport/main.go)"; `frontend/web/src/lib/config.ts:6,21`;
   `frontend/web/src/lib/components/shell/health.ts:4` ("local service on port 8081").
3. **The desktop shell.** `frontend/web/src-tauri/src/lib.rs:145-146`
   `BACKEND_URL_DEFAULT = "http://localhost:8081"` with the comment citing
   `backend/byteport/main.go`; `tauri.conf.json:31-32` CSP `connect-src` allows only
   `localhost:8081` / `127.0.0.1:8081`.
4. **Build and run tooling.** `start:15,38` (`cd ../backend/byteport` … `air`);
   `backend/byteport/.air.toml:48` `proxy_port = 8081` (the only `.air.toml` in the
   repo); `setup-windows.ps1:180-181` (`cd backend\byteport` + `go run main.go`);
   `Taskfile.yml:4` "# Go (backend/byteport) # primary backend", `Taskfile.yml:33`
   `BACKEND_DIR: backend/byteport`; `Dockerfile:4`; `docker-compose.yml:6-7`.
5. **PR-gated CI.** `ci.yml:81,88,109,128-134`, `tier-0-gate.yml:43-46,64,81-84,102,122`,
   `lint.yml:14`, `deny.yml:75-83`, `audit.yml:156-171` all pin
   `working-directory: backend/byteport` and derive the Go version from
   `backend/byteport/go.mod`. No workflow references the outer module's paths.
6. **Documentation that names a winner.** `README.md:62` "`byteport` (main) |
   `backend/byteport/`"; `INSTALL.md:43-48,70-73` (build, run, `go install ./backend/byteport`);
   `AGENTS.md:40-41,135-138,177`; `ARCHITECTURE.md:16` lists `backend/byteport` as a
   component and does not mention the outer module; `docs/ARCHITECTURE.md:55` is the
   only architecture doc that names `github.com/byteport/api`.
7. **History shape.** 74 of 104 files in the outer module have been touched in exactly
   one commit (max depth 3) — a landing, not a service. `backend/byteport/` has files
   at 14 and 19 commits, and its most recent functional work is days old
   (`9580bb95`, `4f821689` both 2026-09-18).

---

## 4. What nothing reaches: the `/api/v1` module

**Search result (observed inventory).** `git grep -n "api/v1" -- . ':(exclude)backend/**'`
returns matches in **only** four places, and none of them is a caller:

- `docs/openapi.yaml` — a spec for the outer module (health, `auth/workos/callback`,
  `user/{id}`, `deployments`, `legacy/deployments/*`, detect, estimate-cost, docs).
- `docs/operations/slos.md:30-32` — unedited template rows (`<service 1>`) in a doc
  whose subject is SLO *format*, not these endpoints.
- `docs/research/API_GATEWAYS_SOTA.md:256` — an nginx `location /api/v1/` snippet in
  unrelated gateway research.
- Two session handoffs, which discuss the two backends as a problem to resolve.

`grep -rn "api/v1" frontend/` (including `frontend/web/src`, `src-tauri`, and tests,
`node_modules` excluded) returns **nothing**. `git grep "byteport/api"` outside
`backend/` matches only docs and handoffs — no code.

Exhaustively enumerated, the app's backend surface is
`/authenticate`, `/health`, `/metrics` (not app-called), `/projects`, `/instances`,
`/deploy`, `/terminate`, `/api/github/repositories`, `/user/:id/creds` (GET+PUT),
`/link` (GET+POST), `/login`, `/signup`, `/api/github/callback` (GitHub redirect).
Every one of those is registered in `backend/byteport/main.go:80-96` and none exists
in `backend/server.go`. This independently corroborates
`docs/sessions/20260919-endpoint-coverage/COVERAGE.md` §5, which measured the same
surface from a live process and found zero "app calls a path the backend does not
route" mismatches.

**Classification:** `backend/` is not dead code (it compiles, its 12 test packages
pass, it has 9 registered route groups and real multi-cloud adapters under
`backend/lib/cloud`). It is **unshipped code with no in-repo consumer**.

---

## 5. Drift between the two `models/` packages — three proofs

The briefing said the packages have "drifted and are separate". Drift here is not
a stale copy; it is two different schemas for the same table names.

**(a) Source-level divergence.**

| | `backend/models/users.go:5-24` | `backend/byteport/models/users.go:9-20` |
|---|---|---|
| Primary key | `UUID string \`gorm:"type:uuid;primaryKey"\`` | `UUID string \`gorm:"type:text;primaryKey"\`` |
| Embedded creds | AwsCreds, AzureCreds, GCPCreds, VercelCreds, NetlifyCreds, RailwayCreds, FlyIOCreds, SupabaseCreds, LLMConfig, Portfolio | AwsCreds, LLMConfig, Portfolio, Git |
| Timestamps | `CreatedAt`/`UpdatedAt` | none |
| LLM shape | `LLM` with `Provider` + provider defaults | `LLM{Provider, Providers map[string]AIProvider}` + `ProviderEntry`/`ProviderKey` helpers |

File sets do not overlap either (measured with `comm` on the two sorted basename
lists). Present only in `backend/byteport/models/`: `secrets.go` (non-test). Present
only in `backend/models/`: `deployments.go`, `hosts.go`, `primary_keys.go`,
`providers.go`, `users_workos.go`, plus eight test files
(`deployments_additional_test.go`, `gorm_hooks_test.go`, `models_100_percent_test.go`,
`models_comprehensive_test.go`, `models_database_integration_test.go`,
`models_final_100_percent_test.go`, `models_ultimate_100_percent_test.go`,
`projects_test.go`).

**(b) Runtime divergence.** Two SQLite files exist in the working tree with different
schemas (observed with `sqlite3 <file> ".tables"` and `PRAGMA table_info(users)`):

```
backend/byteport.db   tables: aws_resources hosts owners repositories deployments
                               instances projects users
backend/database.db   tables: git_secrets instances owners projects repositories
                               users
```

`PRAGMA table_info(users)` — `backend/byteport.db` (this is the **outer** module's
schema): `uuid|uuid` primary key, `name/email/password`, then
`aws_*`, `azure_*`, `gcp_service_account_json`, `vercel_token`, `netlify_token`,
`railway_token`, `flyio_api_token`, `supabase_access_token`, `llm_provider`,
`llm_providers|jsonb`, `portfolio_*`.
`PRAGMA table_info(users)` — `backend/database.db` (the **byteport** module's schema,
the legacy file `backend/byteport/models/data.go:21` deliberately keeps):
`id|INTEGER` primary key, `created_at/updated_at/deleted_at`, `name/email/password`,
`aws_*`, `openai_api_key`, `portfolio_*`, `git_*`, `uuid|TEXT`, `system_token`,
`system_secret_key`, `git_installation_id`.

**(c) Table-name collision.** Both packages map to `users`, `projects`, `instances`,
`owners`, `repositories`. A single SQLite file cannot hold both: the `users` primary
key is `uuid` in one and `INTEGER` in the other. So "keep both" can never mean
"point both at one database"; it necessarily means two files, which is exactly the
current state.

Two related hygiene facts, both `observed inventory`, both flagged rather than fixed:
`backend/database.db` is **tracked in git** (a mutable binary in the history; the
gitignore commit `41500179` deliberately left it alone and said why), and
`backend/byteport/byteport-server.exe` is also tracked (a committed Windows build
artifact). Row counts in both live DBs are `users=0`, `projects=0`, so nothing
observable is lost by either file today; that is not the same as "the files are
disposable", and it is not a claim about any other host.

---

## 6. The one place the repo already ships the wrong module

This is the highest-value finding in the analysis, because it is a defect in the
present, not a risk in the future.

```
.goreleaser.yml  1: project_name: byteport-api
.goreleaser.yml  5:     main: ./backend        <-- the UNCONSUMED module
.goreleaser.yml  6:     dir: .

.github/workflows/release-go.yml
  47:      - name: Run tests
  48:        run: |
  49:          cd backend              <-- again the UNCONSUMED module
  50:          go test -race -coverprofile=coverage.out ./...
  55:          files: ./backend/coverage.out
```

`release-go.yml:3-7` triggers on `push: tags: v*`. So a release tag publishes a
binary (`byteport-api`) built from `github.com/byteport/api` under a BytePort
product name, tested against the module the desktop app never calls. Meanwhile
`Dockerfile:4` and `docker-compose.yml` build and publish `backend/byteport` on
8081. The two shipping paths disagree about what "the backend" is.

Nothing about this is ambiguous: whichever module the project decides is canonical,
the release pipeline must name the same one. Today it does not.

---

## 7. The options

### Option A — finish the WorkOS migration and cut the frontend over

**What it means:** implement the app's consumed surface (`/authenticate`, `/link`,
`/projects`, `/instances`, `/deploy`, `/terminate`, `/user/:id/creds`,
`/api/github/{repositories,callback}`, `/health`) in `backend/`, keep `/api/v1` as the
canonical prefix by changing the frontend, migrate the Android desktop session
(`tauri://localhost` origin + cookie, `tauri.conf.json:31-32`) to WorkOS tokens, and
migrate users from the `database.db` schema to the `byteport.db` schema.

**Cost, measured:** the outer module implements **none** of the 13 paths the app
calls (§4). Its auth is a different identity system with its own table
(`workos_users`), so the migration is not a port but a re-implementation plus a data
migration of an incompatible `users` primary key (§5c). Its port default collides
with the app's (§10), and its release target is already wrong (§6).

**What must be true first:** a product decision that BytePort's identity provider
becomes WorkOS AuthKit. That is not a repository fact and I found no in-repo record
of it. **Evidence does not support starting A today.**

### Option B — retire `backend/`

**What it means:** delete or archive the module, its `openapi.yaml`, its docs and its
release wiring; keep `backend/byteport` as the only Go server.

**Arguments for:** no consumer; a one-shot landing history (74/104 files at one
commit); two modules contending for one port; and it is the only way to make the
ambiguity structurally impossible.

**Arguments against acting now:** deletion is irreversible and the module is not
broken — it builds, vets and its 12 test packages pass `local validation`. It holds
the only WorkOS AuthKit implementation in the repo, a hexagonal layering
(`internal/domain|application|infrastructure`) that the canonical module lacks, and
14 files of multi-cloud provider adapters under `backend/lib/cloud` with their own
test suite. Retiring it destroys a plausible future direction on the strength of an
absence of consumers *today*, without any evidence that the direction was abandoned.
**Evidence does not support B today.**

### Option C — keep both, and make the split explicit

**What it means:** declare one canonical, make the other non-canonical *by
construction* rather than by convention, and gate the open product question.

Concretely, four measures, each testable:

1. **Canonical is `backend/byteport`.** Written down once, in the repo, where a new
   agent or human will read it.
2. **`backend/` must not be able to occupy the app's port.** Change its
   `defaultPort` (`backend/main.go:19`) to a distinct value, so no invocation —
   including a bare `go run .` from `backend/` — can bind 8081 and shadow the real
   server. Today it can, and I measured the resulting failure (§10).
3. **Fix the release target** (§6): `.goreleaser.yml:5` and `release-go.yml:49` must
   name the canonical module, or split into two explicitly named artifacts.
4. **Label the module in-tree** at `backend/README.md` (does not exist today):
   module name, "not the app's backend", the product decision it is waiting on, and
   the two facts that make it undecidable by reading code (no consumer; WorkOS
   identity model).

**Cost:** low. **Benefit:** the harm actually observed — a coordinator built and
tested the wrong backend and got a misleading result — becomes impossible to reach by
accident, without destroying anything.

**What it does not do:** it does not decide A vs B. That decision is deferred, and
deferring it is stated, not hidden.

---

## 8. Recommendation

**Option C, in the form of the four measures above**, with this reasoning:

- The canonical question is **already settled by evidence** (§3). Recommending
  "keep both, unclear which is canonical" would be inventing ambiguity that the repo
  does not have.
- The **end state** for `backend/` is genuinely ambiguous: the deciding input is a
  product decision about WorkOS AuthKit that is not recorded anywhere I could find.
  So the honest recommendation is to remove the *operational* ambiguity now and
  leave the *product* question open, explicitly.
- The concrete harm is reproducible and cheap to block: with `PORT` unset, the
  outer module binds `:8081` — the app's canonical port — and answers `/authenticate`,
  `/health` and `/projects` with 404 while `/api/v1/health` answers 200. A 200 on a
  health check that the app never calls is exactly the misleading signal described in
  the incident. Moving one default port removes that failure mode entirely.

**First actions, in order** (none performed here; this document changes no code):

1. Give `backend/` its own default port (one line, `backend/main.go:19`).
2. Point `.goreleaser.yml:5` and `release-go.yml:49` at the canonical module.
3. Add `backend/README.md` and a one-line pointer from `README.md:135` /
   `docs/ARCHITECTURE.md`, stating canonical vs non-canonical.
4. Record the WorkOS decision gate as an open question with an owner.
5. Separately, and independently of this analysis: the two tracked binaries
   (`backend/database.db`, `backend/byteport/byteport-server.exe`) are hygiene items;
   untracking is a history decision for the owner.

---

## 9. Evidence that would change my mind

**Would move me to A (finish WorkOS and cut over):**
- A recorded product decision to adopt WorkOS AuthKit as BytePort's identity system.
- A commit that implements the app's 13 consumed paths in `backend/`, or a frontend
  commit that switches `API_PORT`/`getApiBaseUrl` (`frontend/web/src/lib/api.ts:16,28-50`)
  and the CSP off 8081.
- A migration plan for `users` that reconciles `id INTEGER` + `uuid TEXT` with
  `uuid UUID` without data loss, plus a statement of which SQLite file survives.
- Evidence that the outer module is the intended deployment target: a workflow that
  build-tests it on PRs, or a Dockerfile that packages it.

**Would move me to B (retire `backend/`):**
- A recorded decision that WorkOS is not the direction.
- Evidence the multi-cloud adapters under `backend/lib/cloud` are duplicated or dead:
  e.g. a superseding implementation in `backend/byteport` or another repo, with tests.
- Evidence the module's green tests are vacuous — e.g. the 12 `ok` packages are
  cached-only or assert nothing. (I ran `-count=1`; they genuinely pass in ~2 min,
  with `internal/infrastructure/secrets` alone taking 117 s.)

**Already-settled questions** (do not need more evidence): which module the app
talks to; which module has a PR-gated CI contract; which module the container builds;
which module's default port the app's CSP, `.air.toml`, Tauri shell and Windows
bootstrap script target; that `/api/v1` is unreferenced by any code outside
`backend/`; that the two `models/` packages cannot share a database.

**Would invalidate something in this document:** a non-`main` branch or an unmerged
PR that cuts the frontend over to `/api/v1` (I analysed `main` @ `2940412a` only), or
a second consumer of `/api/v1` outside this repository (out of scope; not searched).

---

## 10. Risks of leaving it as-is

**R1 — the mis-test, already realised once, and reproducible in 90 seconds.**
The incident is recorded in-tree: `docs/sessions/20260918-byteport-handoff/HANDOFF.md:66-80`
documents the two backends in a table and `HANDOFF.md:421` states plainly: *"Run the
correct backend module … Do not test against `backend/` (the `/api/v1` module); it is
not the app's backend."* That sentence exists because the mistake was made once.

I reproduced the exact failure mode. Built the outer module and ran it **with `PORT`
unset** (the state a bare `cd backend && go run .` produces):

```
2026/09/18 17:41:34 🚀 BytePort API Server starting on :8081
[GIN-debug] Listening and serving HTTP on :8081

/authenticate    -> 404
/health          -> 404
/projects        -> 404
/api/v1/health   -> 200
```

So the wrong backend takes the app's port, returns 404 on every path the app uses,
and returns **200** on the one path the app never calls. An agent or developer
checking "is the backend healthy?" gets a green light from a server the product
cannot talk to. That is the misleading 403/404 described in the incident, in the
one form that is hardest to notice.

**R2 — the release artifact is already the wrong module.** §6, `observed inventory`.
No tag has to be pushed for this to be true; the config says it.

**R3 — documentation that contradicts itself, feeding the ambiguity.**
`API_REFERENCE.md:3` states `Base URL: http://localhost:8080` and documents
byteport's routes (`/login`, `/signup`, `/health`, `/metrics`, `/projects`,
`/instances`, `/deploy`, `/terminate`, `/link`, `/authenticate`,
`/api/github/repositories`, `/user/:id/creds`) under a **JWT bearer** auth model
(`API_REFERENCE.md:5-13`) — but byteport serves a PASETO **cookie** (`lib/auth.go:189`)
on 8081. `docs/CONTRIBUTING.md:14` attributes `go 1.26.0` and module
`github.com/byteport/api` to "`backend/byteport/go.mod`", which is actually
`backend/go.mod` (`backend/byteport/go.mod:1,3` is `byteport` / `go 1.25.0`). Both
errors point a reader at the wrong module or the wrong port.

**R4 — a fix that looks applied and is not.** The packages share table names and
concepts but not code (§5). The recent api_key casing fix had to land in
`backend/byteport/models/users.go` and could not have fixed `backend/models/`,
because the outer package has no provider map to fix. Any future change made in the
wrong package will appear to be a fix while leaving the shipped behaviour unchanged —
which is precisely how the casing bug survived.

**R5 — unverifiable canonical backend in the default development state.**
`local validation`: `go test ./...` in `backend/byteport` **fails**, because
`TestAuthMiddlewareBlocksInvalidToken` (`backend/byteport/internal/routes/routes_test.go:149`)
reaches `lib.AuthMiddleware` → `ValidateToken` → `getSymmetricKey()`
(`lib/auth.go:199,143,24-26`) → `keyring.Get` → `/usr/bin/security`, which was
blocked on this host (I observed the hung child process
`/usr/bin/security find-generic-password -s BytePortTokenKeyService -wa BytePortUser`
while the same code path stalled a live server start for over 35 s). This is an
**environment-dependent operability finding, independently measured and written up in
`docs/sessions/20260919-endpoint-coverage/COVERAGE.md` §2** — it is not a reason to
prefer the outer module (whose tests passed in 119 s here); it is a reason the
canonical module's "green" state cannot be assumed. On Linux CI the keyring call
returns an error instead of blocking, so this is unlikely to reproduce there, which
makes it a local-host trap rather than a CI signal.

**R6 — the port 8080 history.** The outer module's default was 8080 until
`de1ec6b2` (2026-09-18), and **8080 is occupied on this machine right now** by an
unrelated `sl-daemon` (`lsof -nP -iTCP:8080 -sTCP:LISTEN` → `sl-daemon` PID 928,
`127.0.0.1:8080`). Two modules, one 8081 default between them, and a third party on
8080: any "just run the backend" instruction is under-specified by default, and the
docs still say 8080 in places (R3).

---

## 11. Local validation performed, and what stays UNKNOWN

**Build environment.** Plain `go build` needs the Xcode SDK override on this host
(CLT SDK 27.0 `.tbd` stubs are malformed for arm64e). All commands below ran with:

```bash
export DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer \
       SDKROOT=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk \
       CGO_ENABLED=1
```

Go toolchain observed: `go1.23.4 darwin/arm64`.

**Commands run and results (`local validation`):**

```
cd backend            && go build ./...   -> exit 0   (ld "newer macOS version" warnings only)
cd backend            && go vet   ./...   -> exit 0
cd backend            && go test -count=1 ./...  -> 12 packages ok, 0 FAIL, ~119s
                                                (internal/infrastructure/secrets alone: 116.979s)
cd backend/byteport   && go build ./...   -> exit 0
cd backend/byteport   && go vet   ./...   -> exit 0
cd backend/byteport   && go test -count=1 ./...  -> FAIL byteport/internal/routes (600.933s timeout);
                                                ok byteport/lib, ok byteport/models, ok byteport/routes
cd backend/byteport   && go test -count=1 -timeout 90s -v ./internal/routes/
                      -> panic: test timed out after 1m30s, after
                         TestAuthMiddlewareBlocksInvalidToken

# live probes (scratch SQLite, loopback only, all processes stopped afterwards)
outer module, PORT=18081 -> /api/v1/health 200 | /authenticate 404 | /health 404 | /projects 404
outer module, PORT unset -> bound :8081      -> /authenticate 404 | /health 404 | /projects 404 | /api/v1/health 200
byteport module, PORT=18082 -> never bound; stdout stopped at
   "Successfully connected to SQLite database (...probe_bp.db)";
   child /usr/bin/security find-generic-password -s BytePortTokenKeyService blocked
```

Ports 18081, 18082 and 8081 were verified released and all probe processes killed
after measurement (`lsof` empty). The scratch databases live under
`/Users/kooshapari/.jcode/scratch/`, not in the repo. No live 8081 listener existed
before the probe and none exists after.

**Deliberately not measured / UNKNOWN:**
- **Hosted readiness: UNKNOWN.** Nothing was deployed. I did not touch any remote
  environment, AWS account, or WorkOS tenant.
- **Delivered acceptance: UNKNOWN.** No end-user workflow was accepted. The coverage
  doc's F3/F4/F5 findings (`docs/sessions/20260919-endpoint-coverage/COVERAGE.md` §6)
  mean the canonical backend has three user-visible 500s; those are its findings, not
  re-measured here, and they are not evidence about the module split either way.
- **The packaged desktop app:** not launched. Whether the Tauri webview sends the
  `authToken` cookie cross-site is an open, labelled CANDIDATE in the coverage doc
  (§6 F7) and is **UNKNOWN** here; visual state is UNKNOWN by contract.
- **Any second consumer of `/api/v1` outside this repository:** not searched.
- **Whether `backend/` was ever a deployed target** (prod/staging): UNKNOWN; the
  release config suggests it was intended to be, and I found no deployment record.
- **Other hosts' SQLite files and keyring state:** UNKNOWN; the two files and the
  keychain hang reported here are this host, at this commit, on 2026-09-18/19.

---

## 12. Citation index

Backends: `backend/go.mod:1,3` · `backend/main.go:19,47-50,61,63,66` ·
`backend/server.go:49,56-57,59-60,84-99,120-138` · `backend/handlers.go:390` ·
`backend/lib/auth.go:42-56` · `backend/internal/infrastructure/auth/workos_service.go:17,20-21` ·
`backend/models/users.go:5-24` · `backend/models/users_workos.go:7-21` ·
`backend/models/providers.go:9` · `backend/models/data.go:18,78,138` ·
`backend/models/primary_keys.go:13-16` · `backend/byteport/go.mod:1,3` ·
`backend/byteport/main.go:35,76-96,110,114-121,164` ·
`backend/byteport/lib/auth.go:18-26,46-62,70-91,141-161,185-224` ·
`backend/byteport/routes/auth.go:50,84` · `backend/byteport/models/users.go:9-20,24,31-40` ·
`backend/byteport/models/data.go:16,18-21,68-79,118-136` ·
`backend/byteport/internal/routes/routes_test.go:149` ·
`backend/byteport/.air.toml:48` · `backend/byteport/byteport-server.exe` (tracked) ·
`backend/database.db` (tracked).

App and shell: `frontend/web/src/lib/api.ts:16,28-50` · `frontend/web/src/lib/config.ts:6,21` ·
`frontend/web/src/lib/components/shell/health.ts:4` · `frontend/web/src/stores/user.ts:56-66` ·
`frontend/web/src/components/projectData.ts:389,395,413,435` ·
`frontend/web/src-tauri/src/lib.rs:145-146` · `frontend/web/src-tauri/tauri.conf.json:31-32`.

Tooling and shipping: `start:15,38` · `setup-windows.ps1:180-181` ·
`Taskfile.yml:4,33,63` · `Dockerfile:4` · `docker-compose.yml:6-9` ·
`.goreleaser.yml:1,5-6` · `.github/workflows/release-go.yml:3-7,47-55` ·
`.github/workflows/ci.yml:81,88,109,128-134` · `.github/workflows/tier-0-gate.yml:29,43-46,64,81-84,102,122` ·
`.github/workflows/lint.yml:14` · `.github/workflows/deny.yml:75-83` ·
`.github/workflows/audit.yml:156-171` · `.gitignore:74-79`.

Docs: `README.md:62,135-136` · `INSTALL.md:43-48,70-73` · `AGENTS.md:40-41` ·
`ARCHITECTURE.md:16,37` · `docs/ARCHITECTURE.md:55` · `docs/CONTRIBUTING.md:14` ·
`API_REFERENCE.md:3,5-13` · `docs/openapi.yaml:52-529` ·
`docs/sessions/20260918-byteport-handoff/HANDOFF.md:66-80,421` ·
`docs/sessions/20260919-endpoint-coverage/COVERAGE.md` (§2, §5, §6 F3-F7).

Commits: `8454a74f` (2024-09-22, first under `backend/`) · `4f088064` (2024-11-23, first
under `backend/byteport/`) · `cb81ebe5` (2026-05-31, `server.go` lands) ·
`d100c85d` (2026-08-28, WorkOS middleware wired) · `de1ec6b2` (2026-09-18, port 8081 +
Tauri origin) · `9580bb95` (2026-09-18, api_key casing) · `4f821689` (2026-09-18,
SQLite default) · `41500179` (2026-09-18, gitignore) · `2940412a` (HEAD).
