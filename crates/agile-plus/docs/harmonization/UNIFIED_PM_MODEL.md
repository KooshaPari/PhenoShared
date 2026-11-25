# Unified Project Management Model

**Status:** Proposed — harmonization synthesis  
**Branch:** `harmonize/unified-pm-model`  
**Inputs:** [`FRAMEWORK_ANALYSIS.md`](FRAMEWORK_ANALYSIS.md), AgilePlus domain ADRs (0007–0010), Tracera FR/NFR catalog  
**Scope:** Ideology and operating model only — no implementation in this document.

---

## Executive Summary

AgilePlus and Tracera today share a **vocabulary spine** (`traceability-core` / `phenotype-pm-core`) but **not a unified runtime**. Tracera depends on traceability types only and treats governance as a **checklist** (coverage cells, link presence, gate predicates evaluated read-only). AgilePlus is a **process machine**: Feature lifecycle FSM, IntentGraph authoring, claim engine, and versioned `GovernanceContract` binding that **blocks** transitions until evidence and policies pass.

This document defines the **superset-merge** ideology: one reconciled artifact set, lifecycle, gate stack, and traceability graph that composes AgilePlus process control with Tracera evidence projection and best-of patterns from OpenSpec, Spec-Kit, GSD, BMAD, Scrum, PMBOK, and Shape Up.

**Architectural consequence (see ADR-0011):** Tracera **embeds** AgilePlus (or `pm-core` owned by AgilePlus). Tracera MUST NOT run without AgilePlus. AgilePlus remains optionally standalone for teams that need process control without the Tracera graph UI/API.

---

## 1. Current-State Gap Analysis

### 1.1 What is shared today

| Concern | Shared via `traceability-core` | AgilePlus | Tracera |
|---------|-------------------------------|-----------|---------|
| Requirement IDs | `RequirementId`, FR/NFR namespace | Authors in kitty-specs + FR catalog | Ingests as `Requirement` nodes |
| Intent graph types | `IntentGraph`, `Node`, `Edge` | Authors + validates at MCP ingest | Read-only projection |
| Governance types | `GovernanceContract`, `GovernanceRule` | Authors, binds, enforces transitions | Reads; evaluates checklist |
| Progression gates | `ProgressionGate`, `GatePredicate` | Enforces in CLI/API FSM | Evaluates read-only |
| Coverage | `CoverageMatrix`, `AcceptanceContract` | Consumes matrix for ship gate | Builds matrix from TraceLinks |

### 1.2 What is NOT shared (the harmonization target)

| Gap | AgilePlus | Tracera today | Unified rule |
|-----|-----------|---------------|--------------|
| **Runtime coupling** | Standalone CLI + SQLite + FSM | Standalone Go API + Postgres | Tracera embeds AgilePlus process runtime |
| **Governance semantics** | Process machine: transition blocked until contract satisfied | Checklist: predicates evaluated, no FSM ownership | Process machine owns; Tracera surfaces + verifies |
| **Artifact authority** | `kitty-specs/`, worklogs, ADRs | Requirement/Artifact/TraceLink graph | Spec tree is intent source; graph is evidence projection |
| **Work execution** | WP lanes, claim engine, worktrees | None | AgilePlus owns execution; Tracera links outcomes |
| **Lifecycle FSM** | `FeatureState` transitions enforced | No feature lifecycle | Single FSM; Tracera observes state changes |

### 1.3 Framework analysis synthesis

[`FRAMEWORK_ANALYSIS.md`](FRAMEWORK_ANALYSIS.md) establishes the cross-framework invariant:

```text
INTENT → SPEC → PLAN → EXECUTE → VERIFY → EVIDENCE
```

Every evaluated framework (OpenSpec deltas through Waterfall RTM) implements variations of this spine. The unified model **does not** adopt one framework wholesale; it composes a **layered stack** (§4) with scale-adaptive ceremony (GSD quick mode for chores, BMAD depth for epics, Shape Up appetite for portfolio bets).

---

## 2. Superset-Merge Principles

### P1 — Process machine over checklist

Governance is not a post-hoc lint pass. `GovernanceContract` + `ProgressionGate` + Feature FSM **block** illegal transitions. Tracera's coverage matrix and TraceLink graph provide **evidence inputs** to the claim engine; they do not replace the FSM.

*Source:* AgilePlus ADR-0007, ADR-0009; reverses Tracera's read-only checklist posture.

### P2 — Single canonical artifact root

One spec tree: `kitty-specs/<feature-id>/` with harmonized imports from OpenSpec (`proposal.md` / delta specs), Spec-Kit (`constitution.md`, `contracts/`), GSD (`.planning/STATE.md` linked, not duplicated), and BMAD shards (referenced by id). The `agileplus-spec-harmonizer` crate normalizes external formats to `WorkPackage` shape (ADR-0006).

