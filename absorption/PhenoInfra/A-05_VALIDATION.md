# A-05 VALIDATION — Fix build.rs link chain

**Date:** 2026-06-23
**Status:** ✅ PASS

## Checklist

| Item | Status |
|------|--------|
| nvms-ffi/build.rs handles 3 modes (pre-built lib / Go on-the-fly / stub shim) | ✅ |
| nvms-ffi/src/lib.rs shim module gated by `#[cfg(not(nvms_core_lib))]` | ✅ |
| nanovms-core/build.rs does not panic on Go failure (falls back gracefully) | ✅ |
| nvms_core.go build constraint changed from `ignore` to `cgo` | ✅ |
| Top-level Makefile has `nvms-c-archive` target | ✅ |
| Pre-existing CGo type errors documented in A-05_KNOWN_ISSUES.md | ✅ |
| Git commit | ✅ |

## Git SHA
`1fb03fb` — A-05: fix build.rs link chain for nvms-ffi -> nanovms-core
