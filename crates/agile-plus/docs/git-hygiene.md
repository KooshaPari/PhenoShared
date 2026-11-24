# Git Hygiene — AgilePlus

This document defines the branch, commit, and worktree conventions for the
AgilePlus repository.  It is the normative reference for
[eco-028-commit-hygiene](../kitty-specs/eco-028-commit-hygiene/spec.md).

## Branch naming

All branches MUST follow the pattern:

```
<type>/<scope>-<repo>
```

| Component | Valid values | Examples |
|---|---|---|
| `<type>` | `feat`, `fix`, `chore`, `ci`, `docs`, `refactor`, `perf`, `test`, `build` | `feat`, `fix` |
| `<scope>` | Free-form, kebab-case, max 20 chars | `api-v2`, `worklog-seed` |
| `<repo>` | Repository slug or `agileplus` for monorepo | `agileplus`, `phenoAI` |

### Examples

- `feat/api-v2-agileplus` — new API version in AgilePlus
- `fix/build-phenoAI` — build fix for phenoAI
- `chore/worklog-seed-FocalPoint` — worklog seeding for FocalPoint
- `docs/adr-015-agileplus` — ADR documentation

### Prohibited patterns

- `main` and `release/*` are protected — no direct pushes.
- `wip/`, `tmp/`, `test/`, `draft/` prefixes are rejected by CI.
- Upper-case letters, underscores, or spaces in branch names are rejected.
- Branches without a `<type>/` prefix are rejected by the pre-push hook.

## Commit messages

All commits MUST follow [Conventional Commits](https://www.conventionalcommits.org/)
with the exact format enforced by the `.githooks/commit-msg` hook.

### Format

```
<type>[(<scope>)][!]: <subject>

[<body>]

[<footer>]
```

### Rules

1. **Type** is required and must be one of: `build`, `chore`, `ci`, `docs`, `feat`, `fix`, `perf`, `refactor`, `revert`, `style`, `test`.
2. **Scope** is optional but recommended.  Use the crate or module name (e.g. `agileplus-api`, `telemetry`).
3. **Subject** is required, lowercase, max 72 chars, no trailing period.
4. **Body** is required for non-trivial changes.  Explain *what* and *why*, not *how*.
5. **Footer** may contain `BREAKING CHANGE:`, `Closes #NNN`, or `Refs #NNN`.
6. **No `WIP` or `TODO` alone** — the hook rejects commits whose body is exactly `WIP` or `TODO`.

### Examples

```
feat(agileplus-api): add user authentication endpoint

Implements OAuth2 client-credentials flow for service-to-service
calls.  Adds `AuthMiddleware` to the Axum router.

Closes #123
```

```
fix(telemetry): resolve race condition in span exporter

The otel-batch exporter was dropping spans when the runtime shut
down before the flush interval.  Added a graceful shutdown guard.

Refs #456
```

## Worktree hygiene

See `scripts/sweep-stale-worktrees.sh` for the weekly sweep.

### Rules

1. Worktrees older than 14 days with no new commits MUST be removed or refreshed.
2. A branch ahead of remote with a dirty working tree MUST be pushed or reset.
3. The sweep script emits `worklogs/worktree-hygiene-<date>.json` with findings.

## CI enforcement

- `.github/workflows/branch-hygiene.yml` flags PRs from stale or dirty branches.
- The pre-push hook rejects branches without a valid `<type>/` prefix.
- The commit-msg hook rejects non-conventional commits.
- `cargo clippy --workspace -- -D warnings` and `cargo fmt` must pass before merge.

## Install hooks

```bash
# One-time setup
git config core.hooksPath .githooks

# Verify
ls -l .githooks/commit-msg
```

## References

- [Conventional Commits](https://www.conventionalcommits.org/)
- [eco-028-commit-hygiene spec](../kitty-specs/eco-028-commit-hygiene/spec.md)
- [release-plz.toml](../release-plz.toml)
- [cliff.toml](../cliff.toml)
