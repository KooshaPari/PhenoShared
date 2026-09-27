# Known Issues

## Validation Blockers

- `task lint` currently fails on existing markdownlint violations in `docs/adr`,
  `docs/guides`, `docs/planning`, `docs/reference`, `docs/roadmap`, and
  `docs/views`.
- The Python pre-commit security guard requires a GitGuardian API key before
  `uv run pre-commit run --all-files` can complete locally.
- `golangci-lint run ./...` currently reports an existing staticcheck issue in
  `libs/docslib/parser.go` where `strings.HasSuffix` is called without using its
  return value; `go build ./...` and `go test ./...` passed.
