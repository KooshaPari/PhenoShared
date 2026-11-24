# Security Audit Report — AgilePlus Rust Codebase

**Date:** 2026-07-18  
**Scope:** Authentication & Authorization, SQL Injection, Path Traversal / File Operations  
**Auditor:** Automated code review  

---

## Executive Summary

The AgilePlus Rust codebase demonstrates generally sound security practices:
- SQL queries use parameterized statements throughout (`rusqlite::params![]`)
- Path traversal checks exist in the artifact and evidence subsystems
- API key authentication uses constant-time comparison

However, **7 findings** were identified, ranging from **CRITICAL** to **LOW** severity.

| ID | Severity | Category | Location | Status |
|----|----------|----------|----------|--------|
| SEC-001 | **CRITICAL** | Auth | Dashboard routes — no authentication | Exploitable |
| SEC-002 | **HIGH** | Command Injection | `restart_service` handler | Partially mitigated |
| SEC-003 | **HIGH** | Auth | gRPC server — no authentication | Exploitable |
| SEC-004 | **MEDIUM** | Auth | `CorsLayer::permissive()` | Exploitable |
| SEC-005 | **MEDIUM** | Path Traversal | `evidence_preview` handler | Exploitable |
| SEC-006 | **MEDIUM** | Command Injection | `feature_evidence_generate` handler | Partially mitigated |
| SEC-007 | **LOW** | Auth | API key in query string | Informational |

---

## 1. Authentication & Authorization Findings

### SEC-001 — CRITICAL: Dashboard Routes Expose Sensitive Operations Without Authentication

**Files:**
- `crates/agileplus-api/src/router.rs` (lines 106-114)
- `crates/agileplus-api/src/router/compose.rs` (lines 107-116)
- `crates/agileplus-dashboard/src/routes/mod.rs` (lines 96-182)

**Code:**

```rust
// crates/agileplus-api/src/router.rs lines 106-114
// Dashboard UI routes (no auth, seeded with dogfood data).
let dashboard_state = std::sync::Arc::new(tokio::sync::RwLock::new(
    agileplus_dashboard::app_state::DashboardStore::seeded(),
));
let dashboard = agileplus_dashboard::routes::router(dashboard_state);

Router::new()
    .merge(public)
    .merge(protected)
    .merge(dashboard)   // <-- merged WITHOUT auth middleware
```

**Impact:** The entire dashboard router is merged into the top-level router **without** the API key authentication middleware. This exposes ~40 endpoints including:

| Endpoint | Method | Risk |
|----------|--------|------|
| `POST /api/dashboard/services/{name}/restart` | POST | **Arbitrary service restart** (see SEC-002) |
| `POST /api/dashboard/services/{name}/toggle` | POST | Disable services |
| `PATCH /api/dashboard/services/{name}/config` | PATCH | Modify service configuration |
| `POST /api/settings/plane` | POST | Overwrite Plane API credentials |
| `POST /api/settings/agents` | POST | Modify agent pool configuration |
| `POST /api/settings/services` | POST | Add/modify service endpoints |
| `POST /api/features/{id}/transition` | POST | Change feature states |
| `POST /api/features/{id}/evidence/generate` | POST | Execute shell scripts (see SEC-006) |
| `GET /api/dashboard/health.json` | GET | Service health information disclosure |

**Exploitability:** Fully exploitable. Any network-reachable client can invoke these endpoints without any credentials.

**Attack chain:**
1. Attacker discovers the API is listening (e.g., port scan finds port 3000)
2. `POST /api/dashboard/services/NATS/restart` triggers OS command execution
3. `POST /api/settings/plane` overwrites API credentials with attacker-controlled values

**Recommendation:** Apply the auth middleware to the dashboard router, or nest it under the `protected` router group.

---

### SEC-003 — HIGH: gRPC Server Has No Authentication Interceptor

**Files:**
- `crates/agileplus-grpc/src/server/mod.rs` (lines 515-544)
- `crates/agileplus-grpc/src/server/bootstrap.rs` (lines 36-48)

**Code:**

```rust
// crates/agileplus-grpc/src/server/bootstrap.rs lines 40-44
Server::builder()
    .add_service(AgilePlusCoreServiceServer::new(service.clone()))
    .add_service(IntegrationsServiceServer::new(service))
    .serve_with_shutdown(addr, shutdown_signal())
    .await?;
```

**Impact:** The tonic gRPC server is started with `Server::builder()` without any authentication interceptor. All gRPC RPCs—including `DispatchCommand`, `GetFeature`, `ListFeatures`, `GetAuditTrail`, `CheckGovernanceGate`, and `StreamAgentEvents`—are accessible to any client that can reach the gRPC port.

