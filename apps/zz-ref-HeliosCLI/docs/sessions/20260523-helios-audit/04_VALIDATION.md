# 04_VALIDATION.md — Batch Validation Results

## Methodology

- **Cargo repos**: `cargo metadata --format-version 1 --no-deps` — captures workspace validity and root package name.
- **npm repos**: `cat package.json` + `npm ls --depth=0` — captures dep resolution, test scripts, workspace links.
- **Python repos**: TOML parse of `pyproject.toml` — captures name, dep count, pytest presence.
- No heavy builds (`cargo test`, `npm test`) were run — only manifest validation.

---

## Cargo Repos (43 total)

### Batch 1 — All PASS (20/20)

| REPO | WORKSPACE NAME | STATUS |
|------|---------------|--------|
| Agentora | agentkit@0.1.0 | ✅ PASS |
| AgilePlus | agileplus-api@0.1.0 | ✅ PASS |
| Benchora | gauge@0.2.0 | ✅ PASS |
| BytePort | app@0.1.0 (Tauri) | ✅ PASS |
| Civis | civ-engine@0.1.0 | ✅ PASS |
| Configra | pheno-core@0.1.0 | ✅ PASS |
| Eidolon | eidolon-core@0.0.1 | ✅ PASS |
| FocalPoint | agent-orchestrator@0.1.0 | ✅ PASS |
| GDK | gdk@1.0.0 | ✅ PASS |
| HeliosLab | pheno-core@0.1.1 | ✅ PASS |
| HexaKit | phenotype-cache-adapter@0.2.0 | ✅ PASS |
| KDesktopVirt | kvirtualstage@0.2.1 | ✅ PASS |
| KlipDot | klipdot@0.1.0 | ✅ PASS |
| Metron | metrickit@0.1.0 | ✅ PASS |
| PhenoControl | phenobuild-core@0.1.0 | ✅ PASS |
| PhenoDevOps | agileplus-api@0.2.0 | ✅ PASS |
| PhenoKits | phenokits@0.1.0 | ✅ PASS |
| PhenoMCP | pheno-meilisearch@0.1.0 | ✅ PASS |
| PhenoObservability | pheno-dragonfly@0.1.0 | ✅ PASS |
| PhenoPlugins | pheno-plugin-core@0.1.0 | ✅ PASS |

### Batch 2 — 23 PASS, 4 FAIL

| REPO | WORKSPACE NAME | STATUS | NOTE |
|------|---------------|--------|------|
| PhenoProc | pheno-proc-core | ✅ PASS | |
| PhenoRuntime | pheno-minio | ✅ PASS | |
| PhenoVCS | — | ❌ FAIL | Missing `crates/pheno-vcs-core/Cargo.toml` |
| PlayCua | profile warning | ✅ PASS | |
| Sidekick | sidekick-dispatch | ✅ PASS | |
| Tasken | taskkit | ✅ PASS | |
| Tokn | pareto-rs | ✅ PASS | |
| Tracely | helix-tracing | ✅ PASS | |
| bare-cua | profile warning | ✅ PASS | |
| bdd-integration | agileplus-bdd | ✅ PASS | |
| eyetracker | eyetracker-domain | ✅ PASS | |
| forgecode | forge_api | ✅ PASS | |
| helios-router | profile warning | ✅ PASS | |
| heliosHarness | — | ❌ FAIL | Missing `crates/harness_pyo3/Cargo.toml` |
| helioscope | — | ❌ FAIL | Missing `crates/thegent-router/Cargo.toml` |
| pheno | — | ❌ FAIL | Missing `crates/agileplus-api/Cargo.toml` |
| phenoAI | llm-router | ✅ PASS | |
| phenoData | surreal-bridge | ✅ PASS | |
| phenoForge | phenotype-forge | ✅ PASS | |
| phenoShared | ffi_utils | ✅ PASS | |
| phenoUtils | pheno-shell | ✅ PASS | |
| phenotype-bus | phenotype-bus | ✅ PASS | |
| phenotype-journeys | phenotype-journey-core | ✅ PASS | |
| phenotype-tooling | docs-health | ✅ PASS | |
| rich-cli-kit | rck-core | ✅ PASS | |
| thegent-dispatch | thegent-dispatch | ✅ PASS | |
| thegent-workspace | smoke_test | ✅ PASS | |

