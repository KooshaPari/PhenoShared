# B14: OCI Helpers Deduplication Report

**Date:** 2026-06-24
**Unit:** B14
**Type:** governance/dedup

## Summary

Created shared `oci-helpers` crate (`iac/oci-helpers/`) extracting duplicated utilities from `oci-lottery` and `oci-post-acquire`.

## Functions Extracted

| Function | Previously In | Now Lives In |
|----------|--------------|--------------|
| `home_dir()` | oci-post-acquire::main::dirs_home() | oci-helpers::home_dir() |
| `expand_home()` | oci-post-acquire::main::expand() | oci-helpers::expand_home() |
| `home_or_fallback()` | oci-lottery::main::home(), oci-lottery::config::dirs_home() | oci-helpers::home_or_fallback() |
| `which_on_path()` | oci-lottery::hooks::which_on_path() | oci-helpers::which_on_path() |
| `load_json_or()` | (new pattern) | oci-helpers::load_json_or() |
| `save_json()` | (new pattern) | oci-helpers::save_json() |

## Files Modified

- `iac/Cargo.toml` — added "oci-helpers" to workspace members
- `iac/oci-helpers/Cargo.toml` — new crate manifest
- `iac/oci-helpers/src/lib.rs` — new shared library
- `iac/oci-lottery/Cargo.toml` — added oci-helpers dependency
- `iac/oci-lottery/src/main.rs` — replaced `home()` with `home_or_fallback()`
- `iac/oci-lottery/src/config.rs` — replaced `dirs_home()` with `home_or_fallback()`
- `iac/oci-lottery/src/hooks.rs` — replaced local `which_on_path()` with `oci_helpers::which_on_path()`
- `iac/oci-post-acquire/Cargo.toml` — added oci-helpers dependency
- `iac/oci-post-acquire/src/main.rs` — replaced `expand()`/`dirs_home()` with `expand_home()`
- `iac/oci-post-acquire/src/cf.rs` — replaced `crate::expand` with `oci_helpers::expand_home()`
- `iac/oci-post-acquire/src/hooks.rs` — replaced `crate::expand` with `oci_helpers::expand_home()`
- `iac/oci-post-acquire/src/mesh.rs` — replaced `crate::expand` with `oci_helpers::expand_home()`

## Lines of Duplication Removed

- `oci-lottery::main`: removed 8 lines (`fn home()`)
- `oci-lottery::config`: removed 8 lines (`fn dirs_home()`)
- `oci-lottery::hooks`: removed 12 lines (`fn which_on_path()`)
- `oci-post-acquire::main`: removed 14 lines (`fn expand()`, `fn dirs_home()`)

**Total:** ~42 lines of duplication eliminated across 4 source files.
**Net new:** ~96 lines in `oci-helpers/src/lib.rs` (shared utility code, fully tested).