The `DispatchCommand` RPC is particularly dangerous because it forwards commands to agent services:

```rust
// crates/agileplus-grpc/src/server/mod.rs lines 441-484
async fn dispatch_command(
    &self,
    request: Request<DispatchCommandRequest>,
) -> Result<Response<DispatchCommandResponse>, Status> {
    // ... dispatches to proxy router without any auth check
    let result = self.proxy
        .dispatch_agent_command(command, feature_slug, args)
        .await;
```

**Exploitability:** Fully exploitable if the gRPC port is network-accessible.

**Recommendation:** Add a tonic interceptor layer that validates Bearer tokens or API keys, similar to the HTTP middleware in `crates/agileplus-api/src/middleware/auth.rs`.

---

### SEC-004 — MEDIUM: Permissive CORS Allows Cross-Origin Attacks

**Files:**
- `crates/agileplus-api/src/router.rs` (line 120)
- `crates/agileplus-api/src/router/compose.rs` (line 122)
- `crates/agileplus-dashboard/src/main.rs` (line 22)
- `crates/agileplus-mcp-intent/src/http.rs` (line 52)

**Code:**

```rust
// crates/agileplus-api/src/router.rs line 120
.layer(CorsLayer::permissive())
```

Used in at least 4 locations across the codebase.

**Impact:** `CorsLayer::permissive()` sets `Access-Control-Allow-Origin: *` and allows all methods/headers. This means:
- Any website visited by a user with access to the AgilePlus API can make authenticated cross-origin requests
- Combined with SEC-001, any website can trigger dashboard actions (service restarts, config changes)
- API key sent via query parameter (`?api_key=`) is visible in Referer headers sent to other origins

**Note:** `agileplus_domain::config::api.rs` has a `cors_origins: Vec<String>` field but it is never used—the router always applies `CorsLayer::permissive()`.

**Recommendation:** Replace `CorsLayer::permissive()` with a configured CORS policy using `cors_origins` from the API config. At minimum, restrict allowed origins.

---

### SEC-007 — LOW: API Key Accepted in Query String

**File:** `crates/agileplus-api/src/middleware/auth.rs` (lines 45-62)

**Code:**

```rust
// crates/agileplus-api/src/middleware/auth.rs lines 45-62
} else if let Some(query) = request.uri().query() {
    query
        .split('&')
        .find_map(|pair| {
            let (k, v) = pair.split_once('=')?;
            if k == "api_key" {
                Some(v.to_string())
            } else {
                None
            }
        })
```

**Impact:** API keys passed via `?api_key=` query parameter are:
- Logged in HTTP access logs / reverse proxy logs
- Visible in browser history
- Leaked via `Referer` headers (especially dangerous with `CorsLayer::permissive()`)
- Stored in load balancer / CDN access logs

**Exploitability:** Not directly exploitable, but increases the attack surface for key leakage.

**Recommendation:** Deprecate the query parameter method. If it must be supported, add warnings in documentation and configure HSTS / referrer-policy headers.

---

## 2. SQL Injection Findings

### Result: NO VULNERABILITIES FOUND

All SQL queries in `crates/agileplus-sqlite/` use parameterized statements consistently. A thorough review of all repository modules found:

**Properly parameterized queries confirmed in:**

| File | # of `execute`/`query` calls | All parameterized? |
|------|------|------|
| `src/repository/features.rs` | 3 | Yes (`params![]`) |
| `src/repository/work_packages.rs` | 6 | Yes (`params![]`) |
| `src/repository/users.rs` | 4 | Yes (`params![]`) |
| `src/repository/backlog.rs` | 3 | Yes (`params![]`) |
| `src/repository/audit.rs` | 1 | Yes (`params![]`) |
| `src/repository/governance.rs` | 2 | Yes (`params![]`) |
| `src/repository/epics.rs` | 4 | Yes (`params![]`) |
| `src/repository/stories.rs` | 4 | Yes (`params![]`) |
| `src/repository/events.rs` | 4 | Yes (`params![]`) |
| `src/repository/metrics.rs` | 1 | Yes (`params![]`) |
| `src/repository/modules/crud.rs` | 3 | Yes (`params![]`) |
| `src/repository/modules/tags.rs` | 2 | Yes (`params![]`) |
| `src/repository/cycles/mod.rs` | 4 | Yes (`params![]`) |
| `src/repository/projects.rs` | 2 | Yes (`params![]`) |
| `src/repository/evidence.rs` | 1 | Yes (`params![]`) |
| `src/repository/sync_mappings.rs` | 2 | Yes (`params![]`) |
| `src/migrations/mod.rs` | 2 | Yes (`params![]`) |
| `src/rebuild.rs` | 1 | Yes (`params![]`) |
| `src/event_store.rs` | — | Yes |

