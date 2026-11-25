# pheno-runtime-config

Hot-reloadable runtime configuration for the pheno-* fleet (L37).

## Status: ABSORBED into `pheno` workspace

This crate was absorbed from <https://github.com/KooshaPari/pheno-runtime-config>
on **2026-08-14** per docket `plans/dockets/N15-pheno-substrate-family.md`.

Original repo will be soft-tombstoned (archived + replaced with skeleton pointing here).

## Usage

```rust
use pheno_runtime_config::{ArcReloadable, Reloadable};
let cfg = ArcReloadable::new(42);
cfg.reload(100).unwrap();
assert_eq!(*cfg.current(), 100);
```

See `WORKLOG.md` for the absorption log and `CHANGELOG.md` for version history.