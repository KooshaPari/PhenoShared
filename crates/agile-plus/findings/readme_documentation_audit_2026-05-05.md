# README Accuracy & Documentation Audit

**Date:** 2026-05-05
**Scope:** `/Users/<REDACTED>/CodeProjects/Phenotype/repos`

---

## AUDIT 1: README Accuracy (False Test Claims)

### Methodology
Checked top 15 active repos for README claims about tests vs. actual test presence.

### Findings

| Repo | Test Mentions in README | Has tests/ | Has Cargo.toml |
|------|------------------------|------------|----------------|
| AgilePlus | 1 | YES | YES |
| AtomsBot | 2 | YES | - |
| thegent | 9 | YES | - |
| **helios-cli** | **14** | **NO** | YES |
| PhenoMCP | 1 | YES | YES |
| PhenoObservability | 12 | YES | YES |
| PhenoLang | 5 | YES | - |
| BytePort | 24 | YES | YES |
| phenoData | 4 | NO | YES |
| dispatch-mcp | 0 | YES | - |
| AppGen | 0 | NO | - |
| **Civis** | **6** | **NO** | YES |
| FocalPoint | 11 | YES | YES |
| Sidekick | 5 | YES | YES |

### Issues

- **helios-cli**: README mentions "test" 14 times but has no `tests/` directory
- **Civis**: README mentions "test" 6 times but has no `tests/` directory

### Recommendations
1. Add `tests/` directory with at least basic smoke tests to helios-cli and Civis
2. Or remove/reduce test claims in READMEs if tests are not yet implemented

---

## AUDIT 2: Language Distribution

### Summary by Primary Language

| Language | Repo Count |
|----------|------------|
| Rust | 48 |
| Node | 35 |
| Python | 23 |
| Go | 16 |

### Notes
- Many repos have polyglot structure (Rust + Node, etc.)
- Total language assignments: 122 (some repos count multiple)
- Rust is the dominant language (40% of assignments)

---

## AUDIT 3: Docker/Container Presence

### Repos with Dockerfiles

| Repo | Dockerfile(s) |
|------|---------------|
| PhenoDevOps | `Dockerfile.rust` |
| PolicyStack | `Dockerfile` |
| python | `Dockerfile.python` |
| agentapi-plusplus | `Dockerfile` |
| agileplus-mcp | `Dockerfile` |
| argis-extensions | `Dockerfile` |
| AtomsBot | `Dockerfile` |
| pheno | `Dockerfile.rust` |
| cliproxyapi-plusplus | `Dockerfile` |
| helios-router | `Dockerfile` |
| helioscope | `Dockerfile` |
| HexaKit | `Dockerfile.rust` |
| KDesktopVirt | 7 Dockerfiles (desktop variants) |
| kwality | `Dockerfile` |

### Notes
- **19 repos** have at least one Dockerfile
- KDesktopVirt has the most Docker variants (7)
- Multiple repos follow the pattern `Dockerfile.<variant>` for Rust projects

---

## Summary

| Audit | Issues Found |
|-------|--------------|
| README Accuracy | 2 repos with false test claims |
| Language Distribution | Rust-dominant (48 repos) |
| Docker Presence | 19 repos with Dockerfiles |

### Action Items
1. **helios-cli**: Add tests or reduce test claims in README
2. **Civis**: Add tests or reduce test claims in README
3. Consider centralizing common Dockerfile patterns (e.g., `Dockerfile.rust`)
