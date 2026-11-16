# AgilePlus Security Audit — 2026-07-18

## Scope

| Area | Path | Status |
|------|------|--------|
| Dashboard Frontend | `crates/agileplus-dashboard/web/` | Audited |
| Dashboard Backend | `crates/agileplus-dashboard/src/` | Audited |
| API Layer | `crates/agileplus-api/src/` | Audited |
| OpenAPI Spec | `openapi.yaml` | Audited |
| Desktop App | `desktop/src/` | Audited |
| Edge Config | `vercel.json`, `wrangler.toml` | Audited |

---

## CRITICAL Findings

### C-1: Dashboard Backend Has Zero Authentication — All Routes Unauthenticated

**Files:**
- `crates/agileplus-dashboard/src/routes/mod.rs` (lines 96–182)
- `crates/agileplus-dashboard/src/main.rs` (lines 19–22)
- `crates/agileplus-api/src/router.rs` (lines 105–114)

**Description:**
The entire dashboard router (`agileplus_dashboard::routes::router()`) is mounted with **no authentication middleware**. In `main.rs:19`, the router is assembled and in `main.rs:22` `CorsLayer::permissive()` is applied. In `crates/agileplus-api/src/router.rs:109–114`, the dashboard routes are merged into the composite API router **outside** the protected route group (which has the `validate_api_key` middleware). This means:

- All `/api/settings/*` POST endpoints (save Plane API keys, agent config, service config) are **publicly writable** with no auth.
- All `/api/dashboard/services/{name}/restart` endpoints are **publicly callable**.
- All `/api/dashboard/services/{name}/toggle` and `/api/dashboard/services/{name}/config` endpoints are **unprotected**.
- All `/api/features/{id}/transition` state-change POST endpoints are **unprotected**.
- All `/api/features/{id}/evidence/generate` endpoints are **unprotected**.

**Exploitability:** HIGH. Any network-reachable attacker can modify configuration, trigger service restarts, transition feature states, and generate evidence bundles.

**Recommendation:** Apply the `validate_api_key` middleware (or equivalent) to the dashboard router, or gate all mutating dashboard endpoints behind authentication.

---

### C-2: Command Injection via Service Restart Endpoint

**Files:**
- `crates/agileplus-dashboard/src/routes/health.rs` (lines 277–326)
- `crates/agileplus-dashboard/src/routes/helpers.rs` (lines 345–378)

**Description:**
The `POST /api/dashboard/services/{name}/restart` handler takes the `{name}` path parameter (user-supplied) and interpolates it directly into the restart command template via `template.replace("{}", &name)` at `health.rs:292`. While there is an allowlist for the program name (`systemctl`, `docker`, `process-compose`, `echo`), the **arguments** passed via `{name}` are not validated. An attacker can inject shell metacharacters or additional arguments through the service name.

For example, with the default template `systemctl restart {}`, a request to `/api/dashboard/services/foo%20--user%20root/restart` would execute `systemctl restart foo --user root`. More critically, even though `std::process::Command` does not invoke a shell, the attacker can still pass arbitrary arguments to the allowlisted programs.

Additionally, this endpoint has **no authentication** (see C-1), so any network-reachable user can trigger arbitrary service operations.

**Exploitability:** HIGH. Unauthenticated command execution with partial argument injection. If the env var `AGILEPLUS_SERVICE_RESTART_CMD` points to `docker`, an attacker could potentially restart or stop arbitrary containers.

**Recommendation:**
1. Validate that the `{name}` parameter matches an alphanumeric allowlist of known service names.
2. Add authentication to this endpoint.
3. Use a lookup table mapping service names to specific, pre-validated restart commands instead of string interpolation.

---

### C-3: Permissive CORS on All Endpoints

**Files:**
- `crates/agileplus-dashboard/src/main.rs` (line 22): `.layer(CorsLayer::permissive())`
- `crates/agileplus-api/src/router.rs` (line 120): `.layer(CorsLayer::permissive())`
- `vercel.json` (lines 11–16): `"Access-Control-Allow-Origin": "*"`

**Description:**
All three deployment surfaces use fully permissive CORS:
- The dashboard backend allows `*` origin with all methods and headers.
- The API server uses the same `CorsLayer::permissive()`.
- The Vercel configuration explicitly sets `Access-Control-Allow-Origin: *` on all `/api/*` routes.

This means any website on the internet can make authenticated cross-origin requests to the AgilePlus API if the user's browser has credentials (cookies, cached auth headers).

**Exploitability:** MEDIUM-HIGH. Combined with the lack of auth on dashboard routes (C-1), any malicious website can call all dashboard APIs. For the protected `/api/v1/*` routes, exploitation requires the API key to be sent (typically via header, not cookies), which limits but does not eliminate risk.

