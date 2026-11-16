# Python Test Infrastructure Audit

**Date:** 2026-05-05
**Scope:** Canonical repos at `/Users/<REDACTED>/CodeProjects/Phenotype/repos`

---

## AUDIT 1: Python Repos Missing Test Infrastructure

### Summary Table

| Repo | pyproject.toml | tests/ | pytest/unittest | CI Workflow | tests/__init__.py |
|------|----------------|--------|-----------------|-------------|-------------------|
| agent-user-status | YES | YES | NO | NO | NO |
| agileplus-mcp | YES | YES | pytest | YES | YES |
| AuthKit | YES | YES | pytest | YES | YES |
| cheap-llm-mcp | YES | YES | pytest | NO | NO |
| dispatch-mcp | YES | YES | pytest | YES | NO |
| helios-router | YES | YES | pytest | NO | NO |
| heliosBench | YES | YES | pytest | NO | NO |
| helioscope | YES | YES | pytest | YES | YES |
| Httpora | YES | YES | pytest | YES | YES |
| McpKit | YES | YES | pytest | YES | YES |
| Parpoura | YES | YES | pytest | NO | YES |
| phenodocs | YES | YES | pytest | NO | YES |
| phenodocs-scorecard-remediation | YES | NO | NO | NO | NO |
| PhenoMCP | YES | YES | NO | NO | YES |
| phenoResearchEngine | YES+setup.py | YES | pytest+unittest | NO | YES |
| PhenoRuntime | YES | YES | NO | NO | YES |
| phenotype-omlx | YES | YES | pytest | NO | NO |
| PolicyStack | YES | YES | pytest | YES | YES |
| portage | YES | YES | pytest | YES | YES |
| python | YES | YES | pytest | NO | YES |
| QuadSGM | YES | YES | pytest | NO | NO |
| thegent | YES | YES | pytest | YES | YES |
| Tracera | YES | YES | pytest | YES | YES |

### Repos with Python Code but NO CI Workflow (8 repos)

1. **agent-user-status** - Has tests/ but no pytest/unittest in pyproject.toml, no CI
2. **cheap-llm-mcp** - Has tests/ with pytest but no CI workflow
3. **helios-router** - Has tests/ with pytest but no CI workflow
4. **heliosBench** - Has tests/ with pytest but no CI workflow
5. **Parpoura** - Has tests/ with pytest but no CI workflow
6. **phenodocs** - Has tests/ with pytest but no CI workflow
7. **phenodocs-scorecard-remediation** - Has pyproject.toml but NO tests/ directory at all
8. **PhenoMCP** - Has tests/ but no pytest/unittest in pyproject.toml, no CI
9. **phenoResearchEngine** - Has tests/ with pytest+unittest but no CI workflow
10. **PhenoRuntime** - Has tests/ but no pytest/unittest in pyproject.toml, no CI
11. **phenotype-omlx** - Has tests/ with pytest but no CI workflow
12. **python** - Has tests/ with pytest but no CI workflow
13. **QuadSGM** - Has tests/ with pytest but no CI workflow

### Repos with NO tests/ directory at all (1 repo)

- **phenodocs-scorecard-remediation** - Has pyproject.toml with pytest dependency but no tests/ directory

---

## AUDIT 2: Broken CLAUDE.md References

### Broken References Found

| Referencing Repo | Broken Reference | Actual Path | Status |
|-----------------|------------------|-------------|--------|
| helioscope | `heliosCLI` | `helios-cli` | Wrong casing/path |

### Valid References Verified

- `PlayCua` - EXISTS
- `helios-cli` - EXISTS
- `phenotype-shared` - EXISTS
- `phenoShared` - EXISTS
- `phenodocs` - EXISTS
- `phenotype-omlx` - EXISTS
- `nanovms` - EXISTS
- `Paginary` - EXISTS
- `PhenoHandbook` - EXISTS
- `phenodocs-scorecard-remediation` - EXISTS
- `PhenoKits` - EXISTS
- `PhenoProc` - EXISTS
- `phenotype-ops-mcp` - EXISTS
- `phenotype-hub` - EXISTS
- `phenotype-org-audits` - EXISTS
- `phenotype-tooling` - EXISTS
- `thegent` - EXISTS
- `PhenoRuntime` - EXISTS
- `PhenoMCP` - EXISTS
- `AgilePlus` - EXISTS (canonical)
- `~/.claude/CLAUDE.md` - EXISTS (global)

### Notable: Self-Referential Repos

These repos reference themselves in their own CLAUDE.md (acceptable):

- `phenotype-org-audits` - references `phenotype-org-audits`
- `phenoShared` - references `phenotype-shared` (sibling, both exist)
- `phenotype-hub` - references `phenotype-hub`

---

## Recommendations

### High Priority: Add CI Workflow

These 13 Python repos have tests but no CI:
- agent-user-status
- cheap-llm-mcp
- helios-router
- heliosBench
- Parpoura
- phenodocs
- PhenoMCP
- phenoResearchEngine
- PhenoRuntime
- phenotype-omlx
- python
- QuadSGM

### Medium Priority: Add Test Infrastructure

- **phenodocs-scorecard-remediation** - Has pyproject.toml with pytest but no tests/ directory

### Low Priority: Fix CLAUDE.md Reference

- **helioscope** - Fix `heliosCLI` reference to `helios-cli`
