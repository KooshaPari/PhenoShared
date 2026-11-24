# BytePort backend endpoint coverage (measured, not assumed)

**Date:** 2026-09-18/19
**Repo:** `/Users/kooshapari/CodeProjects/Phenotype/repos/wt-byteport-tauri-20260911`
**Backend under test:** `backend/byteport` (module `byteport`) — the app-facing server.
`backend/` (the `/api/v1` module) is a different, unlinked module; it is **not** built into this binary.
**Scope:** verification only. No code was fixed. Every status code below is an observed value from a live process.

**Branch/commit at start of run:** `main` @ `4f821689`
**Evidence class:** local validation (locally built binary + scratch SQLite + loopback HTTP).
**Readiness labels used:** observed inventory / candidate / local validation. Hosted and delivered readiness are **UNKNOWN** and are not claimed anywhere below.

---

## 0. TL;DR

- 15 routes are registered and reachable. 12 answer correctly for the situation; **3 return the wrong status** (F3 `GET /user/:id/creds` 500, F4 `GET /api/github/repositories` 500, F5 `POST /deploy` 500) — all three are hard findings, not passes. The 16th surface entry named in the task, `GET /github/status`, is **not registered at all** (404).
- `GET /user/:id/creds` returns **500 on a brand-new account** — this is deterministic, not data-dependent. The settings/integrations screen that calls it cannot load for a fresh user.
- `GET /api/github/repositories` returns **500 for any user who has not linked GitHub**.
- `POST /deploy` returns **500** (with the internal NVMS URL echoed in the body) when NanoVMS is unreachable; it is not a 502/503.
- The unmodified binary **cannot start at all** on this host: `InitAuthSystem()` blocks forever on the macOS keychain and the server never binds. See §2.
- **No mismatch was found in the direction "app calls a path the backend does not route."** Every path the SvelteKit app calls is registered. Details in §5.

---

## 1. Build

The documented workaround is real and necessary. Plain `go build` fails on this host because CommandLineTools SDK 27.0 ships `.tbd` stubs containing an `arm64e.x1-macos` architecture that its own linker rejects:

```
ld: multiple errors: tapi error: malformed file
/Library/Developer/CommandLineTools/SDKs/MacOSX27.0.sdk/usr/lib/libSystem.B.tbd:4:20: error: unknown architecture
                   arm64e.x1-macos, arm64e.x1-maccatalyst ]
```

Working build (observed, exit 0, 44 MB binary, ~11 s):

```bash
cd backend/byteport
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer \
SDKROOT=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk \
CGO_ENABLED=1 go build -o /Users/kooshapari/.jcode/scratch/bp-cov-api .
```

Build emits `ld: warning: object file ... was built for newer 'macOS' version (27.0) than being linked (26.0)` per object file. Warnings only; binary runs.

---

## 2. BLOCKER: the unmodified binary hangs forever and never binds a port

`main()` calls `lib.InitAuthSystem()`, which calls `keyring.Get(...)` for three services. `zalando/go-keyring@v0.2.8` on macOS shells out to a hardcoded `/usr/bin/security` (see `keyring_darwin.go`, `execPathKeychain = "/usr/bin/security"`). There is no env override and no timeout.

**Observed on the real binary** (`bp-cov-api`, `DATABASE_URL=file:.../bp-cov-20260919a.db PORT=18099`):

- stdout stopped after `Connected to SQLite database`; it never printed `Auth system initialized`.
- process stayed in state `S` for the full observation window (~2.5 min) with no TCP listener on 18099.
- its only child was a blocked `/usr/bin/security find-generic-password -s BytePortTokenKeyService -wa BytePortUser`.

**The keychain is wedged host-wide, not app-specific** — bounded probes of `security list-keychains` never returned, and at the time of the run ~10 unrelated `security find-generic-password -s gh:github.com` processes (other tools/agents) had been blocked since 17:01. A `SecurityAgent` GUI process has been alive since 16:09.

**Consequence for the product:** on any host where the keychain is locked, unresponsive, or absent (headless CI, locked macOS account, Linux without a Secret Service daemon), the backend hangs at startup with no error, no timeout, and no bind. A supervisor would see "process up, port closed" forever. This is a real operability finding, reported not fixed.

