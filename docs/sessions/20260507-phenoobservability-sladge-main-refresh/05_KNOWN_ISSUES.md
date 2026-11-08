# Known Issues

## Superseded Branch

Older prepared evidence at `aa66c86` on
`docs/phenoobservability-sladge-current` diverged from current local `main` and
is superseded by this refresh.

## Validation Blockers

`cargo fmt --all --check`, `cargo clippy --workspace --offline -- -D warnings`,
`cargo test --workspace --offline`, and `task build` all stop during Cargo
metadata loading because the workspace member `crates/pheno-dragonfly` depends
on missing sibling path
`PhenoObservability-wtrees/pheno/crates/phenotype-errors/Cargo.toml`.