*Source:* FRAMEWORK_ANALYSIS §4.3 anti-pattern: triple spec roots.

### P3 — Single ID namespace

`FR-xxx`, `NFR-xxx`, `IC-##`, `WP-##`, `REQ-XX` (GSD import) map to spine `RequirementId`. TraceLink nodes reference the same ids. No shadow catalogs.

### P4 — Evidence before merge

`trace.json`, Tracera TraceLinks, hash-chained worklogs (ADR-004), and CI gate results must exist **before** WP transitions to `for_review`. Evidence-after-merge is an anti-pattern.

### P5 — Scale-adaptive ceremony

| Change class | Primary pattern | Layers engaged |
|--------------|-----------------|----------------|
| Bug / chore | GSD quick mode or OpenSpec fluid apply | L0 evidence |
| Single feature | Spec Kitty full lane | L1–L3 |
| Brownfield refactor | OpenSpec explore + Tracera impact | L0–L2 |
| Enterprise epic | BMAD PRD → epics → WPs | L2–L4 |
| Portfolio initiative | OKRs + Shape Up pitch | L4 only |

### P6 — Repo-native, agent-native

All durable artifacts live in git (markdown, YAML, JSON derivatives). Agents read/write in worktree isolation (Spec Kitty lanes). Fresh-context sub-agents handle research/plan/verify (GSD). Machine gates replace trust-me PRs.

---

## 3. Unified Artifact Set

One reconciled artifact catalog. Each artifact has an **owner layer**, **authoring tool**, and **downstream consumers**.

| Artifact | Path / type | Owner | Author | Consumers |
|----------|-------------|-------|--------|-----------|
| **Charter** | OKR link, Shape Up pitch, or `proposal.md` | L4 Outcomes | Human / BMAD PM | FSM `Draft` gate |
| **Constitution** | `.specify/memory/constitution.md` or repo `CONSTITUTION.md` | L3 Governance | Architect | All specs, ADRs |
| **Feature spec** | `kitty-specs/<id>/spec.md` | L3 Governance | Spec Owner | Harmonizer, IntentGraph |
| **FR/NFR catalog** | `docs/requirements/*-frnfr.md` | L3 Governance | Spec Owner | Tracera ingest, trace-validator |
| **Plan** | `kitty-specs/<id>/plan.md` + IC-## map | L2 Delivery | Architect / GSD planner | WPs, TraceLink `implements` |
| **Architecture** | `design.md` / `architecture.md` / ADRs | L3 Governance | Architect | Governance rules |
| **Tasks / WPs** | `tasks.md`, `wps.yaml` | L2 Delivery | SM / agent | Claim engine, worktrees |
| **Intent graph** | `traces/intent-*.json` (derivative) | L1 Execution | MCP intent tooling | Validation, impact analysis |
| **Work log** | `.work-audit/worklog-*.json` | L0 Evidence | Agent Operator | Audit chain |
| **Trace record** | `traces/*.json` (5-layer schema) | L0 Evidence | trace-validator | Tracera projection |
| **Verification** | `VERIFICATION.md`, test results | L0 Evidence | Verifier | ProgressionGate |
| **Coverage matrix** | Tracera `CoverageMatrix` (runtime) | L0 Evidence | Tracera (derived) | AcceptanceContract satisfaction |
| **TraceLink graph** | Tracera Requirement/Artifact/TraceLink | L0 Evidence | Tracera + ingest | Impact analysis, compliance RTM |
| **Governance contract** | `contracts/governance-v*.json` | L3 Governance | AgilePlus | FSM transition gate |
| **Delta spec** | `openspec/changes/<id>/` (linked) | L1 Execution | Agent | Brownfield isolation |

**Merge rule:** External framework artifacts are **imported or linked**, never forked into parallel roots. `agileplus-spec-harmonizer` is the single ingress for GSD, OpenSpec, BMAD, and Spec-Kitty shapes.

---

## 4. Unified Lifecycle

Eight stages map to one Feature FSM spine. Stages are **logical**; small changes may skip stages via quick-mode policy in `GovernanceContract`.

```text
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌────────────┐
│ 1 Charter│ → │ 2 Specify│ → │  3 Plan  │ → │4 Decompose │
└──────────┘   └──────────┘   └──────────┘   └────────────┘
                                                    │
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────▼─────┐
│8 Archive │ ← │7 Evidence│ ← │ 6 Verify │ ← │ 5 Execute  │
└──────────┘   └──────────┘   └──────────┘   └────────────┘
```

