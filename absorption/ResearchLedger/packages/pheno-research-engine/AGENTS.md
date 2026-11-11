# AGENTS.md — phenoResearchEngine

**DEPRECATED** (2026-06-20) — see `DEPRECATED.md` for full deprecation notice and migration path.

> This repository is in DEPRECATED state. Do NOT initiate new feature work.
> Bug-fix-only is permitted if a downstream consumer is blocked AND the fix
> has been pre-approved by the orchestrator. See `ARCHIVED.md` for the
> migration guide to `packages/phenotype-research/`.

## Quick Links

- **Local CLAUDE.md:** See `CLAUDE.md` in this repository for project-specific guidance
- **Deprecation notice:** See `DEPRECATED.md` (canonical, dated 2026-06-20)
- **Original archive notice:** See `ARCHIVED.md` (2026-03-25)
- **Phenotype org governance:** `/path/to/phenotype/repos/CLAUDE.md`
- **Global agent guidance:** `~/.claude/AGENTS.md`
- **AgilePlus work tracking:** `cd /repos/AgilePlus && agileplus <command>`

## Key Workflows (DEPRECATED state — DO NOT USE for new work)

1. **Before implementing:** Check the active replacement at `packages/phenotype-research/`
   in the monorepo. Migrate there before any new feature work.
2. **Quality gates:** Run linters, tests, and docs validation (see CLAUDE.md) — only
   if explicitly authorized by orchestrator.
3. **Worktrees:** Do NOT create new worktrees on this repo. Use the monorepo.
4. **Integration:** Commit to canonical repo (`main`) only after orchestrator pre-approval.

## Project-Specific Gotchas

This package has 12 undeclared runtime dependencies (see `findings/deps-audit-2026-06-20-phenoResearchEngine.md`).
If you must run tests locally, install: typer, structlog, apscheduler, pydantic, orjson,
httpx, arxiv, praw, feedparser, thegent, pytest, behave.

---

**Parent contract:** Extends Phenotype-org governance. See `CLAUDE.md` and parent `AGENTS.md` for complete operating procedures.

**Deprecation status:** This file is preserved for historical reference. Active governance
lives in the monorepo and the `packages/phenotype-research/` successor module.