### 2.1 How the probes below were still obtained

Because the route surface is what this task measures, the probes were run against a **scratch copy** of the package with only key custody substituted:

- copy: `/Users/kooshapari/.jcode/scratch/bp-probe-20260919/` (41 files, `lib/` verified byte-identical after copy)
- one added file (`lib/probe_keyfile.go`) storing the same services/users/values as 0600 files under `$PROBE_KEY_DIR`
- `lib/auth.go`: exactly 4 call sites rewritten (`keyring.Get`->`probeGet` x3, `keyring.Set`->`probeSet` x1) plus the now-unused import line removed. `diff` vs the repo file is 5 lines, all shown in §7.

`main.go`, `setupRouter()`, the middleware stack, and **every handler are unmodified**. The gin route table printed by the running copy matches the `setupRouter()` source exactly, so the routing and handling under test are the real ones. The only thing not exercised as shipped is where the PASETO symmetric keys live.

**This is disclosed everywhere it matters. Nothing below is claimed to hold for the keychain-backed production path.**

---

## 3. Registered route table (authoritative, from gin debug output at boot)

```
GET    /link                     --> routes.LinkHandler            (6 handlers = +AuthMiddleware)
POST   /link                     --> routes.ValidateLink           (6)
GET    /authenticate             --> routes.Authenticate           (6)
GET    /instances                --> routes.GetInstances           (6)
GET    /projects                 --> routes.GetProjects            (6)
GET    /api/github/repositories  --> routes.RetrieveRepositories   (6)
POST   /deploy                   --> routes.DeployProject          (6)
POST   /terminate                --> routes.TerminateInstance      (6)
GET    /user/:id/creds           --> routes.UpdateLink             (6)
PUT    /user/:id/creds           --> routes.UpdateUser            (6)
POST   /login                    --> routes.Login                  (5)
POST   /signup                   --> routes.Signup                 (5)
GET    /api/github/callback      --> routes.HandleCallback         (5)
GET    /health                   --> routes.HealthHandler          (5)
GET    /metrics                  --> routes.MetricsHandler         (5)
```

`GET /github/status` is **absent**: the line is commented out at `backend/byteport/main.go` (`//protected.GET("/github/status", routes.GitHubStatusHandler)`). `GitHubStatusHandler` does not exist in the package.

---

## 4. Measured results

Probes: `curl -s --noproxy '*' --max-time 5..10` against `http://127.0.0.1:18099`. Mutating routes received empty bodies, `{}`, or malformed JSON only — never real-looking data.

### 4.1 Unauthenticated (no cookie)

| Method | Path | Observed | Interpretation |
|---|---|---|---|
| GET | `/health` | **200** `{"service":"byteport","status":"healthy","uptime":"..."}` | works, public |
| GET | `/metrics` | **200** Prometheus text | works, public |
| GET | `/authenticate` | **401** `{"error":"Authorization header missing"}` | requires auth |
| GET | `/projects` | **401** same | requires auth |
| GET | `/instances` | **401** same | requires auth |
| GET | `/link` | **401** same | requires auth |
| GET | `/api/github/repositories` | **401** same | requires auth |
| GET | `/user/:id/creds` | **401** same | requires auth |
| GET | `/api/github/callback` | **400** `{"error":"Invalid state parameter"}` | routed; validates `state` before anything else |
| GET | `/github/status` | **404** `404 page not found` | **not routed** (finding F2) |
| GET | `/` | **404** | not routed |
| GET | `/api/v1/projects` | **404** | confirms the `backend/` `/api/v1` module is not in this binary |
| GET | `/api/github/auth/webhook` | **404** | referenced only as a comment in `main.go`; not implemented |

### 4.2 Mutating routes, unauthenticated

| Method | Path | Body | Observed | Interpretation |
|---|---|---|---|---|
| POST | `/login` | empty | **400** `{"error":"EOF"}` | auth-middleware exempt; body validation |
| POST | `/login` | `{}` | **401** `{"message":"Failed, user not found"}` | binds to zero-value `email`; DB lookup miss |
| POST | `/login` | `{not-json` | **400** malformed-JSON error | validation |
| POST | `/signup` | empty | **400** `{"error":"EOF"}` | validation |
| POST | `/signup` | `{}` | **400** field-validation (`Name`, `Email` required) | validation |
| POST | `/link` | empty / `{}` | **401** | requires auth (middleware runs first) |
| POST | `/deploy` | empty / `{}` | **401** | requires auth |
| POST | `/terminate` | empty / `{}` | **401** | requires auth |
| PUT | `/user/:id/creds` | empty / `{}` | **401** | requires auth |
| POST | `/health` | — | **404** | method not routed |

