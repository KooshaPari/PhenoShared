# ResearchLedger — AGENTS.md

## Project Overview

ResearchLedger is a **local-first research ledger and LLM knowledge
base**. The desktop app keeps Markdown and SQLite data local,
preserves source provenance, and serves as the durable store for
research notes, citations, and machine-readable evidence.

| Aspect         | Value                                                         |
| -------------- | ------------------------------------------------------------- |
| Language stack | React + TypeScript (Bun), Tauri 2 desktop shell, Rust         |
| Storage        | Local SQLite + local Markdown files                           |
| Audience       | Researchers, knowledge workers, agents writing research notes |
| Distribution   | Local desktop app (no telemetry)                              |

## Workspace Layout

```
ResearchLedger/
├── apps/desktop/src-tauri/     # Tauri shell, Rust core, SQLite migrations
├── docs/                       # User-facing docs
├── dist/                       # Built artifacts
├── index.html                  # Entry point
├── package.json                # Root package manifest
├── bun.lock                    # Bun lockfile
├── LICENSE                     # License
├── CHANGELOG.md                # Release notes
└── audits/                     # Audit-trail artifacts (added 2026-08-11)
    ├── README.md
    ├── org-audit-snapshots/
    ├── postmortems/
    ├── ci-exceptions/
    ├── boundary-reconciliation/
    └── absorption-justifications/
```

## Branch Discipline

- `main` is protected; all changes flow through PRs.
- Branch naming: `feat/`, `fix/`, `chore/`, `docs/`, `refactor/`.
- Knowledge-base content updates (notes, citations) commit via
  `docs(content):` prefix so the changelog can grep them.

## Conventions

- TypeScript with strict mode; prefer named exports.
- Markdown notes are dated `YYYY-MM-DD-<slug>.md` and live under
  `docs/notes/`.
- Cite sources inline using `[[wikilink]]` notation; the build
  resolves these to `linkedin-capture.json` (or similar) at link time.

## Quality Gates

- `bun install --frozen-lockfile`
- `bun run lint` (tsc --noEmit)
- `bun run test` (vitest)
- `bun run build` (tsc + Vite)
- `RESEARCHLEDGER_SKIP_BUNDLE_RESOURCE_VALIDATION=1 cargo test --manifest-path apps/desktop/src-tauri/Cargo.toml --lib`

## Key Commands

- `bun run dev` — start the frontend development server
- `bun run tauri dev` — start the local Tauri desktop app
- `bun run build` — build the frontend bundle
- `bun run release:macos -- --dry-run` — print the non-mutating macOS release plan

## Important Notes

- ResearchLedger is **local-first**. Do not add features that
  require sending data to a remote server.
- Source provenance is non-negotiable. Every note must link back to
  at least one source (URL, paper, conversation reference).
- LinkedIn is manual permalink/content import only. Do not add browser capture,
  cookie extraction, session cloning, or CAPTCHA automation for it.

## Cross-references

- Parent context: `/path/to/phenotype/repos/_cockpit/audit-ResearchLedger.json`
- Backlog: `X-DOCS-022` (closes "Missing AGENTS.md" gap from
  `_cockpit/XREPO_BACKLOG.json`).
- Sister audit-dir commits: Benchora `bd8b717`, PhenoPlugins
  `0fc70fb`, Eidolon `cc20a5e`, RepoLedger `11fde57`.
- Phenotype root: `/path/to/phenotype/repos/CLAUDE.md`.
