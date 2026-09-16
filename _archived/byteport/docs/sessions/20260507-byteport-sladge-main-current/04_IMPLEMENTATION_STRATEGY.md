# Implementation Strategy

- Treat `BytePort-wtrees/sladge-pem-current` as stale prepared evidence because
  it is behind current `main`.
- Use a fresh isolated worktree from canonical `main`.
- Keep the Sladge change documentation-only.
- Keep the Go change limited to removing unused imports, with no tracer behavior
  changes.

