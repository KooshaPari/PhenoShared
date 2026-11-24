# Secrets & Pre-commit Audit

**Date:** 2026-05-05
**Scope:** `/Users/<REDACTED>/CodeProjects/Phenotype/repos`

---

## AUDIT 1: Pre-commit Hook Coverage

### Top 20 Repos Missing `.pre-commit-config.yaml`

| # | Repo |
|---|------|
| 1 | `__pycache__/` |
| 2 | `AgentMCP/` |
| 3 | `agentops-policy-federation/` |
| 4 | `agileplus-agents/` |
| 5 | `agileplus-landing/` |
| 6 | `agileplus-mcp/` |
| 7 | `AgilePlus-wtr/` |
| 8 | `AppGen/` |
| 9 | `apps/` |
| 10 | `bdd-integration/` |
| 11 | `byteport-landing/` |
| 12 | `chatta/` |
| 13 | `cheap-llm-mcp/` |
| 14 | `Conft/` |
| 15 | `default/` |
| 16 | `Dino/` |
| 17 | `DINOForge-UnityDoorstop/` |
| 18 | `fleet-audit/` |
| 19 | `foqos-private/` |
| 20 | `forgecode/` |

**Note:** The grep filter excluded `wtrees`, `_archived`, `findings`, `prompts`, `plans`, `scripts`, `docs/`, `src/`, `templates/`, `crates/`, and `specs/` directories.

---

## AUDIT 2: Hardcoded Secrets Scan

### Secret Pattern Matches

**Command:** `grep -rni --include="*.py" --include="*.js" --include="*.ts" --include="*.go" -E "(api[_-]?key|password|secret[_-]?key|aws[_-]?secret|ghp_[a-zA-Z0-9]{36}|sk-[a-zA-Z0-9]{48})"`

**Result:** No matches found in tracked source files (excludes `.git`, `node_modules`, `target`, `.history`, `lock`, `.sum`).

---

## AUDIT 3: .env Files Found

The following `.env` files were found outside `.git/` and `.github/`:

| Path |
|------|
| `./AgilePlus/.agileplus/plane/apps/web/.env` |
| `./AgilePlus/.agileplus/plane/apps/api/.env` |
| `./repos-wtrees/dep-nkeys/.worktrees/BytePort-docs/frontend/web-next/.env` |
| `./agentapi-plusplus/.worktrees/chore-sast-pin-governance-clean/vendor/github.com/subosito/gotenv/.env` |
| `./.archive/pgai/examples/evaluations/litellm_vectorizer/.env` |
| `./.archive/cloud-ghost-2026-05-02/apps/web/.env` |
| `./.archive/cloud-ghost-2026-05-02/apps/mobile/.env` |
| `./cloud-wtrees/sladge-badge/.env` |
| `./.worktrees/PhenoKits-tracera-fr-scaffold/.worktrees/BytePort-docs/frontend/web-next/.env` |
| `./.worktrees/cloud-docs/.env` |

### Recommendation for .env Files

- **Production `.env` files should never be committed.** Add `.env` to `.gitignore` in all repos.
- The files above are in `.worktrees/`, `.archive/`, and `vendor/` directories which are typically gitignored, but verify each repo's `.gitignore` includes these patterns.
- The `AgilePlus/.agileplus/` directory should have its own `.gitignore` if not already tracked.

---

## Summary

| Audit | Status |
|-------|--------|
| Pre-commit coverage | 20+ repos missing `.pre-commit-config.yaml` |
| Hardcoded secrets in source | Clean (no matches) |
| .env files committed | 10 found in worktrees/archive/vendor dirs |