| Stage | Unified name | FeatureState (indicative) | Primary gate | Framework bias |
|-------|--------------|----------------------------|--------------|----------------|
| 1 | **Charter** | `Draft` | Problem + appetite approved | Shape Up / OpenSpec propose |
| 2 | **Specify** | `Specified` | Spec accepted; FR IDs assigned | Spec Kitty / Spec-Kit |
| 3 | **Plan** | `Planned` | Plan checker or architect sign-off | GSD / BMAD |
| 4 | **Decompose** | `Ready` | WPs defined; lane capacity | Spec Kitty `wps.yaml` |
| 5 | **Execute** | `InProgress` | Resource claim held; DoD per WP | Agent + worktree |
| 6 | **Verify** | `InReview` | Tests green; trace-validator pass | AgilePlus CI + GSD verifier |
| 7 | **Evidence** | `Approved` | Coverage ≥ threshold; governance satisfied | Tracera + claim engine |
| 8 | **Archive** | `Done` / `Shipped` | Delta merged; lane closed | OpenSpec archive / retro |

**FSM ownership:** AgilePlus `FeatureState` is canonical. Tracera receives state-change events and updates graph metadata; it does not advance the FSM independently.

**WP sub-lifecycle** (within Execute–Verify): `planned` → `claimed` → `in_progress` → `for_review` → `done` | `blocked` | `canceled`. Resource claims (ADR-0009) gate `claimed` and heartbeat through `in_progress`.

---

## 5. Unified Gate Stack

Gates compose in strict order. Failure at any layer blocks the transition.

```text
┌─────────────────────────────────────────────────────────────┐
│ L4 — OUTCOME GATE     OKR/KR link or betting-table approval │
├─────────────────────────────────────────────────────────────┤
│ L3 — GOVERNANCE GATE  GovernanceContract rules for transition│
├─────────────────────────────────────────────────────────────┤
│ L2 — PROGRESSION GATE ProgressionGate predicates (ADR-0009) │
├─────────────────────────────────────────────────────────────┤
│ L1 — RESOURCE GATE    ClaimStore TTL/heartbeat (WP scope)   │
├─────────────────────────────────────────────────────────────┤
│ L0 — CI GATE          lefthook + quality-gate + trace-validator│
└─────────────────────────────────────────────────────────────┘
```

| Gate | Predicate examples | Enforced by | Tracera role |
|------|-------------------|-------------|--------------|
| Outcome | KR measurable; appetite set | Human / betting table | Read-only link to initiative |
| Governance | Evidence types present per transition | AgilePlus FSM | Supplies evidence refs |
| Progression | `missing_acceptance`, `missing_evidence`, `missing_test` | Claim engine (spine) | Builds CoverageMatrix input |
| Resource | `ClaimKind::Worktree` held, not expired | agileplus-triage | None |
| CI | clippy, tests, trace-validator, secrets scan | lefthook + CI | Ingest CI artifacts as TraceLinks |

**Fail closed:** No `--no-verify`, no silent downgrade, no Tracera-side override of FSM denial.

---

## 6. Unified Traceability Model

### 6.1 Layer union (AgilePlus ∩ Tracera)

| Layer | AgilePlus artifact | Tracera projection | Unified rule |
|-------|-------------------|-------------------|--------------|
| Requirement | FR-xxx, NFR-xxx in spec + catalog | `Requirement` node | Single canonical ID |
| Spec | `kitty-specs/<id>/spec.md` | — (intent source) | Spec is authority |
| Design | plan.md IC-## | TraceLink `implements` | IC-## ↔ WP ↔ module |
| Code | anchor comments, paths | Artifact + confidence-scored link | Validator + graph |
| Test | test name in trace.json | TraceLink `verifies` | Every new function: test or waiver |
| Evidence | worklog JSON, PR | audit/event store | Hash-chained append-only |

### 6.2 IntentGraph + TraceLink composition

- **IntentGraph** (ADR-0008): DAG of intent → plan → execution nodes; human markdown is source, JSON is validated derivative.
- **TraceLink graph**: Runtime evidence mesh over Requirements, Artifacts, and typed edges (`IMPLEMENTS`, `VERIFIES`, `DERIVES`, etc.).
- **Bridge rule:** IntentGraph node ids MUST equal spine `RequirementId` or explicit `ArtifactRef` mappings ingestible by Tracera. No orphan graph nodes.

### 6.3 Coverage and acceptance

`AcceptanceContract::is_satisfied(matrix)` (ADR-0010) is the sole automation signal for acceptance. Tracera builds the matrix from TraceLinks; AgilePlus rejects ship when unsatisfied. Gherkin refs are advisory metadata only.

### 6.4 Bidirectional confirmation (NFR-AP-001)

