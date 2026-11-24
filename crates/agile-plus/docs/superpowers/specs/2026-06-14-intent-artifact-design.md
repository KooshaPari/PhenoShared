# Prompt-Intent Artifact — Base Driver Format

> **Artifact ID:** `INTENT-ARTIFACT-v1`  
> **Version:** 1.0.0  
> **Date:** 2026-06-14  
> **Status:** DESIGN — pending review  
> **Owner:** `docs/superpowers/specs/`  
> **Scope:** All Phenotype-org projects (AgilePlus, Dino, Civis, KWatch, etc.)  

---

## 1. Purpose

This document defines the **Prompt-Intent Artifact** — a canonical markdown template that bridges a raw user prompt to a structured, actionable work package. It captures:

1. The **exact user prompt** (immutable input).
2. The **LLM synthesis of intent** (what the user actually wants).
3. The **project context** (where this work lives).
4. **Success criteria** (how we know it is done).
5. **Derived tasks** (the decomposed work items).

The artifact is the **first artifact created** when any agent receives a user prompt. It feeds downstream specs (kitty-specs, FR docs, journey pages, BDD features) and upstream intent graphs (agileplus-mcp-intent ontology).

---

## 2. Artifact Location & Naming

| Element | Convention |
|---------|------------|
| Directory | `docs/superpowers/specs/` (or `docs/intents/` for projects without superpowers) |
| Filename | `YYYY-MM-DD-<slug>-intent.md` |
| Slug | Lowercase, kebab-case, derived from the intent title |
| Example | `2026-06-14-dark-mode-intent.md` |

Every project MUST have one of:
- `docs/superpowers/specs/` (preferred, if the project has superpowers infrastructure)
- `docs/intents/` (fallback for projects without superpowers)

---

## 3. Template (Front Matter + Body)

Copy the block below into a new file under `docs/superpowers/specs/` and replace all `<placeholder>` values.