**Recommendation:** Restrict CORS to the specific origins that host the dashboard (e.g., `http://localhost:5173`, `https://agileplus.<REDACTED>.dev`).

---

## HIGH Findings

### H-1: Unvalidated Evidence Generation Executes Shell Script

**File:** `crates/agileplus-dashboard/src/routes/evidence.rs` (lines 254–305)

**Description:**
`POST /api/features/{id}/evidence/generate` spawns `bash scripts/generate-evidence.sh <feature_id>` where `feature_id` is user-supplied from the URL path. While `tokio::process::Command` does not invoke a shell for the argument (the `feature_id` is passed as a separate arg, not interpolated), the underlying bash script might use the argument unsafely. The endpoint is also **unauthenticated** (see C-1), meaning anyone can trigger evidence generation for any feature.

**Exploitability:** MEDIUM. Depends on how `generate-evidence.sh` handles its argument. Direct shell injection is mitigated by `Command::arg()` passing it as a single argument, but the script itself may be vulnerable.

**Recommendation:**
1. Validate `feature_id` against a strict pattern (e.g., numeric or slug-only).
2. Add authentication.
3. Rate-limit this endpoint.

### H-2: XSS in Feature Media Gallery Handler

**File:** `crates/agileplus-dashboard/src/routes/features.rs` (lines 507–525)

**Description:**
The `feature_media` handler builds HTML by interpolating `m.url_or_path` and `m.name` directly into an HTML string using `format!()` without HTML escaping:

```rust
format!(
    r#"<div class="media-asset border rounded p-3 bg-zinc-800">
    <img src="{}" alt="{}" class="w-full rounded"/>
    <p class="text-xs text-zinc-400 mt-2">{}</p>
  </div>"#,
    m.url_or_path, m.name, m.name
)
```

The `url_or_path` and `name` fields are derived from seed data currently, but if they ever come from user input or an external data source, this is a stored XSS vulnerability. A malicious value like `" onload="alert(1)` in `url_or_path` would execute JavaScript.

The evidence module properly uses `html_escape()` (evidence.rs:54–60), but the media handler does not.

**Exploitability:** MEDIUM. Currently the data is generated server-side from seed data, but the pattern is unsafe and will become exploitable when real user data flows through.

**Recommendation:** Use the `html_escape()` function (already defined in `helpers.rs`) for all interpolated values, or use Askama templates (which auto-escape by default) instead of manual `format!()`.

### H-3: API Key Accepted via Query String

**File:** `crates/agileplus-api/src/middleware/auth.rs` (lines 45–57)

**Description:**
The auth middleware accepts `?api_key=<key>` as a query parameter fallback. This means:
- API keys will appear in server access logs, proxy logs, and browser history.
- Referrer headers may leak the key to third-party sites.
- The key is visible in URL bars if endpoints are opened in a browser.

**Exploitability:** MEDIUM. Key leakage through logs and referrer headers can lead to credential compromise.

**Recommendation:** Remove query-string authentication or restrict it to specific use cases (e.g., WebSocket connections) with short-lived tokens.

### H-4: Static File Serving Without Path Normalization

**Files:**
- `crates/agileplus-dashboard/src/main.rs` (line 20): `.nest_service("/static", ServeDir::new("templates/static"))`
- `crates/agileplus-api/src/router.rs` (line 118): `.nest_service("/static", ServeDir::new("templates/static"))`

**Description:**
`tower_http::services::ServeDir` is used with a relative path. While `ServeDir` does perform basic path traversal prevention, the path is relative to the process working directory, which could vary. If the server is started from an unexpected directory, the static file root resolves differently. Additionally, `ServeDir` does not restrict file types — any file in the `templates/static/` tree is served, including potential configuration files or data.

**Exploitability:** LOW-MEDIUM. Requires the server to be started from an unexpected CWD or for sensitive files to be placed in `templates/static/`.

**Recommendation:** Use an absolute path or a compile-time embed. Add file-type restrictions if needed.

---

## MEDIUM Findings

### M-1: Plane API Key Stored in Plaintext Config File

**Files:**
- `crates/agileplus-dashboard/src/routes/settings.rs` (lines 404–432, `save_plane_settings`)
- `crates/agileplus-dashboard/src/routes/health.rs` (lines 94–126, `Config`)

**Description:**
The `POST /api/settings/plane` handler saves the Plane API key to `~/.agileplus/config.toml` in plaintext via `toml::to_string_pretty()`. The `PlaneConfig` struct stores `api_key: String` without encryption. This is accessible to any process running as the same user. The config path is predictable (`$HOME/.agileplus/config.toml`).

