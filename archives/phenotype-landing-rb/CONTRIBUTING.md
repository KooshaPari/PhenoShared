# Contributing

Thanks for your interest in contributing. This document covers local setup,
the quality bar, and how to get a change merged.

## Prerequisites

Install the declared toolchain for this project (see the project README). Do
not bypass the project's linters, formatters, or type checkers.

## Development Workflow

1. Branch from `main`: `git checkout -b <prefix>/<topic>`.
2. Keep commits focused. Use conventional commit prefixes (`feat`, `fix`,
   `chore`, `docs`, `refactor`, `test`).
3. Open a PR against `main` with a clear summary and test plan.

## Quality Gate

Run the local quality gate before pushing (build, lint, format, test). Do not
introduce new lint or type errors. Suppressions are not accepted as a
substitute for fixing the underlying issue.

## Security

See [SECURITY.md](./SECURITY.md) for private vulnerability reporting.

## License

By contributing, you agree your contributions are licensed under the
repository's declared license (MIT).
