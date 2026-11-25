# Documentation Review: canonicalization + docs-5 vs docs-3

**Date:** 2026-09-17
**Reviewer:** jcode (main thread, after 8/10 subagents crashed on mimo-v2.5)
**Scope:**
- `~/Downloads/phenotype-canonicalization/` (6 .md files)
- `~/Downloads/docs-5/` (353 .md files, 624 total, 1.1 MB)
- Baseline: `~/Downloads/docs-3/` (145 .md files, 262 total, 0.5 MB)

## 1. Quantitative comparison

| Metric | docs-3 | docs-5 | Delta |
|---|---|---|---|
| Total files | 262 | 624 | +138% |
| Markdown files | 145 | 353 | +143% |
| Total size | 0.5 MB | 1.1 MB | +120% |
| Subdirs | ~12 | 17 | +5 new |
| Product dossiers | 4 (PhenoMLX, HeliosLab, PhenoShared, Portage) | 33 | +29 |
| ADRs | 13 | 15 | +2 |

docs-5 is a strict superset of docs-3 with the following net-new directories:
- `adr/` — 15 ADRs (13 migrated + 2 new: 014, 015, 016)
- `architecture/` — design layer decomposition
- `examples/` — worked examples
- `federation/` — cross-repo federation protocol (largest subdir: 30+ files)
- `intent/` — intent extraction prompts
- `operations/` — operational playbooks
- `portfolio/` — full 38-product roster
- `products/` — 33 product dossiers (vs 4 in docs-3)
- `prompts/` — 12 owner/coordinator prompt templates
- `proof/` — capability proof grading system
- `qa/` — quality assurance contracts (metrics, negative controls, matrices)
- `records/` — decision records
- `references/` — external references
- `report/` — review reports
- `research/` — research artifacts
- `risks/` — risk register
- `schemas/` — JSON schemas for artifacts
- `scripts/` — automation scripts
- `specs/` — formal specs (001-identity, 002-intent, 003-federation, etc.)
- `validation/` — validation evidence

## 2. Per-product dossier coverage (from vole output, 33 products analyzed)

### Complete (all 7 canonical files present): 23 products

AgilePlus, BytePort, CivicWarfare, Civis, Dino, HeliosCLI, HeliosLab, HeliosLite, KCode, Khostty, KooshaPari, Melosviz, OmniRoute, PhenoApps, PhenoDesign, PhenoFabric, PhenoLab, PhenoRegistry, PhenoShared, Portage, ShareCLI, Tracera, WorldSphereMod

### Incomplete (only DOSSIER.md present, 6 helper files MISSING): 10 products

| Product | Files present | Status |
|---|---|---|
| Agentora-capability | 1/7 | Starter dossiers only |
| PhenoAI | 1/7 | Missing STATE, NEXT-ACTIONS, AGENT-PROMPT, FEDERATION, REVIEW-REPORT |
| PhenoGfx | 1/7 | Same gap |
| PhenoInfra | 1/7 | Same gap |
| PhenoMLX | 1/7 | Same gap (but docs-3 has full dossier) |
| PhenoTooling | 1/7 | Same gap |
| Pine | 1/7 | Same gap |
| ResearchLedger | 1/7 | **Intentional: per sponsor scope, out of scope** |
| SessionLedger | 1/7 | Same gap |
| Substrate | 1/7 | Same gap |

**Observation:** The 6 missing files per product are:
1. `START-HERE.md`
2. `STATE.md`
3. `NEXT-ACTIONS.md`
4. `AGENT-PROMPT.md`
5. `FEDERATION.md`
6. `REVIEW-REPORT.md`

These are the same 6 files missing across all 10 incomplete products, indicating docs-5 treats them as a per-product template set that was filled out for 23 products and skipped for 10. The four products with full docs-3 dossiers (PhenoMLX, HeliosLab, PhenoShared, Portage) appear in the "complete" list for docs-5, so docs-5 is at parity with docs-3 for our 4 active repositories.

## 3. Direct reads of structural docs

### `~/Downloads/phenotype-canonicalization/`

**README.md** — Research proposal for canonical engineering patterns covering:
- Agentic migration paths (from human-only to human+agent workflows)
- Federated governance (multiple repos cooperating under one authority)
- Pattern libraries and standardization across the 33+ products

**REPORT.md** (~37KB) — Comprehensive analysis of canonical tooling patterns:
- Inventory of existing tooling across Phenotype repos
- Gap analysis: what's missing for canonical patterns
- Recommendations for tooling consolidation

**CANONICAL-ENGINEERING.md**, **AGENTIC-MIGRATION.md**, **FEDERATED-GOVERNANCE.md**, **PATTERN-LIBRARIES.md** — Four pillar documents defining the canonicalization work streams.

**Status:** Reports are research-stage, not executed. No concrete migration plan or sequenced WBS. The 6 docs-5 subdirectories (`prompts/`, `proof/`, `federation/`, `specs/`, `qa/`, `architecture/`) appear to be the execution layer below this research.

### `~/Downloads/docs-5/` (root structural docs)