```markdown
---
artifact_id: <YYYY-MM-DD-slug-intent>
artifact_version: "1.0.0"
artifact_type: prompt-intent
status: draft
project: <project-name>
created_at: <YYYY-MM-DDTHH:MM:SSZ>
agent_id: <agent-name-or-identifier>
source_prompt_hash: <sha256-of-exact-prompt>
upstream_spec: <null-or-kitty-spec-slug>
upstream_fr: <null-or-FR-XXX-NNN>
confidence: <0.0-1.0>
---

# Intent: <Human-Readable Title>

> **Status:** `draft` | **Project:** `<project>` | **Agent:** `<agent_id>`  
> **Source prompt hash:** `sha256:<...>` (see Section 4)  
> **Upstream spec:** `<upstream_spec>` | **Upstream FR:** `<upstream_fr>`  

---

## 4. Exact User Prompt

> **Rule:** This section is immutable once the artifact is created. The prompt is pasted verbatim, without paraphrasing, summarization, or editorial correction. If the user followed up with clarifications, append them as a chronological list.

### 4.1 Original Prompt

```
<paste the exact user prompt here, preserving line breaks, punctuation, and formatting>
```

### 4.2 Clarifications / Follow-ups (optional)

| # | Timestamp | Clarification |
|---|-----------|---------------|
| 1 | `<ISO-8601>` | `<exact follow-up text>` |

---

## 5. LLM Synthesis of Intent

> **Rule:** This section is the agent's interpretation of what the user wants. It MUST be explicit, falsifiable, and scoped to the project's actual capabilities. If the prompt is ambiguous, note the ambiguity and the chosen resolution.

### 5.1 Core Intent (one sentence)

<One sentence, written in the imperative, describing the fundamental goal.>

### 5.2 Sub-intents (bullet list)

1. **<Sub-intent 1>** — <one-line description>
2. **<Sub-intent 2>** — <one-line description>
3. **<Sub-intent 3>** — <one-line description>

### 5.3 Ambiguities & Resolutions

| Ambiguity | Resolution | Confidence |
|-----------|------------|------------|
| <what was unclear> | <how the agent interpreted it> | <0.0-1.0> |

### 5.4 Out-of-scope Items

> **Rule:** Explicitly list what the user asked for (or implied) that is NOT being attempted in this intent. This prevents scope creep and sets expectations.

- <item 1> — <reason it is out of scope>
- <item 2> — <reason it is out of scope>

---

## 6. Project Context

> **Rule:** Capture the project state at the moment the intent was received. This is a snapshot, not a living document. If the project evolves, the artifact does not change retroactively.

### 6.1 Project Identity

| Field | Value |
|-------|-------|
| **Name** | `<project-name>` |
| **Repository** | `<org/repo>` |
| **Primary language** | `<language>` |
| **Build system** | `<cargo / npm / xcodebuild / ...>` |
| **Current branch** | `<branch>` |
| **Last commit** | `<sha>` |

### 6.2 Relevant Files (snapshot)

> **Rule:** List the files that the agent read, modified, or created while executing this intent. This is the traceability anchor.

| Path | Role | Action |
|------|------|--------|
| `<path/to/file>` | `<config / source / test / doc>` | `<read / modified / created>` |

### 6.3 Active Dependencies / Constraints

- <constraint 1> — <e.g., "no git operations, disk full" or "protoc not available" >
- <constraint 2> — <e.g., "must maintain hexagonal architecture" >

---

## 7. Success Criteria

> **Rule:** Each criterion MUST be binary (pass/fail), observable, and verifiable by a human or a CI gate. Criterion IDs are stable; do not renumber after the artifact is published.

| ID | Criterion | Verification Method | Owner |
|----|-----------|---------------------|-------|
| SC-1 | <one-sentence, falsifiable statement> | `<test / manual review / CI gate>` | `<agent or human>` |
| SC-2 | <one-sentence, falsifiable statement> | `<test / manual review / CI gate>` | `<agent or human>` |
| SC-3 | <one-sentence, falsifiable statement> | `<test / manual review / CI gate>` | `<agent or human>` |

### 7.1 Success Criteria → Downstream Mapping

> **Rule:** If this intent produces a kitty-spec, FR, or journey, map each SC to the downstream artifact.

| SC ID | Downstream Artifact | Downstream AC |
|-------|---------------------|---------------|
| SC-1 | `<specs/.../FR-XXX.md>` | AC-1 |
| SC-2 | `<docs/journeys/...>` | AC-2 |

---

## 8. Derived Tasks

> **Rule:** Tasks are the work items derived from the intent. Each task MUST be small enough to fit in a single agent session (or a single PR). Tasks are ordered; dependencies are noted.

### 8.1 Task List

| # | Task ID | Title | Description | Dependencies | Status | Evidence |
|---|---------|-------|-------------|--------------|--------|----------|
| 1 | `TASK-001` | <title> | <one-line description> | — | pending | — |
| 2 | `TASK-002` | <title> | <one-line description> | `TASK-001` | pending | — |
| 3 | `TASK-003` | <title> | <one-line description> | `TASK-002` | pending | — |

### 8.2 Task → Intent Graph Mapping (optional)

> **Rule:** If the project uses `agileplus-mcp-intent`, map tasks to ontology nodes.

| Task ID | Node Type | Node ID | Relationship |
|---------|-----------|---------|--------------|
| TASK-001 | `Feature` | `Feature#<slug>-feat-1` | `implements` Intent |
| TASK-002 | `Task` | `Task#<slug>-task-2` | `derives-from` Feature |

---

## 9. Execution Log

> **Rule:** Append a row every time the agent works on this intent. This is the audit trail.

| # | Timestamp | Agent | Action | Result | Evidence |
|---|-----------|-------|--------|--------|----------|
| 1 | `<ISO-8601>` | `<agent>` | `<started / resumed / completed / blocked>` | `<summary>` | `<commit-sha or PR>` |

---

## 10. Evaluation Checklist

- [ ] Section 4 (Exact Prompt) is verbatim and unedited.
- [ ] Section 5 (Intent Synthesis) is falsifiable and scoped.
- [ ] Section 6 (Project Context) lists real paths that exist in the working tree.
- [ ] Section 7 (Success Criteria) has at least one binary, verifiable criterion.
- [ ] Section 8 (Derived Tasks) decomposes the intent into session-sized work items.
- [ ] All `<placeholder>` values are replaced with concrete data.
- [ ] The artifact is saved to `docs/superpowers/specs/YYYY-MM-DD-<slug>-intent.md`.

---

## 11. See Also

