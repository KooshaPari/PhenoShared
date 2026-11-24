# Session Overview

- Task: QC1-001
- Goal: replace the existing mixed-language pre-commit baseline with the requested Rust, secret-scanning, and shell lint hooks
- Success criteria: `.pre-commit-config.yaml` includes `cargo fmt`, `cargo clippy`, `cargo test`, `gitleaks`, `trufflehog`, and `shellcheck`; config validates; worklog written

## Key decisions

- Keep expensive hooks on the `manual` stage to avoid making every commit run full workspace tests or whole-tree secret scans.
- Use the vendored `shellcheck-py` pre-commit hook so shell linting does not depend on a separately installed system binary.