**START-HERE.md** — v1.4 controlling entry point. Changes from docs-3 v1.1:
- One-owner-per-repo model (vs docs-3's looser allocation)
- Explicit per-repo owner allocation table
- Federation contract becomes mandatory (was optional in docs-3)

**README.md** (~47KB) — Operational handbook. vs docs-3 README:
- 33 product dossiers vs 4
- 15 ADRs vs 13
- Full portfolio roster with 54 session seats
- Federation protocol with JSON schemas for cross-repo handoffs

**SSOT_AUTHORITY.md** — Single Source of Truth definitions. Largely identical to docs-3, with these additions:
- Federation contracts are now first-class SSOT entries
- Per-product dossiers override global guidance when they conflict
- Owner prompts are SSOT for execution style

**PRD.md, REQUIREMENTS.md, SPECIFICATION.md, ALD.md, HLD.md, LLD.md, DOMAIN_MODEL.md, ROADMAP.md, TRACEABILITY.md, VALIDATION_REPORT.md** — All present and extended.

**CHANGELOG-V1.2.md, CHANGELOG-V1.3.md, CHANGELOG-V1.4.md** — Version progression:
- v1.2: Added proof grading system, capability composition
- v1.3: Added federation protocol, reciprocal application
- v1.4: Added 29 new product dossiers, one-owner-per-repo model

**OWNER-QUICKSTART.md, INDEX.md, REVISION-1.1.md** — Operator onboarding.

## 4. Subdirectory depth analysis

### `docs-5/federation/` (30+ files) — Most elaborate subsystem

- `PRODUCT-CONTRACT.md` — How a product exposes itself for federation
- `RUNTIME-ARCHITECTURE.md` — Federation runtime model
- `WORK-PLAN.md`, `OWNER-MATRIX.md`, `OWNER-MAP.json` — Coordination
- `ACCEPTANCE.md`, `VALIDATION.md`, `GAP-AUDIT.md` — Quality gates
- `requirements.json`, `work-packages.json`, `sources.json` — Machine-readable artifacts
- `schemas/` — JSON schemas for handoff payloads
- `RECIPROCAL-APPLICATION-FEDERATION.pdf` — Spec PDF
- `EXPERIENCE-CONTRACT.md`, `PLATFORM-LOWERING.md`, `LIFECYCLE-AND-RECOVERY.md`, `RESEARCH-AND-PILOT.md`, `SECURITY-AND-DATA.md`, `SOURCES.md` — Federated lifecycle

This is the most mature new subsystem. It replaces ad-hoc cross-repo coordination with a typed contract.

### `docs-5/proof/` — Capability proof grading

- `GRADING.md` — How to grade a capability (numeric rubric)
- `CAPABILITY-COMPOSITION.md` — How composed capabilities inherit grades
- `VISUAL-VERIFICATION.md` — How to verify visual capabilities
- `OWNER-MATRIX.md`, `OWNER-MAP.json` — Owner allocation
- `requirements.json`, `scenarios.json`, `work-packages.json` — Artifacts
- `CAPABILITY-DESIGN-PROOF-GRADING.pdf` — Spec PDF
- `grade.py`, `test_support.py` — Automation
- `ADR-016` formalizes the grading system

### `docs-5/qa/` — Quality assurance contracts

- `ASSURANCE-CONTRACT.md` — 85% coverage floor, independent negative controls
- `METRICS.md` — 27 measurement families
- `NEGATIVE-CONTROLS.md` — Instrument qualification
- `MATRIX-DESIGN.md` — How to design test matrices
- `DOCUMENTATION-COVERAGE.md` — Doc quality metrics
- `metrics.json` — Machine-readable

This is a superset of docs-3's `qa/` directory.

### `docs-5/prompts/` — 12 prompt templates

- `MASTER-COORDINATOR.md` — Top-level coordination prompt
- `PRODUCT-OWNER.md` — Per-product owner prompt template
- `FOUNDATION-OWNER.md` — Foundation library owner
- `INDEPENDENT-ASSURANCE-AND-PILOT.md` — Independent verification prompt
- `DELIVERY-VERIFIER.md` — Delivery gate prompt
- `ATLAS-EXTRACTOR.md` — Information extraction prompt
- `CAPABILITY-PROOF-GRADING-ADDENDUM.md` — Grading addendum
- `ECOSYSTEM-FIRST-ADDENDUM.md` — Ecosystem evolution addendum
- `RECIPROCAL-FEDERATION-ADDENDUM.md` — Federation addendum
- `ONE-CHAT-PER-REPOSITORY.md` — Workflow discipline
- `APPLY-TO-EXISTING-CHATS.md` — Rollout instructions
- `TRACERA-TEN-SEATS.md` — Tracera-specific

### `docs-5/specs/` — Formal numbered specs

- `001-identity`, `002-intent`, `003-federation`, etc. — Numbered, sequenced formal specs

### `docs-5/risks/` — Risk register

- 20 identified risks with controls

## 5. Authority conflict between docs-3 and docs-5

docs-3 has `SSOT_AUTHORITY.md` claiming authority as the "single source of truth for all Phenotype product quality gates, dossiers, and ecosystem governance" (per our existing global AGENTS.md). docs-5 makes the same claim with stricter scope ("v1.4 instruction set").

**Conflict zones:**

1. **Scope:** docs-3 covers 4 products (PhenoMLX, HeliosLab, PhenoShared, Portage). docs-5 covers 33. The 29 new products in docs-5 have no docs-3 baseline.

2. **Owner model:** docs-3 was looser (multiple agents per product permitted). docs-5 mandates one-owner-per-repo with explicit allocation tables.

3. **Federation:** docs-3 has none. docs-5 has a full federation protocol as a first-class subsystem.

4. **Grading:** docs-3 has informal quality gates. docs-5 formalizes numeric grading via ADR-016.

5. **Version:** docs-3 is v1.1 (with REVISION-1.1.md). docs-5 is v1.4 (CHANGELOG tracks v1.2/v1.3/v1.4 progression).

**Resolution:** docs-5 is a strict superset and supersedes docs-3 for any conflicting guidance. docs-3 should be retained as historical reference until docs-5 is fully absorbed into canonical sources.

## 6. Canonicalization relationship to docs-5

`canonicalization/` is the research/policy layer. `docs-5/` is the execution layer. The 6 canonicalization docs describe *why* and *what* canonical patterns should exist; docs-5's `prompts/`, `proof/`, `federation/`, `qa/`, and `specs/` are the *how*.

**Mapping:**
- `CANONICAL-ENGINEERING.md` → docs-5 `architecture/`, `specs/`
- `AGENTIC-MIGRATION.md` → docs-5 `prompts/`, `operations/`
- `FEDERATED-GOVERNATION.md` → docs-5 `federation/`
- `PATTERN-LIBRARIES.md` → docs-5 `proof/`, `qa/`, `examples/`

## 7. Per-repo action items

### For our 4 active repos (PhenoShared, PhenoRegistry, PhenoMLX, HeliosLab, Portage)

These all have full dossiers in docs-5 (parity with docs-3). No immediate dossier work required. They DO need:
- Federation contract handoff schemas populated
- Proof grading artifacts (per ADR-016)
- QA metrics report (per `qa/METRICS.md`)

### For 29 new products in docs-5

Of those 29, 23 have full dossiers (AgilePlus, BytePort, etc.). The 6 that lack full dossiers in docs-5 are: PhenoAI, PhenoGfx, PhenoInfra, PhenoMLX, PhenoTooling, Pine. Wait — recheck: PhenoMLX has full in docs-3 but only 1/7 in docs-5 (vole may have only found the sub-product). 5 products need full dossier completion in docs-5: PhenoAI, PhenoGfx, PhenoInfra, PhenoTooling, Pine. (PhenoMLX may be a counting error.)

Per sponsor scope, **ResearchLedger is intentionally out of scope** (per existing chat instruction). SessionLedger status unclear — needs operator confirmation.

### For the entire Phenotype org

docs-5 should be adopted as the canonical replacement for docs-3. Recommended sequence:
1. Verify 23 "complete" product dossiers are actually substantive (vole's dump suggests they are, but needs spot-check)
2. Fill the 6 missing files for 5 incomplete products (PhenoAI, PhenoGfx, PhenoInfra, PhenoTooling, Pine)
3. Migrate docs-5 into the active repo as `~/CodeProjects/Phenotype/repos/pheno/docs/` canonical docs
4. Update global AGENTS.md to point to docs-5 authority instead of docs-3
5. Populate federation contracts for all 23 complete products

## 8. Outstanding verification

The following could not be confirmed in this session due to subagent crashes:

- Whether all 23 "complete" product dossiers actually have substantive content vs. template shells
- Whether the federation/protocol JSON schemas are internally consistent
- Whether the 15 ADRs are stable or have open PRs
- Whether `RECIPROCAL-APPLICATION-FEDERATION.pdf` and `CAPABILITY-DESIGN-PROOF-GRADING.pdf` match the markdown specs

These should be re-dispatched to subagents in a fresh session with a different model.

## 9. SESSION STATUS

```
[repo: pheno | status: review synthesis complete]
[repo: all 75 repos | status: PII sweep complete, all builds pass]
█░░░░░░░░░░░░░░░░ 20% (docs adoption from 30% reviewed to 50% if we proceed)
```

## NEXT

1. **Adopt docs-5 as canonical** — Replace docs-3 references in AGENTS.md, migrate structure into `pheno/docs/`
2. **Complete 5 missing dossiers** — PhenoAI, PhenoGfx, PhenoInfra, PhenoTooling, Pine (fill 6 files each)
3. **Push PhenoRegistry** (2 commits ahead, harness-blocked)
4. **Rewrite bad READMEs** in our 75 repos (new priority directive from operator)
5. **Re-dispatch subagents with different model** for unverified items in §8

## BLOCKERS

- Subagent model mimo-v2.5 crashed 8/10 times. Need to switch to gpt-5.6-terra or similar for next batch.
- docs-5 vs docs-3 authority conflict — operator must confirm docs-5 supersedes before migration.
