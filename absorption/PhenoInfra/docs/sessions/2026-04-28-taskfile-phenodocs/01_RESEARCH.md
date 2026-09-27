# Research Notes

## Repo Signals

- `package.json` defines the main site workflow with `bun run build`, `bun run check`, `bun run lint`, and `bun run lint:ts`.
- `pyproject.toml` exists for Python tooling, with `uv run ...` as the documented execution path.
- `scripts/check_docs_links.py` is the only Python script in `scripts/` and is a stub link-check helper.
- `libs/docslib/go.mod` defines a Go library module with tests under `libs/docslib`.
- `libs/docslib/STANDARDS.md` names `go test`, `go fmt`, and `golangci-lint` as Go quality gates.

## Implementation Decision

- Use manifest presence checks to detect whether the Bun, Python, and Go task groups should run.
- Keep the Taskfile simple and repo-local instead of introducing a second abstraction layer.
