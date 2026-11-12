# BytePort — Master Audit (2026-10-17)

## IDENTITY
BytePort is a Tauri+SvelteKit desktop app + Go backend that takes a Git repo and deploys it to a service. Stable GitHub repo ID `861430079`, default branch `main`, owner chat assigned.

## INTENT
Git-to-service deployment product. An installed client must complete a real repository-to-service deployment with health checks, recoverable failure and rollback on a supported target. Native launch must initialise logging once with no panic or secret leakage.

## CURRENT STATE
Last sampled commit `0b4a23b1` (2026-09-16) removed duplicate `tracing_subscriber` init in the Tauri shell so `tauri_plugin_log` owns the global `log` facade. Bounded verdict: `RECENT_LAUNCH_REPAIR_UNQUALIFIED` — the logger fix is necessary but is not yet a measured clean launch or a deployment journey.

## CODE REALITY
- `frontend/web/src-tauri/src/lib.rs:93-128` — real `tauri::Builder` with `tauri_plugin_log` + `tauri_plugin_os`, two IPC handlers (`create_upload`, `health_check`); logger fix is in place (not duplicated, not stubbed).
- `crates/byteport-transport/src/lib.rs:65-89` — `S3UploadTransport::create_upload` builds the URL + headers but does NOT call AWS SigV4 or any signer; PUT headers omit `Authorization`. No `aws-sdk-s3` or presigner in `[dependencies]`.
- `backend/byteport/` — real Go service (`main.go` 174 LOC, models 128 LOC, routes with helpers + tests, internal/auth, internal/crypto, internal/routes); `r.Run("0.0.0.0:8081")` matches Tauri's default.
- `frontend/web/src/routes/home/` — four real feature pages (instances 375, monitor 470, projects 346, settings 96 LOC) with dialogs, projectForm wizard, reviewCard, gitSearch components. Not skeleton pages.
- `frontend/web/src/lib/api.ts:18-55` — defensive `getApiBaseUrl` (Android `10.0.2.2`, localhost, `VITE_API_URL`) replaces 15 hand-rolled copies; `ApiError` + `AbortController` timeout. Real, not mock.

## STUB/MOCK/MVP-LAZINESS INVENTORY
- `stub-inventory.md:4` — self-declared total "7 entries across 4 files"; all but one are in legacy `backend/nvms/` (excluded from current build). 6/7 are comment-context or sentinel errors, not real stubs.
- `crates/byteport-transport/src/lib.rs:65-89` — `S3UploadTransport::create_upload` is pre-sign-stub: produces a raw PUT URL with no SigV4 / presigner; payload to private bucket would 403.
- `frontend/web/src-tauri/vendor/aws-runtime/` — vendored AWS SDK runtime present (sigv4.rs, retries.rs, content_encoding.rs) but never wired into the transport trait; dormant dead code.
- `backend/byteport/models/secrets.go` — 9 LOC file, presumably secret table schema; size suggests thin stub-style rather than real secret manager integration.
- `frontend/web/src/stories/Page.svelte:32,42` — Storybook docs literally say "Render pages with mock data" — that's Storybook convention, not a production stub, but worth noting.
- No `TODO`/`FIXME`/`unimplemented!`/`todo!()` markers found in `frontend/web/src/`, `frontend/web/src-tauri/src/`, `crates/byteport-*/src/`, or `backend/byteport/` (the smoke-test binary matched `backend/byteport/byteport-server.exe` as binary noise).

## FWD PATH TO FINISH
1. Add `aws-sdk-s3` (or `aws-sigv4`) to `crates/byteport-transport/Cargo.toml` and have `S3UploadTransport::create_upload` call `get_presigned_url(PutObject, …)` — 30 min, makes the upload actually usable.
2. Wire vendored `aws-runtime` glue (env, retries) into the presigner config — 20 min.
3. Run `cargo test -p byteport-transport` against a `LocalStack` or `MinIO` container; add one integration test that PUTs a 1-byte object and asserts 200 — 30 min.
4. End-to-end smoke: `cd backend/byteport && go run .`, then `cargo tauri dev`, click "New Project" through `projectForm`, confirm health probe + presigned upload lands in the bucket — 30 min.
5. Capture a VHS tape of the journey + a screenshot of the bucket listing after deploy, attach to PR — 20 min.

## TIME-TO-FINISH ESTIMATE
2.0 to 2.5 hours of focused work to a "real service responds, recovery demonstrated" outcome. Confidence: **medium-high** (the surface is small and the gap is one well-understood dependency, but AWS SigV4 against S3-compatible endpoints has hidden gotchas like path-style vs virtual-host).

## SUNSET/KEEP CALL
**KEEP.** The product is real, recent commits are meaningful (logger dedup is a genuine correctness fix), and the only material gap is the missing presigner — a single-dependency add, not a rebuild. Sunset would waste ~2 hours of integration vs a multi-day pivot.

## CONFIDENCE
**Medium-high.** Source inspected read-only at commit `d58b6e07` worktree tip (Oct 14 local); STATE.md is dated 2026-09-16 and may not reflect intervening work, but the logger fix is committed in the source.
