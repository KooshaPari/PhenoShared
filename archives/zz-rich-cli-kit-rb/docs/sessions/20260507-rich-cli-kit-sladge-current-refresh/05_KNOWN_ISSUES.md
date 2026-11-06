# Known Issues

## Superseded Branch

Older prepared evidence at `d2f5e47` on `docs/rich-cli-kit-sladge-current`
diverged from the active local branch and is superseded by this current-head
refresh.

## Validation Blockers

`cargo fmt --all --check` reports pre-existing Rust formatting drift in
`crates/rck-cli/src/main.rs`, `crates/rck-core/src/capabilities.rs`,
`crates/rck-core/src/emit.rs`, `crates/rck-core/src/encoder.rs`,
`crates/rck-core/src/image_data.rs`, `crates/rck-core/src/interactive.rs`,
`crates/rck-core/src/lib.rs`, `crates/rck-core/src/panel.rs`,
`crates/rck-core/src/progress.rs`, `crates/rck-core/src/shader.rs`, and
`crates/rck-core/src/spans.rs`.

`cargo clippy --workspace --offline -- -D warnings`,
`cargo test --workspace --offline`, and `task build` passed.
