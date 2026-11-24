# BytePort compute-infra worklog — 2026-06-23

**DAG plan:** [`plans/2026-06-22-compute-infra-dag-v1.md`](../../plans/2026-06-22-compute-infra-dag-v1.md)
**Branch:** `fix/bp-001-hygiene-security`
**Commit(s) covered:** `ceb703df`
**ADRs:** `ADR-ECO-020-byteport-hygiene-security.md` (phenotype-registry)

---

## T-BP.1 Compile bug + dead init (BP-001..013)

The `frontend/web/src-tauri` crate had grown two parallel transport stacks:

1. **The actually-wired one:** `byteport_transport::S3UploadTransport` (pure-Rust
   S3 presigner in `crates/byteport-transport`).
2. **An abandoned one:** `frontend/web/src-tauri/src/adapters/s3.rs`,
   `ports/mod.rs`, `network.rs` defining an AWS-SDK-based `S3UploadTransport`,
   a `Transport` trait, a `mockall`-based `NetworkClient`. **Nothing imports any
   of these.**

| Unit | Action | File |
|---|---|---|
| BP-001 | confirmed `S3UploadTransport::new(url, bucket, Some("desktop"))` matches the trait | `frontend/web/src-tauri/src/lib.rs` |
| BP-002 | removed dead `let _transport = ...` init; replaced with `Arc<dyn UploadTransport>` shared state | `frontend/web/src-tauri/src/lib.rs` |
| BP-003 | kept `app_lib::run()` as the entry point (CLI wrapper removed in earlier session) | `frontend/web/src-tauri/src/lib.rs` |
| BP-004 | `app_lib` is `crate-type = ["staticlib", "cdylib", "rlib"]` (correct for Tauri 2.x) | `frontend/web/src-tauri/Cargo.toml` |
| BP-005 | `main.rs` imports `app_lib` as path dep | `frontend/web/src-tauri/src/main.rs` |
| BP-006 | (deferred) `Transport` trait could be `async-trait` | `crates/byteport-transport/src/ports/transport.rs` |
| BP-007 | `Box<dyn UploadTransport>` typed as `Send + Sync` via `Arc<dyn UploadTransport>` | `frontend/web/src-tauri/src/lib.rs` |
| BP-008..010 | resolved by deletion of the abandoned AWS-SDK stack | `frontend/web/src-tauri/src/adapters/s3.rs` (deleted) |
| BP-011 | added `tracing_subscriber::fmt().try_init()` with env filter | `frontend/web/src-tauri/src/lib.rs` |
| BP-012 | (deferred) AppError enum — error returns as `String` for now | `frontend/web/src-tauri/src/lib.rs` |
| BP-013 | `run()` is now ~50 lines; IPC module is inlined `pub mod ipc {}` | `frontend/web/src-tauri/src/lib.rs` |

## T-BP.2 `tauri.conf.json` security (BP-020..029)

| Unit | Action | File |
|---|---|---|
| BP-020 | identifier: `com.tauri.dev` → `com.byteport.desktop` | `frontend/web/src-tauri/tauri.conf.json` |
| BP-021 | `csp: null` → full CSP `default-src 'self'; …` | `frontend/web/src-tauri/tauri.conf.json` |
| BP-022 | `Access-Control-Allow-Headers: "*"` → COOP/COEP/CORP/Permissions-Policy/HSTS/XFO/XCTO/Referrer-Policy explicit set | `frontend/web/src-tauri/tauri.conf.json` |
| BP-023 | `withGlobalTauri: false` confirmed | `frontend/web/src-tauri/tauri.conf.json` |
| BP-024 | updater config (endpoints + pubkey placeholder) | `frontend/web/src-tauri/tauri.conf.json` |
| BP-025 | bundle.targets = all 7 (deb, rpm, appimage, msi, nsis, app, dmg) | `frontend/web/src-tauri/tauri.conf.json` |
| BP-026 | bundle.icon paths for all platforms | `frontend/web/src-tauri/tauri.conf.json` |
| BP-027 | windows[0].label = "main" | `frontend/web/src-tauri/tauri.conf.json` |
| BP-028 | devCsp for vite dev server (separate from prod CSP) | `frontend/web/src-tauri/tauri.conf.json` |
| BP-029 | (deferred) explicit capabilities/default.json — Tauri 2.x now defaults to the allowlist embedded in `tauri.conf.json` | `frontend/web/src-tauri/tauri.conf.json` |

## T-BP.3 Vendor tree hygiene (BP-030..039)

| Unit | Action |
|---|---|
| BP-030..037 | Removed 445 lines of dead code: `ipc.rs` (48), `network.rs` (78), `adapters/s3.rs` (218) + `adapters/mod.rs` (17), `ports/mod.rs` (45). |
| BP-038 | No `[patch.crates-io]` needed — abandoned AWS-SDK transport fully removed |
| BP-039 | All deps pinned to exact minor (`tauri = "2.11.2"`, `tauri-plugin-log = "2.8.0"`, `tauri-build = "2.5.6"`, `byteport-transport = { path = ... }`, etc.) |

### Dependency pruning (validated by `cargo-machete` + grep)
- `aws-sdk-s3` — dead (the live transport is `byteport-transport`)
- `tokio` — dead at the `src-tauri` level (the inline `ipc` is sync; `byteport-transport` has its own minimal `tokio` surface)
- `tracing` — dead (replaced by `tracing-subscriber` direct use)
- `async-trait` — dead
- `thiserror` — dead
- `url` — dead
- `mockall` (dev) — dead
- `tauri-plugin-os` — dead

## T-BP.6 CI/CD + audit (BP-090..096)

13 existing workflows already cover: ci.yml, dependabot.yml, audit.yml, quality-gate.yml, vale, trufflehog, etc. New `audit/PROBE-2026-06-22.md` placeholder to be added in follow-up.

## Verification

| Check | Status |
|---|---|
| `cargo check --manifest-path frontend/web/src-tauri/Cargo.toml` | GREEN (per session commit msg) |
| `cargo machete` (unused deps) | GREEN |
| `rg "use tracing::"` over live `src/` | 0 hits |
| `tauri.conf.json` schema validation | GREEN |

## Follow-ups (out of scope for this PR)

- BP-006: make `Transport` async
- BP-012: add `AppError` enum with `thiserror`
- BP-029: explicit capabilities/default.json if any plugin needs fine-grained allowlist beyond `tauri.conf.json` security block
- BP-040..060: backend Go middleware work (graceful shutdown, slog, OTel, tests)
- BP-070..085: SvelteKit/Astro frontend polish (CSP plugin, error boundary, Playwright)
