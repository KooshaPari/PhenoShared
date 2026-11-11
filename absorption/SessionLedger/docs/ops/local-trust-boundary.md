# Local trust boundary and HTTP admission

`sl-daemon` is a single-user desktop companion, not a multi-tenant network
service. Prefer binding HTTP to loopback (`127.0.0.0/8` or `::1`). Non-loopback
binds are allowed only when a non-empty `SL_API_KEY` is configured; without that
key, `sl serve` fails at startup with an explicit deny. Put a TLS-terminating,
policy-enforcing proxy in front of any LAN/WAN exposure and treat the shared
secret as host-local credential material.

Cryptography inventory (hashing vs encryption-at-rest), Caddy/nginx TLS samples,
Phase-0 deferred KMS / envelope encryption, and recommended host at-rest
deploy patterns:
[`crypto-inventory.md`](crypto-inventory.md).

Single-tenant privacy hygiene (PII in logs, transcript retention, redaction
before export, loopback trust summary):
[`privacy-hygiene.md`](privacy-hygiene.md).

## Bind modes and API-key gate

| Bind                                      | `SL_API_KEY` | Behavior                                                                           |
| ----------------------------------------- | ------------ | ---------------------------------------------------------------------------------- |
| Loopback (`127.0.0.0/8`, `::1`)           | unset        | Local trust model: mutating and read `/api/*` routes are open to the host          |
| Loopback                                  | set          | Mutating routes (`POST /api/ingest`) require the key; read `/api/*` stay open      |
| Non-loopback (`0.0.0.0`, LAN IP, `::`, …) | unset        | **Startup deny** — configure `SL_API_KEY` or bind loopback                         |
| Non-loopback                              | set          | All `/api/*` routes require the key; `/healthz` and `/readyz` stay open for probes |

Accepted credential headers when a key is required:

```text
Authorization: Bearer <SL_API_KEY>
X-API-Key: <SL_API_KEY>
```

Unauthenticated requests return `401` with the API error envelope. Leave
`SL_API_KEY` unset for the default local desktop workflow; set it for local
automation that needs an explicit write secret, or whenever `--http-bind` is not
loopback.

Example remote-style bind (still single-tenant; TLS remains operator-owned):

```bash
export SL_API_KEY="$(openssl rand -hex 32)"
sl-daemon serve --watch ./sessions --out ./okf-out --http-bind 0.0.0.0:8080
curl -H "Authorization: Bearer $SL_API_KEY" http://127.0.0.1:8080/api/bundles
```

## Ingest admission controls

`POST /api/ingest` has process-local body-size and concurrency (bulkhead) limits:

| Environment variable        |           Default | Meaning                           |
| --------------------------- | ----------------: | --------------------------------- |
| `SL_INGEST_MAX_BODY_BYTES`  | `1048576` (1 MiB) | Maximum HTTP request-body bytes   |
| `SL_INGEST_MAX_CONCURRENCY` |               `8` | Maximum in-flight ingest handlers |

Both values must be positive integers; invalid values stop server startup.
Requests above the body limit return `413`. Requests arriving while all ingest
permits are occupied return `429`. These are admission controls, not tenant
quotas or distributed rate limits. Native tower `RateLimitLayer` is not used for
the ingest bulkhead: axum clones layers per connection, so those counters would
not share process-wide state. The ingest semaphore is the intentional bulkhead.

## General `/api/*` rate limit (tower-style)

Beyond the ingest bulkhead, `sl-daemon` can apply a process-wide fixed-window
throttle to every `/api/*` route. The budget is shared across connections (an
`Arc`-backed counter), which is the workable substitute for tower
`RateLimitLayer` under axum's per-connection service clone model.

| Environment variable    |                                                                                     Default | Meaning                                                          |
| ----------------------- | ------------------------------------------------------------------------------------------: | ---------------------------------------------------------------- |
| `SL_API_RATE_LIMIT`     | unset → **off** on open loopback; **`60`** when `SL_API_KEY` is set or bind is non-loopback | Max `/api/*` requests accepted per window (`0` / `off` disables) |
| `SL_API_RATE_WINDOW_MS` |                                                                                      `1000` | Window length in milliseconds (must be > 0)                      |

Loopback without a shared key keeps local DX: the throttle stays off unless you
set `SL_API_RATE_LIMIT` yourself. Shared-key and non-loopback paths enable the
default `60` requests per second when the env is unset. Excess `/api/*` traffic
returns `429` with `error.code="rate_limited"`. `/healthz`, `/readyz`, and
`/metrics` are not throttled.

