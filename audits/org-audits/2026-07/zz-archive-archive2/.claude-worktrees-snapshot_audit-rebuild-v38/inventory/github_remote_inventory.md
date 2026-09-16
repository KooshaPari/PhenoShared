# GitHub Remote Inventory — 2026-04-24

**Audit Date:** 2026-04-24  
**Scope:** <REDACTED> GitHub account  
**Local Repos:** 71 | **Remote Repos:** 142 | **Gap:** 71 remote-only candidates

---

## Executive Summary

- **71 local repos** in `/repos/` directory with git remotes
- **142 total repos** on GitHub/<REDACTED>
- **10 orphaned local repos** with NO_REMOTE configured
- **9 stale local checkouts** of archived projects
- **71 remote-only repos** on GitHub not present in `/repos/` (mostly archived or low-priority)

---

## Local Repo Status Table

| Local Repo | Remote URL | Status | Archived | Visibility |
|-----------|-----------|--------|----------|-----------|
| agent-user-status | https://github.com/<REDACTED>/agent-user-status | ✅ Synced | False | 🔒 Private |
| agentapi-plusplus | https://github.com/<REDACTED>/agentapi-plusplus | ✅ Synced | False | 🌐 Public |
| AgentMCP | https://github.com/<REDACTED>/AgentMCP.git | ⏳ Unverified | N/A | N/A |
| AgilePlus | https://github.com/<REDACTED>/AgilePlus | ✅ Synced | False | 🌐 Public |
| agslag-docs | https://github.com/<REDACTED>/agslag-docs | ❌ Archived | True | 🌐 Public |
| AppGen | https://github.com/<REDACTED>/AppGen | ❌ Archived | True | 🌐 Public |
| argis-extensions | https://github.com/<REDACTED>/argis-extensions | ✅ Synced | False | 🌐 Public |
| artifacts | git@github.com:<REDACTED>/PhenoKits.git | ⏳ Unverified | N/A | N/A |
| atoms.tech | https://github.com/<REDACTED>/atoms.tech | ❌ Archived | True | 🔒 Private |
| AtomsBot | https://github.com/<REDACTED>/AtomsBot | ❌ Archived | True | 🔒 Private |
| AuthKit | https://github.com/<REDACTED>/AuthKit | ✅ Synced | False | 🌐 Public |
| bare-cua | https://github.com/<REDACTED>/bare-cua.git | ⏳ Unverified | N/A | N/A |
| BytePort | https://github.com/<REDACTED>/BytePort | ✅ Synced | False | 🌐 Public |
| chatta | https://github.com/<REDACTED>/chatta | ❌ Archived | True | 🌐 Public |
| cheap-llm-mcp | (not on GitHub) | ⚠️ No Remote | N/A | N/A |
| Civis | https://github.com/<REDACTED>/Civis | ✅ Synced | False | 🔒 Private |
| cliproxyapi-plusplus | https://github.com/<REDACTED>/cliproxyapi-plusplus | ✅ Synced | False | 🌐 Public |
| cloud | git@github.com:<REDACTED>/cloud.git | ⏳ Unverified | N/A | N/A |
| Conft | https://github.com/<REDACTED>/Conft | ✅ Synced | False | 🌐 Public |
| DataKit | https://github.com/<REDACTED>/DataKit | ✅ Synced | False | 🌐 Public |
| Dino | https://github.com/<REDACTED>/Dino | ✅ Synced | False | 🌐 Public |
| Eidolon | (not on GitHub) | ⚠️ No Remote | N/A | N/A |
| FocalPoint | https://github.com/<REDACTED>/FocalPoint.git | ⏳ Unverified | N/A | N/A |
| heliosApp | https://github.com/<REDACTED>/heliosApp | ✅ Synced | False | 🌐 Public |
| HeliosLab | https://github.com/<REDACTED>/HeliosLab | ✅ Synced | False | 🌐 Public |
| hwLedger | https://github.com/<REDACTED>/hwLedger | ✅ Synced | False | 🌐 Public |
| KDesktopVirt | https://github.com/<REDACTED>/KDesktopVirt | ✅ Synced | False | 🔒 Private |
| KlipDot | https://github.com/<REDACTED>/KlipDot | ❌ Archived | True | 🌐 Public |
| kmobile | https://github.com/<REDACTED>/kmobile | ❌ Archived | True | 🌐 Public |
| kwality | https://github.com/<REDACTED>/kwality | ❌ Archived | True | 🌐 Public |
| localbase3 | https://github.com/<REDACTED>/localbase3 | ❌ Archived | True | 🌐 Public |
| McpKit | https://github.com/<REDACTED>/McpKit | ✅ Synced | False | 🌐 Public |
| netweave-final2 | https://github.com/<REDACTED>/netweave-final2.git | ⏳ Unverified | N/A | N/A |
| org-github | git@github.com:<REDACTED>/.github.git | ⏳ Unverified | N/A | N/A |
| Paginary | (not on GitHub) | ⚠️ No Remote | N/A | N/A |
| phench | git@github.com:<REDACTED>/PhenoKits.git | ⏳ Unverified | N/A | N/A |
| phenoDesign | https://github.com/<REDACTED>/phenoDesign | ✅ Synced | False | 🌐 Public |
| PhenoDevOps | https://github.com/<REDACTED>/PhenoDevOps | ✅ Synced | False | 🌐 Public |
| PhenoHandbook | https://github.com/<REDACTED>/PhenoHandbook | ✅ Synced | False | 🌐 Public |
| PhenoKits | https://github.com/<REDACTED>/PhenoKits | ✅ Synced | False | 🌐 Public |
| PhenoLibs | https://github.com/<REDACTED>/PhenoKit.git | ⏳ Unverified | N/A | N/A |
| PhenoMCP | https://github.com/<REDACTED>/PhenoMCP | ✅ Synced | False | 🌐 Public |
| PhenoObservability | https://github.com/<REDACTED>/PhenoObservability | ✅ Synced | False | 🌐 Public |
| PhenoPlugins | https://github.com/<REDACTED>/PhenoPlugins | ✅ Synced | False | 🌐 Public |
| PhenoProc | https://github.com/<REDACTED>/PhenoProc | ✅ Synced | False | 🌐 Public |
| phenoSDK | https://github.com/<REDACTED>/phenoSDK.git | ⏳ Unverified | N/A | N/A |
| PhenoSpecs | https://github.com/<REDACTED>/PhenoSpecs | ✅ Synced | False | 🌐 Public |
| phenotype-auth-ts | https://github.com/<REDACTED>/phenotype-auth-ts | ✅ Synced | False | 🌐 Public |
| phenotype-bus | (not on GitHub) | ⚠️ No Remote | N/A | N/A |
| phenotype-infra | https://github.com/<REDACTED>/phenotype-infra | ✅ Synced | False | 🌐 Public |
| phenotype-journeys | https://github.com/<REDACTED>/phenotype-journeys | ✅ Synced | False | 🔒 Private |
| phenotype-ops-mcp | https://github.com/<REDACTED>/phenotype-ops-mcp | ✅ Synced | False | 🌐 Public |
| phenotype-org-audits | (not on GitHub) | ⚠️ No Remote | N/A | N/A |
| phenotype-tooling | https://github.com/<REDACTED>/phenotype-tooling | ✅ Synced | False | 🌐 Public |
| PhenoVCS | https://github.com/<REDACTED>/PhenoVCS | ✅ Synced | False | 🌐 Public |
| phenoXdd | https://github.com/<REDACTED>/phenoXdd | ✅ Synced | False | 🌐 Public |
| PlayCua | https://github.com/<REDACTED>/PlayCua | ✅ Synced | False | 🌐 Public |
| PolicyStack | git@github.com:<REDACTED>/PolicyStack.git | ⏳ Unverified | N/A | N/A |
| portage | https://github.com/<REDACTED>/portage | ✅ Synced | False | 🌐 Public |
| QuadSGM | https://github.com/<REDACTED>/QuadSGM | ✅ Synced | False | 🔒 Private |
| ResilienceKit | https://github.com/<REDACTED>/ResilienceKit | ✅ Synced | False | 🌐 Public |
| rich-cli-kit | (not on GitHub) | ⚠️ No Remote | N/A | N/A |
| Sidekick | (not on GitHub) | ⚠️ No Remote | N/A | N/A |
| TestingKit | https://github.com/<REDACTED>/TestingKit | ✅ Synced | False | 🌐 Public |
| thegent | https://github.com/<REDACTED>/thegent | ✅ Synced | False | 🌐 Public |
| thegent-dispatch | (not on GitHub) | ⚠️ No Remote | N/A | N/A |
| thegent-workspace | (not on GitHub) | ⚠️ No Remote | N/A | N/A |
| Tokn | https://github.com/<REDACTED>/Tokn | ✅ Synced | False | 🌐 Public |
| Tracely | (not on GitHub) | ⚠️ No Remote | N/A | N/A |
| Tracera-recovered | https://github.com/<REDACTED>/Tracera.git | ⏳ Unverified | N/A | N/A |

