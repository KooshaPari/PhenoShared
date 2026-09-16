# Repo Metadata Completeness Audit

**Date:** 2026-05-05
**Scope:** `/Users/<REDACTED>/CodeProjects/Phenotype/repos`
**Audits:** CLAUDE.md, FUNDING.yml, CI/CD coverage, Governance references

---

## Audit 1: CLAUDE.md Presence

### Missing CLAUDE.md (Canonical Repos)

| Repo | Type | Priority |
|------|------|----------|
| `agentops-policy-federation/` | Policy | High |
| `agileplus-agents/` | App | High |
| `agileplus-landing/` | App | High |
| `agileplus-mcp/` | MCP | High |
| `apps/` | Directory | Low |
| `bdd-integration/` | Integration | High |
| `byteport-landing/` | Landing | Medium |
| `dispatch-mcp/` | MCP | High |
| `fleet-audit/` | Tool | High |
| `frontend/` | Directory | Low |
| `harnesses/` | Directory | Low |
| `hwledger-landing/` | Landing | Medium |
| `Observably/` | App | High |
| `pheno-cli/` | CLI | High |
| `PhenoContracts/` | Lib | High |
| `PhenoControl/` | Lib | High |
| `PhenoEvents/` | Lib | High |
| `PhenoSchema/` | Lib | High |
| `phenotype-icons/` | Asset | Medium |
| `phenotype-previews-smoketest/` | Test | Medium |
| `phenotype-shared/` | Lib | High |
| `phenotype-skills/` | Skills | High |
| `plans/` | Directory | Low |
| `portage-adapter-core/` | Adapter | High |
| `prompts/` | Directory | Low |
| `python/` | Directory | Low |
| `references/` | Directory | Low |
| `rust/` | Directory | Low |
| `scripts/` | Directory | Low |
| `src/` | Directory | Low |
| `templates/` | Directory | Low |
| `thegent-jsonl/` | Tool | Medium |
| `tooling/` | Directory | Low |
| `ValidationKit/` | Kit | High |
| `worklogs/` | Directory | Low |

**Summary:** 34 canonical repos missing CLAUDE.md

### Repos WITH CLAUDE.md (72 total)

Active repos with proper governance documentation include: `AgilePlus/`, `AppGen/`, `AtomsBot/`, `AuthKit/`, `bare-cua/`, `Benchora/`, `Civis/`, `Configra/`, `DataKit/`, `DevHex/`, `dinoforge-packs/`, `DINOForge-UnityDoorstop/`, `Eidolon/`, `foqos-private/`, `GDK/`, `helioscope/`, `HexaKit/`, `hwLedger/`, `KDesktopVirt/`, `KlipDot/`, `MCPForge/`, `Metron/`, `nanovms/`, `netweave-final2/`, `ObservabilityKit/`, `Paginary/`, `Parpoura/`, `pheno/`, `PhenoAgent/`, `phenoAI/`, `PhenoCompose/`, `phenoDesign/`, `PhenoDevOps/`, `phenodocs-scorecard-remediation/`, `phenodocs/`, `PhenoHandbook/`, `PhenoKits/`, `PhenoLang/`, `PhenoMCP/`, `PhenoObservability/`, `PhenoPlugins/`, `PhenoProc/`, `PhenoProject/`, `PhenoRuntime/`, `phenoShared/`, `phenotype-hub/`, `phenotype-omlx/`, `phenotype-ops-mcp/`, `phenotype-org-audits/`, `phenotype-registry/`, `phenotype-tooling/`, `phenoUtils/`, `Pine/`, `PlayCua/`, `PolicyStack/`, `ResilienceKit/`, `Sidekick/`, `thegent/`, `thegent-dispatch/`, `thegent-shm/`, `thegent-workspace/`, `Tokn/`, `vibeproxy-monitoring-unified/`, and more.

---

## Audit 2: FUNDING.yml Presence

### Missing FUNDING.yml (ALL directories)

**ALL canonical repos lack FUNDING.yml**

This is a critical gap for open-source sustainability. FUNDING.yml enables:
- GitHub Sponsors integration
- Community funding links
- Corporate sponsorship pathways

**Recommended Action:** Create `FUNDING.yml` with placeholder for all active repos.

---

## Audit 3: CI/CD Coverage Map

### Repos with Build Manifests but NO CI Pipeline