## General `/api/*` circuit breaker

Beyond rate limiting, `sl-daemon` can apply a process-wide closed/open/half-open
circuit breaker to `/api/*`. Consecutive handler `5xx` responses trip the
breaker; while open, further `/api/*` calls return `503` with
`error.code="circuit_open"` and a `Retry-After` header. After the open window,
one half-open probe is allowed; success closes the breaker, failure re-opens it.
Client `4xx` responses do not trip the breaker. Probes and `/metrics` stay open.

| Environment variable               |                                                                                   Default | Meaning                                 |
| ---------------------------------- | ----------------------------------------------------------------------------------------: | --------------------------------------- |
| `SL_API_CIRCUIT_BREAKER`           | unset → **off** on open loopback; **on** when `SL_API_KEY` is set or bind is non-loopback | `on`/`1` enables; `off`/`0` disables    |
| `SL_API_CIRCUIT_FAILURE_THRESHOLD` |                                                                                       `5` | Consecutive `/api/*` 5xx before opening |
| `SL_API_CIRCUIT_OPEN_MS`           |                                                                                   `30000` | Open duration before a half-open probe  |

## Outbound CLI retry policy

`sl-daemon status` / `list` (and other client subcommands that call the HTTP API)
apply a bounded exponential-backoff retry on transient `reqwest` failures
(connect/timeout/request). Connection-refused for `status` still maps to
"daemon not running" without spinning retries.

| Environment variable    | Default | Meaning                                               |
| ----------------------- | ------: | ----------------------------------------------------- |
| `SL_HTTP_RETRY_MAX`     |     `2` | Extra attempts after the first (`0` / `off` disables) |
| `SL_HTTP_RETRY_BASE_MS` |    `50` | Base backoff; doubles each attempt (capped shift)     |

Clients may send `Idempotency-Key` on `POST /api/ingest` to safely retry a
successful request while the daemon process is still running. The daemon stores
the key, raw-body hash, and success response in memory only: same key plus same
body returns the prior `200` validation response, while same key plus different
body returns `409` with the API error envelope. The cache is not persisted,
shared across processes, or retained after restart.

API transport errors use this small JSON envelope where the endpoint can adopt
it without changing successful response contracts:

```json
{
  "error": {
    "code": "payload_too_large",
    "message": "ingest payload exceeds 1048576 bytes"
  }
}
```

Validation failures remain `422` with the existing validation-result JSON so
current clients retain actionable field diagnostics.

## Structured audit events

Mutating or persistence-adjacent local operations emit `tracing` events and append
the same actor/action record to a durable local audit sink. The sink is append-only:
the daemon never truncates, updates, or deletes historical records.

### Backend selection

| Environment variable | Default | Meaning                                                                                                                                |
| -------------------- | ------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `SL_AUDIT_BACKEND`   | `jsonl` | `jsonl` writes newline-delimited JSON; `sqlite` uses an append-only SQLite table (requires `sl-daemon` built with `--features sqlite`) |

### Storage paths

When `SL_DATA_DIR` is set, audit files live under that directory. Otherwise paths
are relative to the command output directory (`serve --out`, archive/restore
`--data-dir`, etc.).

| Backend           | Path                            |
| ----------------- | ------------------------------- |
| `jsonl` (default) | `<data_dir>/audit/events.jsonl` |
| `sqlite`          | `<data_dir>/audit/events.db`    |

Concrete examples:

- `$SL_DATA_DIR/audit/events.jsonl` when `SL_DATA_DIR` is set and backend is `jsonl`.
- `<serve --out>/audit/events.jsonl` for `sl serve` when `SL_DATA_DIR` is unset.
- `<data_dir>/audit/events.jsonl` for archive/restore commands that already take
  a `--data-dir`.

### Record shape and durability

Each JSONL line is a standalone JSON object written with append/create semantics,
a flush, and `sync_data`. The SQLite backend uses WAL mode and `INSERT` only into
`audit_events`; there are no daemon-driven `UPDATE` or `DELETE` statements.
Records include:

- `event_kind="audit"` in structured logs (not duplicated in the JSONL/SQLite payload)
- `actor="local"`
- `action` such as `ingest`, `export`, `archive`, or `restore`
- `outcome` and a non-payload `reason` or `resource`
- `request_id` and Unix-millisecond `timestamp`