### 4.3 Authenticated (session obtained from `POST /signup` on the scratch DB)

```
201 POST /signup  -> uuid e50b2279-9b5b-42fc-be1e-ab8a8114c7b3 ; real v4.local PASETO cookie
```

| Method | Path | Body | Observed | Interpretation |
|---|---|---|---|---|
| GET | `/authenticate` | — | **200**, returns `User` | works |
| GET | `/projects` | — | **200** `[]` | works (empty DB) |
| GET | `/instances` | — | **200** `[]` | works (empty DB) |
| GET | `/user/:id/creds` | — | **500** `{"error":"Failed to decrypt OAI","details":"no provider entry for \"openai\""}` | **broken for fresh users** (F3) |
| GET | `/api/github/repositories` | — | **500** `{"error":"Failed to decrypt Git token"}` | **broken for unlinked users** (F4) |
| POST | `/link` | `{}` | **400** `{"error":"Missing OpenAI API key"}` | correct validation on a no-op body |
| POST | `/deploy` | `{}` | **500** `{"error":"Failed to deploy project: Post \"http://localhost:8443/v1/deploy\": dial tcp [::1]:8443: connect: connection refused"}` | **5xx where 502/503 belongs; leaks internal URL** (F5) |
| POST | `/terminate` | `{}` | **400** `{"error":"missing sandbox ID"}` | correct validation |
| PUT | `/user/:id/creds` | `{}` | **200**, returns updated user | works as a no-op update |
| POST | `/signup` | duplicate email | **409** `{"message":"Failed, User Already Exists"}` | works |
| POST | `/login` | correct creds | **200** + `Set-Cookie` | works |
| POST | `/login` | wrong password | **401** `{"message":"Failed, invalid credentials"}` | works |

n.b. `POST /deploy` was probed with `{}` only after confirming (a) `nvmsURL()` defaults to `http://localhost:8443` and (b) nothing was listening on 8443. The outbound request was loopback-only and refused. No external host was contacted at any point in this run.

### 4.4 CORS preflight (`OPTIONS /projects`)

| Origin | Observed |
|---|---|
| `tauri://localhost` (desktop app origin) | **204**, `Access-Control-Allow-Origin: tauri://localhost`, `Access-Control-Allow-Credentials: true` |
| `http://localhost:5173` (dev origin) | **204**, allow-origin echoed, allow-credentials true |
| `http://evil.example.com` | **403** |

CORS behaves as the `main.go` comment describes; the desktop origin is admitted.

### 4.5 `/metrics` after the battery

```
byteport_uptime_seconds 94.81
byteport_requests_total 49
byteport_errors_total 38
byteport_deploys_total 0
byteport_sandboxes_active 0
byteport_goroutines 6
```

`routes.MetricsMiddleware()` **is** wired (`main.go:37`) and counters increment. Earlier suspicion that it was dead code was wrong; it is live.

---

## 5. What the desktop app actually needs, and path mismatch analysis

Every HTTP call site in `frontend/web/src` (exhaustive grep of `apiFetch`/`apiUrl`/`fetch`/`window.open`):

| App call site | Path | Routed? |
|---|---|---|
| `stores/user.ts:60` | `/authenticate` | yes |
| `lib/api.ts:117` (`isBackendReachable`) | `/health` | yes |
| `components/gitSearch.svelte:80` | `/api/github/repositories` | yes |
| `components/projectData.ts:389`, `routes/home/monitor/+page.svelte:224`, `lib/utils.ts:125` | `/projects` | yes |
| `components/projectData.ts:395`, `routes/home/monitor/+page.svelte:223` | `/instances` | yes |
| `components/projectData.ts:413` | `/deploy` | yes |
| `components/projectData.ts:435` | `/terminate` | yes |
| `routes/home/settings/integrations/+page.svelte:126` | `/user/${uuid}/creds` (GET) | yes |
| `routes/home/settings/profile/+page.svelte:86` | `/user/${uuid}/creds` (PUT) | yes |
| `routes/home/settings/integrations/+page.svelte:222`, `routes/fts/+page.svelte:197` | `/link` (POST) | yes |
| `routes/home/settings/integrations/+page.svelte:253`, `routes/fts/+page.svelte:169,271` | `/link` (GET, `window.open`) | yes |
| `routes/signup/+page.svelte:109` | `/signup` | yes |
| `routes/login/+page.svelte:88` | `/login` | yes |

