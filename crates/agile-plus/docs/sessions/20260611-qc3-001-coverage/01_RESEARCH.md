# Research

- Existing CI already had a `rust-coverage` job in `.github/workflows/ci.yml` using `cargo-tarpaulin` and `codecov/codecov-action`.
- Existing README badge convention uses top-of-file badges, currently only Scorecard, in `README.md`.
- Canonical worklog JSON in this repo uses 8 top-level fields:
  - `status`
  - `task_id`
  - `agent_id`
  - `files_changed`
  - `commit_sha`
  - `verification_result`
  - `started_at`
  - `completed_at`