Enable newline-delimited JSON with the `json-logs` feature and
`SL_LOG_FORMAT=json`. Events deliberately omit transcript and ingest-body
contents.

### Retention and rotation policy

`sl-daemon` does not enforce retention windows, quotas, or automatic pruning.
The sink grows until an operator rotates or archives it. That is intentional:
the daemon stays append-only and never rewrites historical audit rows.

| Knob                         | Default                  | Effect on audit retention                                                   |
| ---------------------------- | ------------------------ | --------------------------------------------------------------------------- |
| `SL_DATA_DIR`                | unset (command-specific) | When set, pins `<SL_DATA_DIR>/audit/*` across `serve`, archive, and restore |
| `SL_AUDIT_BACKEND`           | `jsonl`                  | Selects `events.jsonl` vs `events.db`; does not change retention duration   |
| `serve --out` / `--data-dir` | command default          | Audit path root when `SL_DATA_DIR` is unset                                 |

Recommended operator policy for a single-user desktop install:

1. **Retention window** — keep the active audit file until a calendar boundary
   (for example 90 days or one quarter) or until disk budget requires rotation.
   There is no daemon-side TTL; document the chosen window in your local ops
   notes if compliance requires one.
2. **Rotation** — stop or restart `sl-daemon`, then **move or copy** the active
   file to a dated archive such as
   `<data_dir>/audit/archive/events-2026-07.jsonl`. Do not truncate
   `events.jsonl` in place while the daemon is running. After rotation, create
   an empty `events.jsonl` (or let the next append recreate it) before restart.
3. **SQLite** — rotate by copying `events.db` plus any `-wal`/`-shm` siblings,
   then starting with a fresh database path or renamed archive file. The daemon
   only appends with `INSERT`; pruning requires an offline copy, not an in-process
   `DELETE`.
4. **Backup** — include `<data_dir>/audit/` in the same backup scope as OKF
   bundles. Treat exported audit copies like security-sensitive metadata (actor,
   action, resource names) even though payloads are omitted.
5. **Access control** — rely on OS file permissions plus the HTTP bind/API-key
   policy above. Audit files are not exposed over `/api/*`; local filesystem
   access remains the primary trust boundary for the sink itself.

### Export and compliance review

Audit review is a **local file operation**. No HTTP route serves the durable
sink; remote review requires copying files off the host through your normal
secure channel.

Quick checks from repo root (PowerShell 7):

```powershell
# Last 20 structured audit records (default JSONL backend)
pwsh ./scripts/audit-review.ps1 -DataDir ./.sl-data -Tail 20

# Records since a calendar date into a review bundle
pwsh ./scripts/audit-review.ps1 -DataDir ./.sl-data -Since "2026-07-01" `
  -Export ./review/audit-export.jsonl
```

Equivalent manual paths:

| Backend  | Tail / inspect                                                                                     | Export for review                                                                      |
| -------- | -------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| `jsonl`  | `Get-Content -Tail 20 $env:SL_DATA_DIR/audit/events.jsonl`                                         | Copy or `audit-review.ps1 -Export <path>`                                              |
| `sqlite` | `sqlite3 $env:SL_DATA_DIR/audit/events.db "SELECT * FROM audit_events ORDER BY id DESC LIMIT 20;"` | `audit-review.ps1 -Backend sqlite -Export <path>.jsonl` (requires `sqlite3` on `PATH`) |

Review checklist:

1. Resolve the active data root (`SL_DATA_DIR`, `serve --out`, or `--data-dir`).
2. Confirm backend (`SL_AUDIT_BACKEND` or default `jsonl`) and open the matching
   path under `audit/`.
3. Filter by `timestamp` (Unix milliseconds), `action`, or `outcome` when
   investigating a specific ingest/export/archive event.
4. Correlate `request_id` with same-day `tracing` logs (`RUST_LOG`,
   `SL_LOG_FORMAT=json`) when process logs are also retained.
5. Store exported JSONL under your evidence retention policy; do not re-import
   into `sl-daemon` — the sink is write-only from the daemon's perspective.

For scheduled rotation automation, use OS tooling (Task Scheduler, cron,
logrotate in **copytruncate off** / move-then-create mode) against
`<data_dir>/audit/events.jsonl`. See also [`runbook.md`](runbook.md#audit-retention-and-review)
and [`distribution.md`](distribution.md) for data-root layout.