**Note on `format!` usage:** `crates/agileplus-sqlite/src/repository/events.rs` (line 70) uses `format!` with SQL, but only to interpolate the constant `SELECT_COLS` (a compile-time `&str` containing column names)—no user input is interpolated:

```rust
// crates/agileplus-sqlite/src/repository/events.rs lines 62-84
const SELECT_COLS: &str =
    "id, entity_type, entity_id, event_type, payload, actor, timestamp, prev_hash, hash, sequence";

pub fn append_event(conn: &Connection, event: &Event) -> Result<i64, DomainError> {
    // ...
    conn.execute(
        &format!(
            "INSERT INTO events ({SELECT_COLS}) VALUES (NULL, ?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9)"
        ),
        params![
            event.entity_type,     // <-- parameterized
            event.entity_id,       // <-- parameterized
            // ... all values parameterized
        ],
    )
```

This is safe because `SELECT_COLS` is a constant defined at compile time.

---

## 3. Path Traversal / File Operations Findings

### SEC-005 — MEDIUM: `evidence_preview` Handler Lacks Path Traversal Protection

**File:** `crates/agileplus-dashboard/src/routes/evidence.rs` (lines 210-230)

**Code:**

```rust
// crates/agileplus-dashboard/src/routes/evidence.rs lines 210-230
pub async fn evidence_preview(
    State(_state): State<SharedState>,
    Path((feature_id, artifact_id)): Path<(i64, String)>,
) -> Response {
    let artifact_path = PathBuf::from(".agileplus")
        .join("evidence")
        .join(feature_id.to_string())
        .join(&artifact_id);       // <-- NO validation of artifact_id

    let text = fs::read_to_string(&artifact_path)
        .unwrap_or_else(|_| format!("No preview — artifact not found: {artifact_id}"));
```

**Contrast with sibling handler:** The `evidence_content` handler at line 175 in the same file correctly validates `artifact_id`:

```rust
// crates/agileplus-dashboard/src/routes/evidence.rs lines 184-193
// Validate artifact_id to prevent path traversal attacks
if artifact_id.contains("..") || artifact_id.starts_with('/') || artifact_id.contains('\0') {
    return Html("# Forbidden\n\nInvalid artifact ID.".to_string()).into_response();
}
let artifact_path = base_path.join(&artifact_id);
// Ensure the resolved path is within the base directory (security check)
if !artifact_path.starts_with(&base_path) {
    return Html("# Forbidden\n\nPath traversal detected.".to_string()).into_response();
}
```

But `evidence_preview` **omits both checks entirely**.

**Exploitability:** Exploitable. Combined with SEC-001 (no auth on dashboard routes):

```
GET /api/evidence/1/..%2F..%2F..%2F..%2Fetc%2Fpasswd/preview
```

This reads arbitrary files relative to the process working directory, returning contents as HTML.

**Attack chain:**
1. No authentication required (SEC-001)
2. Send `GET /api/evidence/1/../../../../etc/shadow/preview`
3. Server reads and returns the file contents

**Recommendation:** Apply the same validation from `evidence_content` to `evidence_preview`. Ideally extract into a shared validation function.

---

### SEC-002 — HIGH: Service Restart Command Injection via Path Name

**File:** `crates/agileplus-dashboard/src/routes/health.rs` (lines 277-326)

**Code:**

```rust
// crates/agileplus-dashboard/src/routes/health.rs lines 277-304
pub async fn restart_service(
    State(_state): State<SharedState>,
    Path(name): Path<String>,    // <-- user-controlled service name from URL
) -> impl IntoResponse {
    let template = std::env::var("AGILEPLUS_SERVICE_RESTART_CMD")
        .unwrap_or_else(|_| "systemctl restart {}".to_string());

    // ...
    let command_str = template.replace("{}", &name);  // <-- injected into command

    let mut command = match build_restart_command(&command_str) {
        // ...
    };

    match command.output() { /* executes the command */ }
```

**Mitigation analysis:** The `build_restart_command` function validates the first whitespace-delimited token against an allowlist:

