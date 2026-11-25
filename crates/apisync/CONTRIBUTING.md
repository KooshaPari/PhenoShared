# Contributing to Apisync

Thanks for considering a contribution!

## Getting Started

- Fork the repo, create a feature branch from `main`, and open a PR against `main`.
- Branch protection requires `ci / lint` and `ci / test` to pass, 1 approving review, and linear history.
- See `AGENTS.md` and `CLAUDE.md` for quality gates (cargo fmt/clippy/test, trunk).

## Development

```bash
cargo fmt --all -- --check
cargo clippy --all-targets --all-features -- -D warnings
cargo test --locked
cargo doc --no-deps
```

## Pull Requests

- Use the template in `.github/PULL_REQUEST_TEMPLATE.md`.
- Keep PRs focused, add tests for new behavior, and update `CHANGELOG.md` for user-facing changes.
- For security issues, see `SECURITY.md` — do not open public issues.

## Code of Conduct

Be respectful. By participating, you agree to uphold the project's code of conduct.

<!-- code-review signal 6 -->