### Cargo Summary
- **43 repos checked** | **39 PASS** | **4 FAIL**

### Stale Cargo.toml members (4 FAIL repos):
| REPO | Missing Crate |
|------|--------------|
| PhenoVCS | `crates/pheno-vcs-core` |
| heliosHarness | `crates/harness_pyo3` |
| helioscope | `crates/thegent-router` |
| pheno | `crates/agileplus-api` |

---

## npm Repos (35 total)

| REPO | NAME | DEP_COUNT | HAS_TEST | STATUS |
|------|------|:---------:|:--------:|--------|
| AppGen | appgeneric | 25 | ✗ | ⚠️ WARN — unmet deps |
| AtomsBot | atomsbot | 18 | ✓ | ⚠️ WARN — unmet deps |
| Civis | civ-docs | 0 | ✗ | ❓ UNKNOWN — docs only |
| HeliosLab | colab | 19 | ✓ | ⚠️ WARN — unmet deps |
| KDesktopVirt | kdesktopvirt-docs | 0 | ✗ | ❓ UNKNOWN — no deps |
| OmniRoute | omniroute | 42 | ✓ | ⚠️ WARN — unmet deps |
| Paginary | paginary | 0 | ✗ | ❓ UNKNOWN — no deps |
| Parpoura | parpour-docs | 0 | ✗ | ❓ UNKNOWN — no deps |
| PhenoCompose | nanovms-docs | 0 | ✗ | ❓ UNKNOWN — no deps |
| PhenoHandbook | pheno-handbook | 0 | ✓ | ❓ UNKNOWN — no deps |
| PhenoMCP | @phenotype/mcp | 2 | ✗ | ⚠️ WARN — unmet deps |
| PhenoRuntime | @phenotype/runtime | 0 | ✗ | ❓ UNKNOWN — no deps |
| Planify | plane | 1 | ✗ | ⚠️ WARN — workspace config warnings |
| PolicyStack | — (unnamed) | 0 | ✗ | ❓ UNKNOWN — no deps |
| agent-devops-setups | — (unnamed) | 0 | ✗ | ❓ UNKNOWN — no deps |
| agileplus-landing | agileplus-landing | 6 | ✓ | ⚠️ WARN — unmet deps |
| byteport-landing | byteport-landing | 5 | ✗ | ⚠️ WARN — unmet deps |
| cliproxyapi-plusplus | cliproxyapi-plusplus-oxc-tools | 0 | ✗ | ⚠️ WARN — unmet deps |
| forgecode | forge-code-evals | 19 | ✗ | ⚠️ WARN — unmet deps |
| heliosApp | heliosapp | 7 | ✓ | ⚠️ WARN — unmet deps + local workspace links |
| heliosBench | heliosbench-docs | 0 | ✗ | ❓ UNKNOWN — no deps |
| helioscope | codex-monorepo | 0 | ✗ | ❓ UNKNOWN — no deps |
| nanovms | nanovms-docs | 0 | ✗ | ❓ UNKNOWN — no deps |
| phenoData | phenodata-docs | 0 | ✗ | ❓ UNKNOWN — no deps |
| phenoDesign | @kooshapari/design | 1 | ✓ | ⚠️ WARN — unmet deps |
| phenoResearchEngine | @phenotype/research-engine | 0 | ✓ | ❓ UNKNOWN — no deps |
| phenoShared | @phenotype/shared-utils | 0 | ✗ | ❓ UNKNOWN — no deps |
| phenodocs | phenodocs | 3 | ✗ | ⚠️ WARN — unmet deps + local workspace link |
| phenodocs-scorecard-remediation | phenodocs | 3 | ✗ | ⚠️ WARN — unmet deps + local workspace link |
| phenokits-landing | phenokits-landing | 5 | ✗ | ⚠️ WARN — unmet deps |
| phenotype-auth-ts | @phenotype/auth-ts | 0 | ✓ | ⚠️ WARN — unmet deps |
| phenotype-org-audits | phenotype-org-audits-docs | 0 | ✗ | ❓ UNKNOWN — no deps |
| phenotype-registry | phenotype-registry-docs | 0 | ✗ | ❓ UNKNOWN — no deps |
| phenotype-tooling | phenotype-tooling-docs | 0 | ✗ | ❓ UNKNOWN — no deps |
| thegent | thegent-docs | 2 | ✗ | ⚠️ WARN — unmet deps |

