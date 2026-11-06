# Contributing to PhenoVCS

Standardized Phenotype-org contribution guidelines.

## Development Workflow

- Follow the branch-based delivery protocol described in `CLAUDE.md` / `AGENTS.md`.
- Run local quality gates (build, lint, test) before opening a PR.
- Document user-facing changes in `CHANGELOG.md` under the `[Unreleased]` section.
- AgilePlus spec references are required for non-trivial work; see
  `/Users/kooshapari/CodeProjects/Phenotype/repos/AgilePlus`.
- Reuse shared infrastructure from
  [`phenoShared`](https://github.com/KooshaPari/phenoShared) where applicable
  before hand-rolling utilities.

## Branch Naming

Use `<type>/<topic>`, e.g. `feat/new-transport`, `fix/retry-backoff`,
`chore/hygiene-bootstrap`, `docs/architecture-overview`.

## Commit Style

Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`,
`perf:`, `build:`, `ci:`).

## PR Checklist

- [ ] Tests added or updated (with FR/spec traceability where applicable).
- [ ] `CHANGELOG.md` updated under `[Unreleased]`.
- [ ] Lint, format, and test gates pass locally.
- [ ] No suppressed lint/type errors without an inline justification + tracking
      reference.
- [ ] Linked AgilePlus spec / issue if applicable.