---

## Orphaned Local Repos (NO_REMOTE) — Action Required

These repos exist locally but have no GitHub remote configured:

1. **cheap-llm-mcp** — Initialize: `git remote add origin https://github.com/<REDACTED>/cheap-llm-mcp.git`
2. **Eidolon** — Initialize: `git remote add origin https://github.com/<REDACTED>/Eidolon.git`
3. **Paginary** — Initialize: `git remote add origin https://github.com/<REDACTED>/Paginary.git`
4. **phenotype-bus** — Initialize: `git remote add origin https://github.com/<REDACTED>/phenotype-bus.git`
5. **phenotype-org-audits** — Initialize: `git remote add origin https://github.com/<REDACTED>/phenotype-org-audits.git`
6. **rich-cli-kit** — Initialize: `git remote add origin https://github.com/<REDACTED>/rich-cli-kit.git`
7. **Sidekick** — Initialize: `git remote add origin https://github.com/<REDACTED>/Sidekick.git`
8. **thegent-dispatch** — Initialize: `git remote add origin https://github.com/<REDACTED>/thegent-dispatch.git`
9. **thegent-workspace** — Initialize: `git remote add origin https://github.com/<REDACTED>/thegent-workspace.git`
10. **Tracely** — Initialize: `git remote add origin https://github.com/<REDACTED>/Tracely.git`