**Direction 1 — app calls a path the backend does not route: NONE.** This was the highest-value thing to look for and the answer is clean. No broken link of that kind exists.

**Direction 2 — backend routes a path the app never calls:**

| Path | Assessment |
|---|---|
| `/metrics` | Not app-called. Monitoring-only; correctly public. Fine. |
| `/api/github/callback` | Not app-called by design — GitHub redirects the popup here after the `window.open(apiUrl('/link'))` OAuth start. Fine. |
| `/github/status` | **Not routed and not called.** Dead on both sides. `routes.GitHubStatusHandler` does not exist; the registration is commented out. |

Also checked in `frontend/web/src-tauri/src/lib.rs`: the Tauri shell probes `GET /health` at `http://localhost:8081` (`HEALTH_PATH`, `BACKEND_URL_DEFAULT`). That path is routed and returns 200.

---

## 6. Findings (reported, not fixed)

**F1 — Startup depends on the OS keychain with no timeout and no fallback. Severity: high, operability.**
`lib.InitAuthSystem()` -> `keyring.Get` -> blocked `/usr/bin/security` means the process never binds. No error, no timeout, no non-keychain mode. Affects headless CI, locked keychains, and any Linux host without a Secret Service. Observed as a hard hang. (`backend/byteport/main.go:145`, `lib/auth.go:46-62`)

**F2 — `GET /github/status` is not registered. Severity: low (dead code), but it is a 404.**
`main.go` has the registration commented out and `routes.GitHubStatusHandler` does not exist. A client probing it gets `404`. It is also not called by the app, so nothing is currently broken by it.

**F3 — `GET /user/:id/creds` returns 500 for a freshly created account. Severity: high, user-visible.**
`routes.UpdateLink` seeds `user.LLMConfig.Provider = "openai"` when the provider is empty, then immediately looks up a provider entry that cannot exist yet and returns `500 {"error":"Failed to decrypt OAI","details":"no provider entry for \"openai\""}`. Reproduced on a clean signup with no prior interaction. The app calls this from the settings/integrations page (`integrations/+page.svelte:126`), so that page cannot load for a new user. The handler's own default-seeding makes the failure deterministic rather than data-dependent.

**F4 — `GET /api/github/repositories` returns 500 for a user who has not linked GitHub. Severity: medium.**
`routes.RetrieveRepositories` calls `lib.DecryptSecret(user.Git.Token)` with an empty token and maps the decrypt failure to `500 {"error":"Failed to decrypt Git token"}`. "Not linked yet" is client state, not a server fault; 400/409/empty-list would be correct. Called from `gitSearch.svelte:80`.

**F5 — `POST /deploy` returns 500 and echoes the internal NVMS URL when NanoVMS is down. Severity: medium.**
Observed `500` with body `Failed to deploy project: Post "http://localhost:8443/v1/deploy": dial tcp [::1]:8443: connect: connection refused`. An unreachable upstream is a 502/503, not a 500, and the upstream address should not be revealed to the client. (`routes/deployment.go:110-125`)

**F6 — Auth failure message is misleading. Severity: low.**
`AuthMiddleware` reads only the `authToken` cookie; there is no `Authorization` header path in the code, yet every rejection says `{"error":"Authorization header missing"}`. The message sends callers down the wrong debugging path. (The handler also `TrimPrefix`es `"Bearer "` off a cookie value, which is inert.)

