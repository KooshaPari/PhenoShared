# Absorption Manifest — PhenoCompose

**Status:** absorbed. This manifest exists so `bin/repo-delete-gate.sh` gate (a) can pass for `PhenoCompose`
material held in `PhenoTooling`.

- **Source repo:** `KooshaPari/PhenoTooling` (archived)
- **Source revision:** `2feccc2f5b12c77785dda7960f7c31d25baf4e54` (`origin/main`)
- **Source path:** `PhenoCompose/`
- **Absorbed:** 2026-11-08
- **Method:** blob-identity sweep of PhenoShared `HEAD` and its entire object graph, then a verbatim port of every
  source file that existed nowhere in that history.

## What was already absorbed

The 16 buildable crates were absorbed earlier (commit `35fe8a24`, "absorb PhenoCompose (16 crates)") and live in
this repo as workspace members:

```
crates/pheno-compose-agentctl              crates/pheno-compose-port-composer
crates/pheno-compose-apple-container-adapter  crates/pheno-compose-port-di
crates/pheno-compose-bindings              crates/pheno-compose-port-publisher
crates/pheno-compose-i18n                  crates/pheno-compose-port-runtime
crates/pheno-compose-pheno-config          crates/pheno-compose-port-secret
crates/pheno-compose-phenocompose-cli      crates/pheno-compose-port-types
crates/pheno-compose-plugin-api            crates/pheno-compose-secret-file-adapter
crates/pheno-compose-plugin-sample         crates/pheno-compose-wslc-adapter
```

## What this manifest covers (the 41 files that were NOT absorbed)

These are the non-crate parts of `PhenoCompose/` — platform shells, tooling, language bindings and Go internals.
They are preserved **verbatim** under `docs/absorbed-from-PhenoCompose/`, with their paths relative to
`PhenoCompose/`. They are archival: they are **not** workspace members and are **not** wired into any build.

| Area | Files | Why it is archival rather than a crate |
|---|---:|---|
| `mobile/android-monitor` | 2 | JNI bridge + lib; needs an Android toolchain |
| `mobile/ios-shell` | 1 | iOS shell; needs Xcode |
| `mobile/macos-shell` | 3 | FFI + launchd + lib; needs a macOS app target |
| `windows/scm-service` | 3 | Windows service; needs a Windows service host |
| `ports` | 6 | orchestrator + helm/argocd adapters |
| `pheno-compose-driver` | 4 | config/error/instance/lib |
| `packages/integration`, `pheno-config`, `pheno-errors`, `pheno-tracing` | 7 | TypeScript packages with their own vitest config |
| `internal`, `nanovms` | 5 | Go internals + cgo shim |
| `benches`, `fuzz`, `tools` | 9 | bench/fuzz/release-notes/update targets |
| `bindings` | 1 | Python cross-platform build script |

## Verification

- The 41 paths were selected by an exact test: present on `PhenoTooling origin/main`, **absent from every object in
  `PhenoShared`'s history** (`rev-list --objects --all`), and having a source-code extension.
- All 41 were written byte-for-byte from the recorded source revision (no transformation).
- Reproduce with `docs/sessions/2026-11-07-session-handoff/06_TESTING_STRATEGY.md` §3.

## What this does NOT do

- It does not make these components buildable here. If any becomes live, it needs its own repo and toolchain.
- It does not assert these 41 are the only PhenoCompose material left anywhere; it asserts they existed nowhere in
  PhenoShared's history and now do.
