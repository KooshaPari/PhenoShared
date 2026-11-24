# Implementation Strategy

- Keep the change narrow by editing the existing `rust-coverage` job instead of adding a parallel workflow.
- Preserve the repo's pinned-action approach and existing job structure.
- Generate LCOV directly from `cargo-llvm-cov` to match Codecov input expectations cleanly.
- Use README-level documentation only; no extra root docs.

