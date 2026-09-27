# Testing Strategy

## Validation Commands

- `task build`: required to pass.
- `task test`: required to pass.
- `task lint`: required to exercise the wired lint paths; current repo blockers
  are tracked in `05_KNOWN_ISSUES.md`.
- `task clean`: required to pass.

## Coverage

- `task build` validates the VitePress site build, Python script compilation,
  and Go module build.
- `task test` runs the existing site/Python check flow and Go module tests.
- `task lint` runs markdown/TypeScript linting, Python pre-commit hooks, Go
  formatting, and `golangci-lint`.
- `task clean` removes generated site artifacts, Python caches, and Go test
  cache.