---

## Archived Local Checkouts (Stale) — Cleanup Candidates

These exist locally but are archived on GitHub (no further development):

1. agslag-docs
2. AppGen
3. atoms.tech
4. AtomsBot
5. chatta
6. KlipDot
7. kmobile
8. kwality
9. localbase3

**Recommendation:** Remove from `/repos/` (e.g., `rm -rf <dir>`) after verifying no local work exists.

---

## Unverified Remote URLs (git@/custom)

Remotes using SSH or non-standard URLs (need manual verification):

1. **AgentMCP** — `https://github.com/<REDACTED>/AgentMCP.git` (SSH format)
2. **artifacts** — `git@github.com:<REDACTED>/PhenoKits.git` (mismatched remote)
3. **bare-cua** — `https://github.com/<REDACTED>/bare-cua.git` (SSH format)
4. **cloud** — `git@github.com:<REDACTED>/cloud.git` (SSH format)
5. **FocalPoint** — `https://github.com/<REDACTED>/FocalPoint.git` (SSH format)
6. **netweave-final2** — `https://github.com/<REDACTED>/netweave-final2.git` (SSH format)
7. **org-github** — `git@github.com:<REDACTED>/.github.git` (.github repo)
8. **phench** — `git@github.com:<REDACTED>/PhenoKits.git` (mismatched remote)
9. **PhenoLibs** — `https://github.com/<REDACTED>/PhenoKit.git` (name mismatch: PhenoKit vs PhenoLibs)
10. **phenoSDK** — `https://github.com/<REDACTED>/phenoSDK.git` (SSH format)
11. **PolicyStack** — `git@github.com:<REDACTED>/PolicyStack.git` (SSH format)
12. **Tracera-recovered** — `https://github.com/<REDACTED>/Tracera.git` (name mismatch: Tracera-recovered vs Tracera)

