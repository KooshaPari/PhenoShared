# Changelog
All notable changes to this project will be documented in this file.

## 🐛 Bug Fixes
- Fix: restore and fix PhenoProc workspace crates

- Fixed phenotype-cipher: restored corrupted files, fixed imports
- Fixed pheno-proc-core: added [lib] section, fixed Clone trait
- Fixed pheno-proc-dedup: created lib.rs with deduplication filters
- Fixed pheno-proc-queue: added [lib] section
- Fixed pheno-proc-shm: created Cargo.toml and lib.rs
- Fixed pheno-proc-uds: created Cargo.toml and lib.rs
- Fixed facades: added [lib] section
- All workspace crates now compile successfully (`dcb1b26`)
## 📚 Documentation
- Docs(readme): expand README.md with purpose, stack, quick-start, related projects (`f85d98e`)
- Docs: add PLAN.md (`307cbeb`)
- Docs: add README.md (`cb8e205`)
- Docs: add SPEC.md (`4013b58`)
## ✨ Features
- Feat: mass extraction of all phenoSDK modules to PhenoProc

Extracted 17 AI infrastructure packages from phenoSDK/src/pheno/:
- pheno-analytics: 23 files, 5,302 LOC (Analytics, metrics)
- pheno-cicd: 11 files, 4,141 LOC (CI/CD automation)
- pheno-cli: 74 files, 11,631 LOC (CLI commands)
- pheno-clink: 23 files, 1,852 LOC (AI agents: Codex, Claude, Gemini)
- pheno-deployment: 66 files, 7,493 LOC (Deployment automation)
- pheno-infra: 211 files, 40,921 LOC (Infrastructure: control center, services, tunneling)
- pheno-kits: 131 files, 23,619 LOC (CLI builders, infra abstractions)
- pheno-llm: 19 files, 4,437 LOC (LLM routing, ensemble)
- pheno-mcp: 109 files, 17,143 LOC (MCP tools, adapters)
- pheno-observability: 30 files, 8,307 LOC (Observability, monitoring)
- pheno-optimization: 5 files, 2,028 LOC (Optimization)
- pheno-process: 16 files, 1,657 LOC (Process management)
- pheno-providers: 12 files, 1,218 LOC (Provider adapters)
- pheno-quality: 64 files, 10,311 LOC (Quality tools)
- pheno-testing: 251 files, 53,951 LOC (Testing framework with MCP QA)
- pheno-workflow: 51 files, 8,279 LOC (Workflow orchestration)

Total: ~202,000 LOC from phenoSDK
Each package includes pyproject.toml and README.md

Extraction date: 2026-04-04 (`49cc669`)
- Feat: add pheno-clink and pheno-llm from phenoSDK

Extracted Python AI modules:
- pheno-clink: AI agent integrations (Codex, Claude, Gemini) (~2,100 LOC)
- pheno-llm: LLM routing and ensemble strategies (~4,500 LOC)

Total: ~6,600 LOC from phenoSDK/src/pheno/ (`dbd7259`)
- Feat: add process management, deduplication, and queue crates

- pheno-proc-core: ProcessPool, ProcessInfo, ProcessFilter, SharedRuntime,
  ProjectLimits, ProjectResources
- pheno-proc-dedup: CommandLock, InMemoryLockAdapter, DedupFilter, BloomFilter
  (ported from thegent-sharecli Python)
- pheno-proc-queue: Priority, QueueItem, InMemoryQueueAdapter, QueueStats
  (ported from thegent-sharecli Python)

Consolidates sharecli/thegent-sharecli duplication into reusable crates. (`158f9b3`)
- Feat: add phenotype-* crates from workspace consolidation (`804abd9`)
## 🔨 Other
- Ci(wave-6): add quality-gate and fr-coverage workflows (`4426f60`)
- Chore(deps): align tokio + serde to org baseline (phenotype-versions.toml)

- tokio: unified to 1.39
- serde: unified to 1.0
- Verified: cargo check passed

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com> (`cbf130b`)
- Chore(ci): adopt phenotype-tooling workflows (wave-2) (`f94e62a`)
- Chore: add AgilePlus scaffolding (`d2fa389`)
- Chore: add phenotype-cli-core, config-ts, validation, governance to PhenoProc (`b2b7a0b`)
- Chore: add phenotype-colab-extensions, router-monitor, gauge, agent-core to PhenoProc (`113ef16`)
- Ci(legacy-enforcement): add legacy tooling anti-pattern gate (WARN mode)

Adds legacy-tooling-gate.yml monitoring per CLAUDE.md Technology Adoption Philosophy.

Refs: phenotype/repos/tooling/legacy-enforcement/ (`2338174`)
- Reorg: add phenotype-* crates and pheno-cli from HexaKit (`ae72962`)
- Chore: add worktree-manager and Evalora as submodules (`d041dc4`)
- Chore: keep nanovms as standalone repo (`d722363`)
- Chore: add nanovms, worktree-manager, Evalora to PhenoProc (`3a46de3`)
- Merge: add helmo, thegent-cli-share, forge, phenotype-colab-extensions (`da4cc09`)
- Merge: add additional crates (byteport, cursora, eventra, guardis, datamold, diffuse, holdr, mcp-forge, prismal, phenotype-patch, servion, portalis, guardrail) (`b080947`)
- Merge: add crypto, token, and CLI crates (`fddf0af`)
- Merge: add phenoGauge, phenoShared, phenoForge as crates (`65df757`)
- Merge: add phenotype-dep-guard crate (`897a795`)
- Merge: add phenotype-vessel crate from phenoVessel (`75030f6`)
- Initial: PhenoProc process orchestration registry (`4214bb3`)
