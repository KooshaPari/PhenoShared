# Disabled workflows

Files here are **not** loaded by GitHub Actions. GitHub only reads
`.github/workflows/`, so nothing in this directory runs.

A workflow belongs here when it _cannot run at all_ — not when it is merely red.
A red workflow is a bug to fix. A workflow that references something
nonexistent is a latent trap: it will fail the moment its trigger fires, and
leaving it armed teaches people to ignore failures on that trigger.

Each disabled file carries a header explaining:

- what made it unrunnable,
- what was already tried,
- exactly what has to be true before it can be moved back.

| File                | Disabled   | Blocker                                                                                                                                       |
| ------------------- | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `release-macos.yml` | 2026-11-09 | calls `phenotype-fleet-ops`, a repository that no longer exists                                                                               |
| `pages.yml`         | 2026-11-10 | second GitHub Pages deployer; 0 successful runs ever, and it races `docs.yml` for the same environment. The live site is served by `docs.yml` |