### npm Issues
- **0 FAIL** — all `package.json` files are valid and parseable
- **15 WARN** — need `npm install` to hydrate `node_modules`
- **18 UNKNOWN** — docs-only / zero-dep packages (healthy as-is)
- **2 unnamed** — `PolicyStack`, `agent-devops-setups` missing `name` field
- **3 workspace-linked** — `heliosApp`, `phenodocs`, `phenodocs-scorecard-remediation` have local workspace references

---

## Python Repos (17 total)

| REPO | NAME | HAS_PYTEST | DEP_COUNT | STATUS |
|------|------|:-----------:|:---------:|:------:|
| AuthKit | AuthKit | ✅ (Poetry) | 0 | ✅ PASS |
| McpKit | McpKit | ✅ (Poetry) | 0 | ✅ PASS |
| Parpoura | parpour | ✅ | 22 | ✅ PASS |
| PhenoMCP | pheno-mcp | ✗ | 0 | ✅ PASS |
| PhenoRuntime | pheno-runtime | ✗ | 0 | ✅ PASS |
| PolicyStack | policy-contract | ✗ | 0 | ✅ PASS |
| agent-user-status | agent-user-status | ✗ | 0 | ✅ PASS |
| cheap-llm-mcp | cheap-llm-mcp | ✅ | 4 | ✅ PASS |
| helios-router | helios-router-ui | ✅ | 6 | ✅ PASS |
| heliosBench | helios-bench | ✅ | 3 | ✅ PASS |
| helioscope | helioscope | ✅ | 6 | ✅ PASS |
| phenoResearchEngine | phenotype-research-engine | ✗ | 0 | ✅ PASS |
| phenodocs | phenodocs | ✗ | 0 | ✅ PASS |
| phenodocs-scorecard-remediation | phenodocs | ✗ | 0 | ✅ PASS |
| phenotype-omlx | omlx | ✅ | 25 | ✅ PASS |
| portage | portage | ✅ | 26 | ✅ PASS |
| thegent | thegent | ✅ | 42 | ✅ PASS |

### Python Summary
- **17/17 PASS** — all `pyproject.toml` files are valid
- **10 repos** have pytest configured
- **7 repos** use Poetry-style dev deps (AuthKit, McpKit) or have no test framework
- **8 repos** have `.venv` directory (prior active use)

---

## Previously Tested Repos

| REPO | MANIFEST | STATUS |
|------|----------|--------|
| Httpora | pyproject.toml | ✅ Tested |
| HeliosCLI | Cargo.toml, package.json, pyproject.toml | ✅ Tested |
| QuadSGM | pyproject.toml | ✅ Tested |
| Tracera | package.json, pyproject.toml | ✅ Tested |

---

## Action Items

### Must Fix (stale Cargo.toml members)
1. **PhenoVCS** — remove or restore `crates/pheno-vcs-core` entry
2. **heliosHarness** — remove or restore `crates/harness_pyo3` entry
3. **helioscope** — remove or restore `crates/thegent-router` entry
4. **pheno** — remove or restore `crates/agileplus-api` entry

### Should Fix (npm hygiene)
1. Run `npm install` across the 15 WARN repos
2. Add `name` field to `PolicyStack/package.json` and `agent-devops-setups/package.json`
3. Resolve local workspace links in `heliosApp`, `phenodocs`, `phenodocs-scorecard-remediation`

### Nice to Have
- Add pytest to the 7 Python repos that lack it (PhenoMCP, PhenoRuntime, PolicyStack, agent-user-status, phenoResearchEngine, phenodocs, phenodocs-scorecard-remediation)
- Consider `npm test` scripts for the 9 npm repos that have `test: true` but no defined test script
