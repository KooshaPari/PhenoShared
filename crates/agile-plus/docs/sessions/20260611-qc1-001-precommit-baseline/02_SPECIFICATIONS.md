# Specifications

## Acceptance criteria

- `.pre-commit-config.yaml` exists at the workspace root.
- The config defines hooks for `cargo fmt`, `cargo clippy`, `cargo test`, `gitleaks`, `trufflehog`, and `shellcheck`.
- Heavy hooks are present and callable even if assigned to the `manual` stage.
- A canonical 8-field worklog file named `worklog-QC1-001-2026-06-11.json` is written.

## ARUs

- Assumption: using `manual` stage for `cargo clippy`, `cargo test`, `gitleaks`, and `trufflehog` still satisfies the task because the hooks are configured and documented.
- Risk: `shellcheck-py` or `pre-commit` may not be installed everywhere. Mitigation: prefer pinned pre-commit repos and validate config locally.
- Uncertainty: canonical worklog examples in repo are inconsistent in values, but the shared 8-field shape is stable.