**Exploitability:** MEDIUM. Requires local file read access, but the file location is predictable and the key is stored in cleartext.

**Recommendation:** Use the OS keychain (per ADR-011) or encrypt secrets at rest. At minimum, restrict file permissions to `0600`.

### M-2: Dashboard Data Directory Configurable Without Validation

**File:** `crates/agileplus-dashboard/src/routes/settings.rs` (lines 468–497, `save_dashboard_settings`)

**Description:**
The `data_directory` field from `DashboardSettingsForm` is persisted without any path validation. A malicious (unauthenticated) request could set this to an arbitrary path. Depending on how this directory is later used, this could enable path traversal or file write attacks.

**Exploitability:** LOW-MEDIUM. Depends on downstream usage of the configured directory.

**Recommendation:** Validate the path is within an allowed directory, or restrict to a predefined list of locations.

### M-3: SSE Stream Has No Authentication or Rate Limiting

**File:** `crates/agileplus-dashboard/src/routes/dashboard.rs` (lines 383–414)

**Description:**
`GET /api/stream` creates a Server-Sent Events connection that broadcasts feature and health data every 5 seconds indefinitely. There is no authentication, no connection limit, and no rate limiting. An attacker could open thousands of SSE connections to exhaust server resources.

**Exploitability:** MEDIUM. Denial-of-service via resource exhaustion.

**Recommendation:** Add authentication, connection limits, and/or a maximum connection duration.

### M-4: Evidence Content Served Without Content-Type Header

**File:** `crates/agileplus-dashboard/src/routes/evidence.rs` (lines 175–208)

**Description:**
The `evidence_content` handler reads files from `.agileplus/evidence/` and serves them wrapped in `<pre>` tags with `Html()`. While the content is HTML-escaped, the response Content-Type is `text/html`. If an attacker could place a crafted file in the evidence directory, the HTML-escaped content would render as a full HTML page. The `evidence_preview` handler (lines 210–230) has the same pattern but is additionally missing the `starts_with` path containment check that `evidence_content` has.

**Exploitability:** LOW-MEDIUM. Requires the ability to write to the `.agileplus/evidence/` directory.

**Recommendation:** Add the `starts_with` path containment check to `evidence_preview`. Consider serving evidence as `text/plain` or `application/octet-stream` instead of `text/html`.

---

## LOW Findings

### L-1: No CSRF Protection on Form Endpoints

**Files:** All POST handlers using `axum::Form` in `settings.rs`, `agents.rs`, `health.rs`

**Description:**
The settings and configuration POST endpoints accept `application/x-www-form-urlencoded` data without CSRF tokens. Combined with permissive CORS (C-3), this means any website can submit forms to these endpoints.

**Recommendation:** Add CSRF tokens for form-based endpoints, or switch to JSON-only APIs with `Content-Type` validation.

### L-2: Frontend Client-Side Routing Exposes All Views Without Server Auth

**File:** `crates/agileplus-dashboard/web/src/App.tsx` (lines 349–429)

**Description:**
Navigation between dashboard views (dashboard, epics, stories, evidence) is handled entirely client-side via React state (`useState<View>`). There is no router-based access control or server-side auth check. While the backend data is served from unauthenticated endpoints anyway (C-1), there is no mechanism to restrict views to authorized users.

**Recommendation:** Implement authentication and route guards once the auth story is completed.

### L-3: Desktop App CLI Execution Uses PATH-Based Binary Lookup

**File:** `desktop/src/cli.ts` (lines 23–31)

**Description:**
The `CLI` class defaults to `this.bin = "agileplus"` and runs it via `spawn()`. This resolves via the user's `$PATH`. In a development environment, a malicious binary named `agileplus` earlier in `$PATH` would be executed instead. The `spawn` call correctly uses array-based args (not shell interpolation), which mitigates command injection.

**Exploitability:** LOW. Requires local filesystem access to place a malicious binary.

**Recommendation:** Use an absolute path to the `agileplus` binary, or verify the binary's integrity (e.g., checksum) before execution.

### L-4: Desktop App innerHTML Usage (Properly Escaped)

**File:** `desktop/src/views/main.ts` (lines 60–86)

**Description:**
The renderer uses `innerHTML` to populate lists, but all values are passed through `escapeHtml()` (lines 88–94). The escaping handles `&`, `<`, `>`, `"` but not single quotes (`'`). This is a minor gap — single-quote escaping is needed if values are placed in single-quoted HTML attributes (currently they are not).

**Exploitability:** VERY LOW. The current code does not place escaped values in single-quoted attributes.

**Recommendation:** Add `'` → `&#39;` to the `escapeHtml` function for defense in depth.

---

## OpenAPI Spec Analysis

**File:** `openapi.yaml`