When AgilePlus links to Tracera evidence, `TraceabilityPort` must receive confirmation. Orphan claims are rejected. This survives the embed re-architecture as an internal port, not a cross-service hop.

---

## 7. Unified Role Model

Minimum viable roles for mixed human/agent teams:

| Role | Responsibility | Framework source |
|------|----------------|------------------|
| **Outcome Owner** | OKR/KR alignment, betting approval | OKRs, Shape Up |
| **Spec Owner** | spec.md acceptance, IC-## completeness | Spec Kitty PO analog |
| **Architect** | constitution, plan.md, ADRs | Spec-Kit, BMAD |
| **Agent Operator** | WP execution in worktree, atomic commits | GSD executor |
| **Verifier** | trace-validator, CI, QA against spec | AgilePlus, XP |
| **Trace Curator** | TraceLink graph health, impact analysis | Tracera (embedded) |

BMAD personas map to these six at scale; small teams collapse roles.

---

## 8. Layered Framework Stack

```text
┌─────────────────────────────────────────────────────────────┐
│  L4 — OUTCOMES     OKRs · Shape Up betting · Lean metrics   │
├─────────────────────────────────────────────────────────────┤
│  L3 — GOVERNANCE   Constitution · FR/NFR · ADRs · BMAD PRD  │
├─────────────────────────────────────────────────────────────┤
│  L2 — DELIVERY     Spec Kitty lanes · GSD phases · Scrum cadence (optional) │
├─────────────────────────────────────────────────────────────┤
│  L1 — EXECUTION    OpenSpec deltas · Spec-Kit tasks · worktrees │
├─────────────────────────────────────────────────────────────┤
│  L0 — EVIDENCE     Tracera TraceLink · trace.json · CI gates · worklogs │
└─────────────────────────────────────────────────────────────┘
```

**Runtime mapping:**

| Layer | AgilePlus component | Tracera component (embedded) |
|-------|--------------------|-----------------------------|
| L4 | Charter CLI hooks (future) | Initiative ↔ Requirement linking |
| L3 | Domain FSM, GovernanceContract, ADR tooling | Contract read + evidence catalog |
| L2 | WP lanes, harmonizer, triage | CoverageMatrix builder |
| L1 | Worktrees, claim engine, MCP | Artifact ingest, impact queries |
| L0 | trace-validator, audit chain | TraceLink store, graph API |

---

## 9. Anti-Patterns (merged)

| Anti-pattern | Mitigation |
|--------------|------------|
| Triple spec roots (`specs/`, `kitty-specs/`, `.planning/`) | Canonical `kitty-specs/` + harmonizer ingress |
| Chat-only intent | Charter artifact before WP claim |
| Tracera standalone without process FSM | ADR-0011 embed mandate |
| Governance as checklist only | Process machine owns transitions (§2 P1) |
| SAFe ceremony on 1-dev agent loops | SAFe vocabulary at L4 only |
| Waterfall phase gates on every bugfix | GSD quick mode + OpenSpec fluid apply |
| Evidence after merge | trace.json required before `for_review` |
| Shadow FR catalogs | Single namespace via spine `RequirementId` |

---

## 10. ADR Index (this harmonization track)

| ADR | Title |
|-----|-------|
| [0011](../adr/0011-tracera-embeds-agileplus.md) | Tracera embeds AgilePlus |
| [0012](../adr/0012-unified-artifact-set.md) | Unified artifact set |
| [0013](../adr/0013-unified-lifecycle-and-gates.md) | Unified lifecycle and gate stack |
| [0014](../adr/0014-unified-traceability-model.md) | Unified traceability model |
| [0015](../adr/0015-process-machine-over-checklist-governance.md) | Process machine over checklist governance |
| [0016](../adr/0016-unified-framework-layer-stack.md) | Unified framework layer stack |
| [0017](../adr/0017-tracera-embedding-migration-path.md) | Tracera embedding migration path |

**Prior spine ADRs (unchanged vocabulary, refined ownership):** 0005 traceability-core, 0007 governance contract, 0008 intent graph, 0009 claim engine, 0010 acceptance contract.

---

## References

| Source | Location |
|--------|----------|
| Framework comparative matrix | [`FRAMEWORK_ANALYSIS.md`](FRAMEWORK_ANALYSIS.md) |
| AI-DD quality gates | `docs/ai-dd-governance.md` |
| Traceability NFRs | `docs/specs/NFR-AP-001-traceability-requirements.md` |
| Tracera FR catalog | `docs/requirements/tracera-frnfr.md` |
| Cross-repo DRY audit | `docs/audit/XREPO_DRY.md` |
| Spec harmonizer | ADR-0006 |

---

*Document version: 1.0 — harmonize/unified-pm-model — 2026-06-26*