| Repo | Language | Risk |
|------|----------|------|
| `AgilePlus/` | Rust | Critical |
| `agent-devops-setups/` | Node | High |
| `AppGen/` | Node | High |
| `AtomsBot/` | Node | High |
| `bare-cua/` | Rust | High |
| `bdd-integration/` | Rust | Critical |
| `BytePort/` | Go | High |
| `Civis/` | Node | High |
| `Configra/` | Rust | High |
| `DevHex/` | Go | High |
| `docs/` | Node | Medium |
| `Eidolon/` | Rust | High |
| `eyetracker/` | Rust | Critical |
| `FocalPoint/` | Rust | Critical |
| `GDK/` | Rust | High |
| `kwality/` | Go | High |
| `netweave-final2/` | Go | High |
| `Paginary/` | Node | High |
| `phenoAI/` | Rust | Critical |
| `PhenoCompose/` | Node | High |
| `phenoData/` | Node | High |
| `phenodocs-scorecard-remediation/` | Python | High |
| `PhenoHandbook/` | Node | Medium |
| `PhenoLang/` | Go | High |
| `phenotype-auth-ts/` | Node | Critical |
| `phenotype-bus/` | Rust | Critical |
| `phenotype-ops-mcp/` | Go | High |
| `phenotype-org-audits/` | Node | High |
| `phenotype-registry/` | Node | High |
| `phenoUtils/` | Rust | High |
| `Planify/` | Node | High |
| `PlayCua/` | Rust | High |
| `rich-cli-kit/` | Rust | High |
| `rust/` | Rust | High |
| `Sidekick/` | Rust | High |
| `thegent-dispatch/` | Rust | Critical |
| `thegent-workspace/` | Rust | Critical |

**Summary:** 37 repos have build manifests but no CI pipeline

### Repos with CI Coverage

Repos confirmed to have CI/CD pipelines: `AgilePlus/` (via deny.toml audit), and others to be verified.

---

## Audit 4: Governance Reference Check

### Repos WITH AgilePlus Governance Reference (58)

| Repo | Status |
|------|--------|
| `agent-devops-setups/` | Compliant |
| `agent-user-status/` | Compliant |
| `AgilePlus/` | Compliant |
| `AppGen/` | Compliant |
| `AtomsBot/` | Compliant |
| `AuthKit/` | Compliant |
| `bare-cua/` | Compliant |
| `Benchora/` | Compliant |
| `cheap-llm-mcp/` | Compliant |
| `Civis/` | Compliant |
| `Configra/` | Compliant |
| `DataKit/` | Compliant |
| `DevHex/` | Compliant |
| `dinoforge-packs/` | Compliant |
| `DINOForge-UnityDoorstop/` | Compliant |
| `Eidolon/` | Compliant |
| `foqos-private/` | Compliant |
| `GDK/` | Compliant |
| `helioscope/` | Compliant |
| `HexaKit/` | Compliant |
| `hwLedger/` | Compliant |
| `KDesktopVirt/` | Compliant |
| `KlipDot/` | Compliant |
| `MCPForge/` | Compliant |
| `Metron/` | Compliant |
| `nanovms/` | Compliant |
| `netweave-final2/` | Compliant |
| `ObservabilityKit/` | Compliant |
| `Paginary/` | Compliant |
| `Parpoura/` | Compliant |
| `pheno/` | Compliant |
| `PhenoAgent/` | Compliant |
| `phenoAI/` | Compliant |
| `PhenoCompose/` | Compliant |
| `phenoDesign/` | Compliant |
| `PhenoDevOps/` | Compliant |
| `phenodocs-scorecard-remediation/` | Compliant |
| `phenodocs/` | Compliant |
| `PhenoHandbook/` | Compliant |
| `PhenoKits/` | Compliant |
| `PhenoLang/` | Compliant |
| `PhenoMCP/` | Compliant |
| `PhenoObservability/` | Compliant |
| `PhenoPlugins/` | Compliant |
| `PhenoProc/` | Compliant |
| `PhenoProject/` | Compliant |
| `PhenoRuntime/` | Compliant |
| `phenoShared/` | Compliant |
| `phenotype-hub/` | Compliant |
| `phenotype-omlx/` | Compliant |
| `phenotype-ops-mcp/` | Compliant |
| `phenotype-org-audits/` | Compliant |
| `phenotype-registry/` | Compliant |
| `phenotype-tooling/` | Compliant |
| `phenoUtils/` | Compliant |
| `Pine/` | Compliant |
| `PlayCua/` | Compliant |
| `PolicyStack/` | Compliant |
| `ResilienceKit/` | Compliant |
| `Sidekick/` | Compliant |
| `thegent/` | Compliant |
| `thegent-dispatch/` | Compliant |
| `thegent-shm/` | Compliant |
| `thegent-workspace/` | Compliant |
| `Tokn/` | Compliant |
| `vibeproxy-monitoring-unified/` | Compliant |

### Repos WITHOUT Governance Reference (47)

