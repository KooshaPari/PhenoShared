# Implementation Strategy

- Keep the existing repo-language detection in `Taskfile.yml`.
- Use the package manager detected from lockfiles to invoke the repo's Node scripts.
- Route `build` to `docs:build`, `test` to `test`, and `lint` to a repo-wide formatter check.
- Leave `clean` focused on VitePress and other generated artifacts.
- Validate the handbook's full file tree with `prettier --check . --ignore-unknown` so
  the lint task stays useful as content grows across `patterns/`, `docs/`, and root docs.