---

## Remote-Only Repos (On GitHub, Not in /repos/)

**71 remote repos** exist on GitHub but are not cloned locally. Breakdown:

### Active Remote-Only (High-Value Candidates for Integration)
- **DevHex** — Public, active
- **Benchora** — Public, active
- **helios-cli** — Public, active (similar to heliosApp)
- **heliosCLI** — Public, active (similar to helios-cli)
- **GDK** — Public, active
- **phenoAI** — Public, active
- **PhenoRuntime** — Public, active
- **HexaKit** — Public, active
- **pheno** — Public, active
- **phenoShared** — Public, active
- **phenodocs** — Public, active
- **Metron** — Public, active
- **agent-devops-setups** — Public, active
- **phenotype-hub** — Public, active
- **vibeproxy-monitoring-unified** — Public, active
- **Tasken** — Public, active
- **Stashly** — Public, active
- **Httpora** — Public, active
- **phenoUtils** — Public, active
- **PhenoLang** — Public, active
- **PhenoCompose** — Public, active
- **phenoData** — Public, active
- **vibeproxy** — Public, active
- **Apisync** — Public, active
- **nanovms** — Public, active
- **phenotype-omlx** — Public, active
- **PhenoProject** — Public, active
- **ObservabilityKit** — Public, active
- **phenotype-registry** — Public, active
- **Planify** — Public, active
- **MCPForge** — Public, active
- **DINOForge-UnityDoorstop** — Public, active
- **dinoforge-packs** — Public, active
- **heliosBench** — Public, active

### Private Remote-Only
- **Configra** — Private
- **Parpoura** — Private
- **foqos-private** — Private
- **helios-router** — Private
- **phenoResearchEngine** — Private
- **phenotype-colab-extensions** — Archived, private
- **Prismal** — Archived, private
- **forge** — Archived, private
- **Diffuse** — Archived, private
- **Cryptora** — Archived, private
- **Servion** — Archived, private
- **Guardrail** — Archived, private
- **helios-cli-backup** — Archived, private
- **router-docs** — Archived, private
- **model-conductor-hub** — Archived, private
- **canvasApp** — Archived, private
- **go-nippon** — Archived, private

### Archived Remote-Only (Low Priority)
- KodeVibeGo
- phenoForge
- Quillr
- Zerokit
- Settly
- Authvault
- phenotype-dep-guard
- phenoRouterMonitor
- worktree-manager
- phenoXddLib
- Synthia
- KaskMan
- ccusage
- vibe-kanban
- KWatch
- slickport
- Logify
- Eventra
- KommandLineAutomation
- KodeVibe
- Frostify
- odin-dash
- odin-TTT
- odin-library
- odin-recipes
- odin-weather
- odin-todo
- odin-restaurant
- odin-Signup
- odin-calc
- odin-etchasketch
- odin-res
- odin-landing
- Project-Spyn
- agentapi
- tehgent
- argisexec
- acp
- PriceyApp
- pheno-sdk
- RIP-Fitness-App

---

## Recommendations

1. **Immediate:** Add remotes to 10 orphaned local repos (NO_REMOTE)
2. **Short-term:** Remove 9 archived local checkouts to reclaim disk space
3. **Medium-term:** Clone high-value active remote-only repos (DevHex, Benchora, helios-cli, GDK, phenodocs, Metron)
4. **Long-term:** Archive or consolidate low-value repos (30+ odin-* and other learning projects)

---

## Audit Metadata

- **Generated:** 2026-04-24
- **Tool:** `gh cli` + local git introspection
- **Command:** `gh repo list <REDACTED> --limit 200 --json name,url,isPrivate,isArchived`
- **Local Scan:** `find . -maxdepth 2 -type d -name .git`