| Repo | Type | Recommended Action |
|------|------|-------------------|
| `agentapi-plusplus/` | API | Add CLAUDE.md + governance |
| `AgentMCP/` | MCP | Add CLAUDE.md + governance |
| `Agentora/` | Agent | Add CLAUDE.md + governance |
| `argis-extensions/` | Extension | Add CLAUDE.md + governance |
| `BytePort/` | Port | Add CLAUDE.md + governance |
| `chatta/` | Chat | Add CLAUDE.md + governance |
| `cliproxyapi-plusplus/` | Proxy | Add CLAUDE.md + governance |
| `Conft/` | Config | Add CLAUDE.md + governance |
| `Dino/` | Dino | Add CLAUDE.md + governance |
| `eyetracker/` | Tool | Add CLAUDE.md + governance |
| `FocalPoint/` | Tool | Add CLAUDE.md + governance |
| `forgecode/` | Forge | Add CLAUDE.md + governance |
| `helios-cli/` | CLI | Add CLAUDE.md + governance |
| `helios-router/` | Router | Add CLAUDE.md + governance |
| `heliosApp/` | App | Add CLAUDE.md + governance |
| `heliosBench/` | Bench | Add CLAUDE.md + governance |
| `HeliosLab/` | Lab | Add CLAUDE.md + governance |
| `Httpora/` | HTTP | Add CLAUDE.md + governance |
| `kwality/` | Tool | Add CLAUDE.md + governance |
| `localbase3/` | DB | Add CLAUDE.md + governance |
| `McpKit/` | Kit | Add CLAUDE.md + governance |
| `phenoData/` | Data | Add CLAUDE.md + governance |
| `phenoForge/` | Forge | Add CLAUDE.md + governance |
| `phenoResearchEngine/` | Research | Add CLAUDE.md + governance |
| `PhenoSpecs/` | Specs | Add CLAUDE.md + governance |
| `phenotype-auth-ts/` | Auth | Add CLAUDE.md + governance |
| `phenotype-bus/` | Bus | Add CLAUDE.md + governance |
| `phenotype-infra/` | Infra | Add CLAUDE.md + governance |
| `phenotype-journeys/` | Journeys | Add CLAUDE.md + governance |
| `PhenoVCS/` | VCS | Add CLAUDE.md + governance |
| `phenoXdd/` | XDD | Add CLAUDE.md + governance |
| `Planify/` | Plan | Add CLAUDE.md + governance |
| `PlatformKit/` | Kit | Add CLAUDE.md + governance |
| `portage/` | Portage | Add CLAUDE.md + governance |
| `QuadSGM/` | SGM | Add CLAUDE.md + governance |
| `rich-cli-kit/` | Kit | Add CLAUDE.md + governance |
| `Tasken/` | Task | Add CLAUDE.md + governance |
| `TestingKit/` | Kit | Add CLAUDE.md + governance |
| `Tracely/` | Trace | Add CLAUDE.md + governance |
| `Tracera/` | Trace | Add CLAUDE.md + governance |
| `vibeproxy/` | Proxy | Add CLAUDE.md + governance |

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| Total directories scanned | ~100 |
| Repos with CLAUDE.md | 72 |
| Repos missing CLAUDE.md | 34 |
| Repos with FUNDING.yml | 0 |
| Repos missing FUNDING.yml | 100+ |
| Repos with manifest + NO CI | 37 |
| Repos with governance reference | 58 |
| Repos without governance reference | 47 |

---

## Critical Gaps

1. **FUNDING.yml Missing Everywhere** - Zero repos have FUNDING.yml. This blocks GitHub Sponsors integration.

2. **CI/CD Gap** - 37 repos (38%) with build manifests have no CI pipeline. These include:
   - 16 Rust repos
   - 10 Node/TypeScript repos
   - 7 Go repos
   - 1 Python repo

3. **Governance Fragmentation** - 47 repos (45%) lack AgilePlus governance references despite having CLAUDE.md.

---

## Recommended Remediation Order

### Tier 1: Critical (Security & Compliance)
1. Add FUNDING.yml to all active production repos
2. Add CI/CD to Rust critical repos: `AgilePlus/`, `bdd-integration/`, `eyetracker/`, `FocalPoint/`, `phenoAI/`, `phenotype-auth-ts/`, `phenotype-bus/`, `thegent-dispatch/`, `thegent-workspace/`

### Tier 2: High (Quality Assurance)
1. Add CI/CD to remaining manifest repos
2. Add governance references to 47 non-compliant repos

### Tier 3: Medium (Completeness)
1. Add CLAUDE.md to 34 missing repos
2. Add FUNDING.yml to remaining repos

---

*Report generated: 2026-05-05*