```rust
// crates/agileplus-dashboard/src/routes/health.rs lines 156-178
const ALLOWED_RESTART_PROGRAMS: [&str; 4] = ["systemctl", "docker", "process-compose", "echo"];

fn validate_restart_command(cmd_line: &str) -> Result<(), String> {
    let mut parts: Vec<&str> = cmd_line.split_whitespace().collect();
    let program = parts.remove(0);
    if !is_restart_command_allowed(program) {
        return Err(/* ... */);
    }
    Ok(())
}
```

**Remaining vulnerability:** The `name` path parameter is interpolated into arguments passed to the allowed programs. With the default template `"systemctl restart {}"`, an attacker can supply a service name like `NATS; curl attacker.com` — but since `std::process::Command` is used (not shell execution), shell metacharacters are **not** interpreted.

**However**, argument injection is still possible:
- With `"docker restart {}"`: name = `--force somecontainer` injects extra flags
- With `"systemctl restart {}"`: name = `--no-block attacker-service` could restart unintended services
- No auth required (SEC-001)

**Exploitability:** Partially exploitable. The allowlist prevents arbitrary program execution, but argument injection via the service name can manipulate the behavior of allowed programs.

**Recommendation:**
1. Validate the `name` parameter against a strict allowlist of known service names (alphanumeric + hyphens only)
2. Add authentication to this endpoint (fix SEC-001)

---

### SEC-006 — MEDIUM: Shell Script Execution from User Input in Evidence Generation

**File:** `crates/agileplus-dashboard/src/routes/evidence.rs` (lines 254-305)

**Code:**

```rust
// crates/agileplus-dashboard/src/routes/evidence.rs lines 254-295
pub async fn feature_evidence_generate(
    State(_state): State<SharedState>,
    Path(feature_id): Path<String>,  // <-- user-controlled feature_id
) -> Response {
    let script = PathBuf::from("scripts").join("generate-evidence.sh");
    // ...
    tokio::spawn(async move {
        let out = tokio::process::Command::new("bash")
            .arg(&script)
            .arg(&fid)    // <-- feature_id passed as shell argument
            .output()
            .await;
```

**Impact:** The `feature_id` URL path parameter is passed directly as an argument to a bash script. While `tokio::process::Command` passes it as a single argv element (preventing shell injection), the script itself may interpret it unsafely (e.g., using `$1` without quoting in the shell script).

Combined with SEC-001 (no auth), any client can trigger evidence generation with an arbitrary feature_id.

**Exploitability:** Depends on the `generate-evidence.sh` script implementation. The Rust side correctly avoids shell injection by using `Command::new("bash").arg(script).arg(fid)` rather than string concatenation with `sh -c`.

**Recommendation:**
1. Validate `feature_id` against expected format (e.g., numeric or alphanumeric slug)
2. Add authentication to this endpoint (fix SEC-001)

---

## Additional Observations (Not Vulnerabilities)

### Positive Security Practices Found

1. **Constant-time API key comparison** (`crates/agileplus-api/src/middleware/token_verifier.rs` lines 58-81): Uses XOR-based byte comparison with `std::hint::black_box` to prevent timing attacks.

2. **API key generation** (`crates/agileplus-api/src/api_key.rs`): Uses 32 bytes of randomness via `rand::thread_rng()`, base64url encoding, and proper file permissions (0600).

3. **Path traversal prevention in git artifacts** (`crates/agileplus-git/src/artifact/mod.rs` lines 15-41): Properly normalizes path components and validates the result stays within the base directory.

4. **Worktree path validation** (`crates/agileplus-git/src/worktree/mod.rs` lines 136-147): Uses `canonicalize()` and `starts_with()` to ensure worktree cleanup only operates within `.worktrees/`.

5. **HTML escaping** (`crates/agileplus-dashboard/src/routes/helpers.rs` lines 235-241): Evidence content is HTML-escaped before rendering, preventing XSS in the `evidence_content` handler.

6. **Hook dispatch command execution** (`crates/agileplus-hook/src/dispatch.rs` lines 156-177): Uses `std::process::Command` (not shell), which prevents shell metacharacter injection.

### Areas for Future Hardening

1. **No RBAC/role-based checks**: The auth middleware validates API keys but does not differentiate between user roles. All authenticated users have identical access to all endpoints.

2. **`load_evidence_bundles_from_disk`** (`crates/agileplus-dashboard/src/routes/evidence.rs` line 66-70): The `feature_id` parameter is used directly in path construction without validation, but since this function is called with values from both URL parameters and internal state, it should validate the input.

3. **Pipeline executor** (`crates/agileplus-pipeline/src/executor.rs` lines 160-161, 244): Executes arbitrary shell commands from DAG node properties via `sh -c`. This is by design for a pipeline executor, but the DAG definition source should be trusted/validated.
