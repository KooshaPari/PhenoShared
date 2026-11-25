# Extended Workspace DAG v10
Generated: 2026-05-06 (extension of v7, 2026-05-05)

This v10 consolidates findings from the evening audit sprint (2026-05-05/06):
WS-Y Rust CI, WS-Z Go CI, WS-AA Node CI, WS-AB Dependabot/CODEOWNERS,
WS-AC Secrets/Pre-commit, WS-AD README/Docs, WS-AE Python Ecosystem, WS-AF GitHub Actions quality.

---

## Executive Summary

| Dimension | Finding | Severity |
|---|---|---:|
| CI Coverage | Almost all repos already have CI; only `rust/` bootstrap repo needed CI added | P0 — RESOLVED |
| GitHub Actions Quality | 7,013 workflows: 151 non-SHA-pinned (trufflehog@main in 128+), 91% missing timeout-minutes, 51% missing permissions | P0 |
| Dependabot | 10 repos missing Dependabot; 92 repos have it | P1 |
| CODEOWNERS | 30+ canonical repos missing .github/CODEOWNERS | P1 |
| Python Type Safety | 16/23 Python repos have zero type checking | P1 |
| Secrets | Clean — no hardcoded secrets in tracked source | P2 — CLEAR |
| Pre-commit | 20 repos missing .pre-commit-config.yaml | P2 |
| README Accuracy | helios-cli/phenoData/Civis false test claims (helios-cli is actually accurate — has inline #[cfg(test)]) | P2 |

---

## Completed Workstreams

| WS | Action | Repos | Status |
|---|---|---|---|
| WS-R | Add Go CI | BytePort | ✅ PR#213 (`ci/go-workflow`) |
| WS-T | Fix lock-copying | netweave-final2 | ✅ `0e378d8` |
| WS-U | Fix broken symlinks | 5 repos | ✅ 5 commits |
| WS-V | Add FUNDING.yml | 5 repos | ✅ 5 FUNDING.yml added |
| WS-W | Fix npm vulns | AtomsBot | ✅ `4d32914` — undici update |
| WS-X | Fix npm vulns | thegent | ✅ `9d08d44` |
| WS-Y | Add Rust CI | eyetracker, thegent-dispatch, phenotype-bus, FocalPoint, phenoUtils, Sidekick | ✅ pushed to branches; 3 already had CI |
| WS-Z | Add Go CI | kwality | ✅ `bc43ca0`; most repos already had CI |
| WS-AA | Add Node CI | Paginary, phenoData, PhenoHandbook, docs, phenodocs-scorecard-remediation | ✅ pushed; PhenoCompose archived |
| WS-S | Fix argis-extensions interface drift | argis-extensions | ⏸️ Paused — multi-module GraphQL schema sync needs architectural decision |

---

## New Workstreams (Priority Order)

### WS-AG: SHA-Pin trufflehog/actions/setup@main across 128+ repos (P0)

**Finding:** `trufflehog/actions/setup@main` is non-SHA-pinned in 128+ repos (trufflehog/agents/setup README + 127 callers). This is a supply-chain security risk — floating `@main` refs can be substituted.

**Fix:** Replace all instances of `trufflehog/actions/setup@main` with the pinned SHA. Get current SHA from `https://github.com/trufflehog/actions/releases`.

**Pattern:**
```yaml
# Before
- uses: trufflehog/actions/setup@main
# After (verify SHA at releases page)
- uses: trufflehog/actions/setup@sha256:XXXXXXXX...
```

**Affected repos** (sample): AgentMCP, Agentora, AuthKit, Civis, Conft, FocalPoint, Paginary, Parpoura, PhenoAgent, PhenoMCP, PhenoObservability, PhenoPlugins, PhenoVCS, PlatformKit, QuadSGM, Sidekick, Tracely, helios-cli, helios-router, helioscope, portage, thegent, Tracera, etc.

**Agent assignment:** Target ~20 repos per sub-agent, 6 sub-agents in parallel.

---

### WS-AH: Add timeout-minutes to org-level workflows (P0)

**Finding:** 91.3% of workflows (6,401 / 7,013) have no `timeout-minutes` on jobs. 37 root org-level workflows are all missing it. Hung jobs can consume CI minutes indefinitely.

**Fix:** Add `timeout-minutes: 30` (or appropriate) to all jobs in org-level workflows at `.github/workflows/*.yml` in the root AgilePlus repo.

**Risk:** Changing timeouts in 6,000+ files is high-churn. Limit to org-level workflows first.

---

### WS-AI: Add Dependabot to 10 repos (P1)

**Finding:** 10 repos have package managers but no Dependabot:
- `AgilePlus/` (cargo), `agileplus-agents/` (cargo), `agileplus-mcp/` (pip)
- `bdd-integration/` (cargo), `dispatch-mcp/` (pip), `docs/` (npm)
- `pheno-cli/` (go), `PhenoLang/` (go), `python/` (pip), `rust/` (cargo)

**Fix:** Add `.github/dependabot.yml` to each.

---

### WS-AJ: Add .github/CODEOWNERS to canonical repos (P1)

**Finding:** 30+ canonical repos (AgilePlus/, PhenoLang/, pheno-cli/, etc.) are missing .github/CODEOWNERS.

**Fix:** Add `.github/CODEOWNERS` with appropriate team ownership entries.

---

### WS-AK: Python type-checking gap — add mypy to 16 repos (P1)

**Finding:** 16 of 23 Python repos have zero type checking. Only agileplus-mcp, helios-router, helioscope, Parpoura, phenotype-omlx, QuadSGM, and thegent use mypy.

**Priority repos:** agent-user-status, AuthKit, McpKit, phenodocs, PhenoMCP, phenoResearchEngine, PhenoRuntime, PolicyStack (all have tests/ but no pytest and no mypy).

**Fix:** Add mypy + pre-commit hook to `pyproject.toml` and add `types` stubs to CI.

---

### WS-AL: Fix README accuracy — phenoData and Civis (P2)

**Finding:**
- **phenoData:** README claims tests but `tests/` doesn't exist (only has minisearch tests in `node_modules/`)
- **Civis:** README claims tests but `tests/` doesn't exist

**Note:** helios-cli's README is **accurate** — it has `#[cfg(test)]` inline modules, not a `tests/` directory.

**Fix:** Add `tests/` directories with basic smoke tests to phenoData and Civis, or remove test claims from READMEs.

---

## Existing Findings (Reference)

See `findings/` for full reports:
- `go_ecosystem_audit_2026-05-05.md` — 7 Go repos without CI (superseded — most had CI)
- `dependency_hygiene_audit_2026-05-05.md` — npm staleness, Actions SHA-pinning
- `repo_metadata_completeness_2026-05-05.md` — 37 repos need CI (superseded)
- `misc_audits_2026-05-05.md` — broken symlinks, duplicate Cargo names
- `byteport_todo_audit_2026-05-05.md` — live todo!() clusters
- `argis_extensions_interface_audit_2026-05-05.md` — multi-module GraphQL schema drift
- `rust_ecosystem_audit_2026-05-05.md` — all ignores well-reasoned
- `dependabot_codeowners_audit_2026-05-05.md` — Dependabot + CODEOWNERS coverage
- `secrets_precommit_audit_2026-05-05.md` — clean on secrets, pre-commit gap
- `readme_documentation_audit_2026-05-05.md` — language distribution, Dockerfiles
- `python_ecosystem_audit_2026-05-05.md` — 23 Python repos, 6 with mypy
- `github_actions_quality_audit_2026-05-05.md` — 7,013 workflows, 151 non-SHA-pinned

---

## Repo Language Distribution (2026-05-05)

| Language | Count |
|---|---|
| Rust | 48 |
| Node/TypeScript | 35 |
| Python | 23 |
| Go | 16 |

---

## CI Coverage Status (2026-05-06)

Only `rust/` bootstrap repo was genuinely missing CI. All other target repos already had CI workflows.

**Remaining CI-less repos:** NONE (after rust/ fix).

---

## Open Questions

1. **argis-extensions schema sync (WS-S):** The GraphQL schema (generated) and resolver signatures have drifted. Architectural decision needed — regenerate schema from source IDL, or manually align resolvers. Do NOT attempt blind fixes.

2. **WS-AH timeout-minutes:** 6,401 workflows without timeouts. Bulk change is high-risk. Should be scoped to org-level workflows only, or automated via tooling.

3. **PhenoCompose is archived:** CI for PhenoCompose cannot be pushed. Unarchive if active.

4. **helios-cli inline tests:** README is accurate — has `#[cfg(test)]` modules. WS-AL finding should note this correction.