**F7 — CANDIDATE, UNVERIFIED: the session cookie may not be sent by the desktop webview. Severity: unknown.**
Observed on the wire: `Set-Cookie: authToken=...; Path=/; Max-Age=3600; HttpOnly; Secure; SameSite=Lax`. The cookie is the *only* auth channel. The packaged app's origin is `tauri://localhost` and it fetches `http://localhost:8081` with `credentials: 'include'`, which is cross-site from the browser's perspective; `SameSite=Lax` cookies are normally withheld from cross-site `fetch`. The cookie is also `Secure` while the backend is plain HTTP.
This is stated as a **candidate**, not a defect. I could not drive the Tauri webview in this run, and the cookie is set for the `tauri://localhost` origin path, so the practical effect is **UNKNOWN**. It is worth a targeted check in a real packaged app, because if it holds it would break every authenticated screen.

*(Noted while reading, outside the endpoint question: `routes.SetCookie` passes `c.GetHeader("Host")` as the cookie domain, which net/http rejects as invalid, so no `Domain` attribute is emitted. Host-only cookies are the desired outcome here, so this appears benign — flagged only because it means the value is silently dropped rather than applied.)*

---

## 7. Exact diff between the repo package and the probed copy

```
14d13
< 	"github.com/zalando/go-keyring"
25c24
< 	return keyring.Get(tokenKeyService, keyringUser)
---
> 	return probeGet(tokenKeyService, keyringUser)
28c27
< 	_, err := keyring.Get(service, user)
---
> 	_, err := probeGet(service, user)
43c42
< 	return keyring.Set(service, user, newKey)
---
> 	return probeSet(service, user, newKey)
102c101
< 	keyHex, err := keyring.Get(serviceKeyService, keyringUser)
---
> 	keyHex, err := probeGet(serviceKeyService, keyringUser)
```

Nothing else in `backend/byteport` differs. No repository file was modified for this report.

---

## 8. Caveats — what is UNKNOWN and is not claimed

- **No seeded data.** The scratch DB was empty; `[]` responses prove the routes return 200 correctly but do not exercise non-empty serialization, pagination, or the `AfterFind` decrypt path in `GetProjects`.
- **Success paths behind external services were never exercised.** No real GitHub, AWS, OpenAI, or portfolio endpoint was contacted. `POST /deploy`'s success path is UNVERIFIED because NanoVMS was not running; I observed only its failure path. `/api/github/callback` beyond `state` validation is UNVERIFIED.
- **Auth success paths were exercised only with a substituted key store** (§2.1). The PASETO token round-trip, session cookie, middleware gating, and handler logic are real; the key *source* is not.
- **Keychain-backed startup was never observed to succeed** on this host, so this backend's shipped startup path is UNVERIFIED as working here. It is also UNVERIFIED as broken elsewhere — this is a host-condition observation, not a claim about all environments.
- **Visual state of the desktop app: UNKNOWN.** No screenshots were taken (shared cockpit contract). Nothing about rendering, layout, or in-app error surfacing is asserted.
- **Hosted deployment readiness: UNKNOWN.** Not tested, not claimed.
- **One session, one host, one binary.** Not a load or soak test.

---

## 9. Reproduction

```bash
# 1. Build (Xcode SDK override is required on this host)
cd backend/byteport
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer \
SDKROOT=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk \
CGO_ENABLED=1 go build -o /Users/kooshapari/.jcode/scratch/bp-cov-api .

# 2. Observe the shipped binary hang before it binds (expect: no listener, no "Auth system initialized")
DATABASE_URL="file:/Users/kooshapari/.jcode/scratch/bp-cov-<unique>.db" PORT=18099 \
  /Users/kooshapari/.jcode/scratch/bp-cov-api &
lsof -nP -iTCP:18099 -sTCP:LISTEN   # nothing

# 3. Probe route surface (the copy in §2.1) on a scratch DB
PROBE_KEY_DIR=/Users/kooshapari/.jcode/scratch/bp-keys-20260919 \
DATABASE_URL="file:/Users/kooshapari/.jcode/scratch/bp-probe-20260919.db" PORT=18099 \
  /Users/kooshapari/.jcode/scratch/bp-probe-api &
curl -s --noproxy '*' --max-time 5 -o /dev/null -w '%{http_code}\n' http://127.0.0.1:18099/health   # 200
```

All probe processes were started by this run and were stopped by it. Nothing on 8081 was touched.
