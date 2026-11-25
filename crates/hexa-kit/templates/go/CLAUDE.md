# template-lang-go

Go language layer templates composed on top of template-commons

## Stack

- Template layer for: Go
- Build orchestration: Taskfile

## Structure

- `templates/` - Language-specific project templates
- `contracts/` - Interface contracts
- `scripts/` - Automation scripts
- `docs/` - Documentation

## Phenotype Org Rules

- UTF-8 encoding only in all text files. No Windows-1252 smart quotes or special characters.
- Worktree discipline: canonical repo stays on `main`; feature work in worktrees.
- CI completeness: fix all CI failures on PRs, including pre-existing ones.
- Never commit agent directories (`.claude/`, `.codex/`, `.gemini/`, `.cursor/`).
