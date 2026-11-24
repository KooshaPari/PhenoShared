# Research

## Repo signals

- `package.json` identifies the project as a Node/VitePress documentation repository.
- Available scripts are `docs:dev`, `docs:build`, `docs:preview`, and `test`.
- `docs/guides/tooling.md` documents Bun as the preferred JS runtime/package manager and
  `oxlint` for TypeScript linting, but the repo does not currently ship a lint config.

## Implementation choice

- Use the existing language-detection pattern in `Taskfile.yml`.
- Route `build` to the `docs:build` script and `test` to the `test` script.
- Implement `lint` as a repo-wide Prettier check so the task covers the handbook's
  Markdown, YAML, and TypeScript config surfaces without needing a dedicated lint script.
- Keep the fallback lint target list constrained to files that exist in the repository so
  future VitePress config reshuffles do not make the common lint task fail before it checks
  formatting.
