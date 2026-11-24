# Absorption Manifest — PhenoCompose

## Source

- **Repository:** `KooshaPari/PhenoTooling` (archived)
- **Revision:** `2feccc2f5b12c77785dda7960f7c31d25baf4e54` (`origin/main`)
- **Path:** `PhenoCompose/`
- **Absorbed:** 2026-11-08

## Target

Two destinations, because the source is two different kinds of thing.

**Buildable crates** (16) were absorbed earlier under commit `35fe8a24` as workspace members:

```
crates/pheno-compose-agentctl                 crates/pheno-compose-port-composer
crates/pheno-compose-apple-container-adapter  crates/pheno-compose-port-di
crates/pheno-compose-bindings                 crates/pheno-compose-port-publisher
crates/pheno-compose-i18n                     crates/pheno-compose-port-runtime
crates/pheno-compose-pheno-config             crates/pheno-compose-port-secret
crates/pheno-compose-phenocompose-cli         crates/pheno-compose-port-types
crates/pheno-compose-plugin-api               crates/pheno-compose-secret-file-adapter
crates/pheno-compose-plugin-sample            crates/pheno-compose-wslc-adapter
```

**Non-crate remainder** (41 files) is preserved verbatim here, under `docs/absorbed-from-PhenoCompose/`, with paths
relative to `PhenoCompose/`. It is archival: not a workspace member, not wired into any build.

| Area | Files | Why archival |
|---|---:|---|
| `mobile/{android-monitor,ios-shell,macos-shell}` | 6 | needs Android / Xcode / macOS app targets |
| `windows/scm-service` | 3 | needs a Windows service host |
| `ports` | 6 | orchestrator + helm/argocd adapters |
| `pheno-compose-driver` | 4 | config/error/instance/lib |
| `packages/{integration,pheno-config,pheno-errors,pheno-tracing}` | 7 | TypeScript packages with their own vitest config |
| `internal`, `nanovms` | 5 | Go internals + cgo shim |
| `benches`, `fuzz`, `tools` | 9 | bench/fuzz/release-notes/update targets |
| `bindings` | 1 | Python cross-platform build script |

## Status

**Absorbed.** The 41 files were selected by an exact test — present on `PhenoTooling origin/main`, absent from
**every object** in `PhenoShared`'s history (`rev-list --objects --all`), source-code extension — and written
byte-for-byte from the recorded revision.

This was the only group in the whole absorption sweep with no repo and no local byte-identical copy, so it was the
single real point of loss.

## Last-Resort-Exceptions

`src/helios_bench/`-style merge was **not** attempted: these are platform shells and tooling, not benchmarks or
libraries, so there is no counterpart to merge with.

Nothing was deliberately dropped. If any component later becomes live, it needs its own repo and toolchain; keeping
it here is preservation, not adoption.

## Restore-Command

```bash
git clone https://github.com/KooshaPari/PhenoTooling.git
git -C PhenoTooling checkout 2feccc2f5b12c77785dda7960f7c31d25baf4e54
cp -a PhenoTooling/PhenoCompose/. docs/absorbed-from-PhenoCompose/
```

Or, offline, from the only full backup:

```bash
git clone /Users/kooshapari/Exports/backups/PhenoTooling-20261104-2359-with-sweep.bundle PhenoTooling-restored
```