| Finding | Detail |
|---------|--------|
| Auth coverage | All 5 documented endpoints (`/api/v1/features`, `/api/v1/work-packages/{id}`, `/api/v1/events`, `/api/v1/features/{slug}/audit`, `/api/v1/features/{slug}/governance`) require `api_key` security. This is correctly enforced in `router.rs` via the `validate_api_key` middleware layer. |
| Public endpoints | Not documented in the spec but exist: `/health`, `/detailed-health`, `/info`. These are intentionally public. |
| Rate limiting | **Not defined** in the OpenAPI spec. No `x-ratelimit-*` headers or descriptions. The backend has no rate limiting implementation. |
| Request validation | Schema validation is defined for `CreateFeatureRequest` (requires `title`). No `maxLength`, `pattern`, or format constraints on string fields. |
| Dashboard endpoints | The ~40 dashboard endpoints under `/api/dashboard/*` and `/api/settings/*` are **not documented** in the OpenAPI spec, and critically, they are **not protected** by the API key middleware. |

**Recommendation:** Document all endpoints in the OpenAPI spec. Add rate limiting definitions and enforce them in the backend. Add string length/pattern constraints to schemas.

---

## Edge / Deployment Analysis

### Vercel (`vercel.json`)

| Finding | Detail |
|---------|--------|
| SPA fallback | `"rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]` — This is a standard SPA pattern and serves the React dashboard. No serverless functions or API proxies are defined. |
| CORS wildcard | `"Access-Control-Allow-Origin": "*"` on `/api/*` — see C-3. |
| No API proxy | The Vercel deployment serves only the static frontend. API calls from the browser would need to go to a separate backend origin, which means the wildcard CORS is likely intentional but still risky. |

### Cloudflare (`wrangler.toml`)

| Finding | Detail |
|---------|--------|
| Worker not implemented | `main = "src/worker.ts"` is configured but the file **does not exist**. The edge worker is a placeholder. |
| API origin exposed | `AGILEPLUS_API = "https://agileplus.<REDACTED>.dev"` — the production API hostname is hardcoded. |
| KV/R2 bindings | KV namespace `AGILEPLUS_KV` and R2 bucket `agileplus-builds` are configured but with placeholder IDs. |

**Risk:** No actual edge worker code exists, so there are no edge-specific vulnerabilities. However, when implemented, the worker must enforce auth on proxied requests to prevent the pattern where an edge proxy strips or bypasses auth headers.

---

## Desktop App Analysis

**Files:** `desktop/src/index.ts`, `desktop/src/cli.ts`, `desktop/src/repo-bridge.ts`, `desktop/src/paths.ts`, `desktop/src/views/main.ts`, `desktop/src/views/index.ts`

| Finding | Detail |
|---------|--------|
| IPC | Uses Electrobun RPC (typed `defineRPC`) with a single `getRepoState` request. No dangerous operations exposed via RPC. |
| Network isolation | The app explicitly makes **no network calls** — it reads from local filesystem only. |
| Path traversal guard | `repo-bridge.ts:89–93`: The `abs()` method validates that resolved paths stay within `repoRoot` via `startsWith()` check. This is correct. |
| Shell execution | `cli.ts:29`: Uses `spawn()` with array args (not shell interpolation). See L-3 for PATH-based lookup risk. |
| No `shell.openExternal` | No external URL handling found. |
| No `nodeIntegration` risk | Uses Electrobun (not Electron), which has a different security model. The renderer uses a typed RPC bridge rather than direct Node.js access. |

---

## Summary Matrix

| ID | Severity | Category | Exploitable Now? | Fix Priority |
|----|----------|----------|-----------------|--------------|
| C-1 | CRITICAL | AuthN | Yes | Immediate |
| C-2 | CRITICAL | Injection | Yes | Immediate |
| C-3 | CRITICAL | CORS | Yes | Immediate |
| H-1 | HIGH | Injection | Partially | High |
| H-2 | HIGH | XSS | Not yet (seed data) | High |
| H-3 | HIGH | AuthN | Yes (log leakage) | High |
| H-4 | HIGH | Path Traversal | Edge case | Medium |
| M-1 | MEDIUM | Secret Storage | Requires local access | Medium |
| M-2 | MEDIUM | Path Traversal | Requires C-1 | Medium |
| M-3 | MEDIUM | DoS | Yes | Medium |
| M-4 | MEDIUM | Info Disclosure | Requires file write | Medium |
| L-1 | LOW | CSRF | Yes (via C-3) | Low |
| L-2 | LOW | AuthZ | Design gap | Low |
| L-3 | LOW | Binary Trust | Local only | Low |
| L-4 | LOW | XSS | No | Low |