- `docs/templates/journey-template.md` — if this intent spawns a journey page.
- `specs/<module>/bdd/<journey>.feature` — if this intent spawns BDD scenarios.
- `docs/requirements/<project>-frnfr.md` — if this intent spawns a new FR.
- `kitty-specs/<slug>/spec.md` — if this intent spawns an ecosystem spec.
- `crates/agileplus-mcp-intent/README.md` — intent graph ontology reference.
- `docs/ai-dd-governance.md` — quality gate and traceability rules.
```

---

## 4. Field-by-Field Specification

### 4.1 Front Matter

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `artifact_id` | string | Yes | Unique ID: `YYYY-MM-DD-slug-intent` |
| `artifact_version` | string | Yes | SemVer of the artifact format itself |
| `artifact_type` | enum | Yes | Always `prompt-intent` |
| `status` | enum | Yes | `draft` → `review` → `approved` → `superseded` |
| `project` | string | Yes | Project name (AgilePlus, Dino, Civis, etc.) |
| `created_at` | ISO-8601 | Yes | UTC timestamp of creation |
| `agent_id` | string | Yes | The agent that created the artifact |
| `source_prompt_hash` | sha256 | No | Hash of the exact prompt (for integrity) |
| `upstream_spec` | string | No | `kitty-specs/<slug>` if linked |
| `upstream_fr` | string | No | `FR-XXX-NNN` if linked |
| `confidence` | float | No | Agent's confidence in the synthesis (0.0–1.0) |

### 4.2 Body Sections

| Section | Purpose | Immutable? |
|---------|---------|------------|
| 4. Exact Prompt | Preserves the raw input | **Yes** |
| 5. Intent Synthesis | Agent's interpretation | No (can be revised with user feedback) |
| 6. Project Context | Snapshot of the workspace | **Yes** (snapshot semantics) |
| 7. Success Criteria | Definition of done | No (can be refined) |
| 8. Derived Tasks | Decomposed work items | No (updated as work progresses) |
| 9. Execution Log | Audit trail | Append-only |
| 10. Eval Checklist | Self-verification gate | No (checked by agent) |

---

## 5. Relationship to Existing Artifacts

### 5.1 Upstream: User Prompt

The artifact is the **first artifact** created after the user prompt. It is the translation layer from natural language to structured work.

### 5.2 Downstream: Intent Graph (JSON)

If the project uses `agileplus-mcp-intent`, the artifact's Sections 5 and 8 can be fed to the `convert_prompt_to_intent_graph` tool to produce a JSON intent graph. The markdown artifact is the **human-readable source of truth**; the JSON graph is the **machine-readable derivative**.

### 5.3 Downstream: kitty-specs

If the intent requires a formal specification, the artifact feeds into `kitty-specs/<slug>/spec.md`:
- Section 5 (Intent Synthesis) → Problem statement
- Section 7 (Success Criteria) → Acceptance Criteria
- Section 8 (Derived Tasks) → Functional Requirements

### 5.4 Downstream: FR/NFR Catalog

If the intent requires a new functional requirement, the artifact feeds into `docs/requirements/<project>-frnfr.md`:
- Section 5 → Description
- Section 7 → Acceptance Criteria
- Section 6 → Traceability

### 5.5 Downstream: Journey Pages

If the intent requires user-facing documentation, the artifact feeds into `docs/journeys/<journey-id>.md`:
- Section 5 → User story
- Section 7 → Acceptance Criteria
- Section 8 → Steps

---

## 6. Audit Findings: What Exists vs. What Is Missing

### 6.1 Existing Spec Artifacts in AgilePlus

| Artifact | Location | Format | Notes |
|----------|----------|--------|-------|
| FR specs | `specs/<module>/FR-XXX-NNN.md` | Markdown | Per-crate functional requirements; no front matter |
| BDD features | `specs/<module>/bdd/*.feature` | Gherkin | Linked to FR specs via tags |
| kitty-specs | `kitty-specs/<slug>/spec.md` | Markdown + YAML front matter | Ecosystem-level specs; formal structure |
| FR/NFR catalog | `docs/requirements/agileplus-frnfr.md` | Markdown | Backfilled from shipped PRs |
| Journey pages | `docs/journeys/*.md` | Markdown + YAML front matter | Rich-media stubs, traceability tables |
| Journey templates | `docs/templates/journey-template.md` | Markdown | Copy-paste template with eval checklist |
| BDD templates | `docs/templates/bdd-feature-template.feature` | Gherkin | Copy-paste template with tagging rules |
| Intent graph (JSON) | `crates/agileplus-mcp-intent/README.md` | JSON example | Rule-based prompt-to-graph converter |
| Architecture | `ARCHITECTURE.md` | Markdown | Project-level architecture |
| SPEC | `SPEC.md` | Markdown | Stack, commands, decisions |
| Governance | `docs/ai-dd-governance.md` | Markdown | Quality gates, drift detection, traceability |

### 6.2 Missing Artifacts

| Missing Artifact | Impact | This Design Addresses |
|------------------|--------|----------------------|
| `docs/superpowers/` directory | No canonical place for agent-level artifacts | Creates `docs/superpowers/specs/` |
| Prompt-intent template | No bridge from raw prompt to structured specs | Defines the base driver format |
| Verbatim prompt preservation | User prompts are lost or paraphrased | Section 4: immutable exact prompt |
| Confidence scoring | No structured confidence metadata | `confidence` front-matter field |
| Out-of-scope enumeration | Scope creep is common | Section 5.4: explicit exclusions |
| Session-sized task decomposition | Intents are too large for single sessions | Section 8: ordered task list with dependencies |
| Execution audit trail | No log of agent actions per intent | Section 9: append-only execution log |

### 6.3 Cross-Project Gap Analysis

| Project | Has `specs/` | Has `docs/superpowers/` | Has intent template | Has FR catalog |
|---------|------------|------------------------|---------------------|----------------|
| AgilePlus | Yes | **No** | **No** | Yes |
| Dino | Yes | Yes (plans only) | **No** | Partial |
| Civis | Yes | Yes (plans only) | **No** | Partial |
| KWatch | Yes | **No** | **No** | Partial |

> **Finding:** No project in the Phenotype org has a canonical prompt-intent artifact. The `agileplus-mcp-intent` crate produces JSON graphs, but there is no human-readable markdown equivalent that preserves the raw prompt and captures the agent's reasoning. This design fills that gap.

---

## 7. Usage Instructions for Agents

### 7.1 On Receiving a User Prompt

1. **Hash the prompt** — compute SHA-256 of the exact text.
2. **Create the artifact** — copy the template, fill front matter, paste prompt into Section 4.
3. **Synthesize intent** — write Sections 5.1–5.3. If ambiguous, ask the user before proceeding.
4. **Snapshot context** — write Section 6 with real paths from the working tree.
5. **Draft success criteria** — write Section 7 with at least one binary criterion.
6. **Decompose tasks** — write Section 8 with session-sized work items.
7. **Save** — write to `docs/superpowers/specs/YYYY-MM-DD-<slug>-intent.md`.

### 7.2 During Execution

1. **Append to Execution Log** — Section 9, one row per session.
2. **Update task status** — Section 8, mark tasks `in-progress`, `completed`, or `blocked`.
3. **Revise success criteria** — if scope changes, update Section 7 and note the revision in the log.

### 7.3 On Completion

1. **Run eval checklist** — Section 10, all boxes must be checked.
2. **Map downstream** — if the intent spawned a kitty-spec, FR, or journey, fill Section 7.1.
3. **Archive or publish** — set `status: approved` in front matter.

---

## 8. Governance & Quality Gates

| Gate | Rule | Enforcer |
|------|------|----------|
| **Immutable Prompt** | Section 4 must not be edited after creation | Agent self-check + lefthook |
| **Verifiable Criteria** | Every SC must have a verification method | `docs/ai-dd-governance.md` traceability |
| **Session Sizing** | No task in Section 8 may exceed a single agent session | PR size check (≤ 800 lines) |
| **Real Paths** | Every path in Section 6.2 must exist in the working tree | `git ls-files` validation |
| **Downstream Linkage** | If an intent spawns a spec, the spec must link back to the intent | `tooling/trace-validator` |

---

## 9. Version History

| Version | Date | Change | Author |
|---------|------|--------|--------|
| 1.0.0 | 2026-06-14 | Initial design | Forge |

---

## 10. See Also

- `docs/templates/journey-template.md` — downstream journey artifact
- `docs/templates/bdd-feature-template.feature` — downstream BDD artifact
- `docs/ai-dd-governance.md` — quality gate and drift detection
- `crates/agileplus-mcp-intent/README.md` — intent graph ontology (JSON)
- `FUNCTIONAL_REQUIREMENTS.md` — downstream FR catalog
- `kitty-specs/` — downstream ecosystem specs
- `specs/` — downstream crate-level specs
