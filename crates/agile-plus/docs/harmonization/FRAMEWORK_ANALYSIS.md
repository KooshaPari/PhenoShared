# Framework Process Analysis — Comparative Matrix

**Status:** Draft for AgilePlus + Tracera PM-ideology harmonization  
**Branch:** `harmonize/framework-analysis`  
**Scope:** Process comparison only — no implementation. Feeds unified operating model design.

---

## Purpose

This document compares **AI-driven / spec-driven development (AI-DD)**, **traditional software engineering**, and **project/product management** frameworks across six process dimensions:

| Dimension | Question answered |
|-----------|-------------------|
| **Core artifacts** | What durable objects does the process produce? |
| **Lifecycle stages** | What ordered (or iterative) phases does work pass through? |
| **Gates / checkpoints** | Where is progress blocked until criteria are met? |
| **Traceability model** | How does intent link forward to delivery and backward to evidence? |
| **Roles** | Who decides, who executes, who verifies? |
| **AI-DD fit** | How naturally does the framework compose with agentic coding assistants? |

Legend for AI-DD fit: **★★★** native / designed for agents · **★★☆** adaptable with tooling · **★☆☆** human-centric, agents as accelerators · **☆☆☆** pre-AI, weak agent alignment.

---

## Part I — AI-DD / Spec-Driven Frameworks

### Summary Matrix

| Framework | Core artifacts | Lifecycle stages | Gates / checkpoints | Traceability model | Roles | AI-DD fit |
|-----------|----------------|------------------|---------------------|----------------------|-------|-----------|
| **OpenSpec** | `openspec/` delta specs, change folders (`proposal.md`, `specs/`, `design.md`, `tasks.md`), archived changes, schema YAML | Explore → Propose → Apply → Sync → Archive (fluid; OPSX actions, not rigid phases) | Soft: artifact DAG readiness (READY/BLOCKED/DONE); optional `/opsx:verify`; human review before apply | Delta specs per change; capability-indexed main specs; git PR as audit trail | Developer + AI agent; no prescribed personas | ★★★ |
| **GitHub Spec-Kit** | `constitution.md`, `specs/<feature>/spec.md`, `plan.md`, `tasks.md`, `research.md`, `contracts/` | Constitution → Specify → Clarify → Plan → Validate → Tasks → Implement | Hard linear gates: spec clarification required before plan; plan validation before tasks; prerequisite check before implement | Feature-folder hierarchy; constitution constrains all downstream; cross-artifact analysis | Human author + AI executor; optional MAQA multi-agent QA | ★★★ |
| **GSD (Get Sh*t Done)** | `.planning/PROJECT.md`, `REQUIREMENTS.md` (REQ-XX), `ROADMAP.md`, `STATE.md`, phase `PLAN.md`/`SUMMARY.md`/`VERIFICATION.md`, atomic git commits | Discuss → Plan → Execute → Verify → Ship (per phase/milestone) | Plan checker (8 dimensions, up to 3x loop); optional execution verification; manual UAT in verify-work | REQ-XX IDs → phases → plans → commits → SUMMARY; Nyquist validation layer | Orchestrator + sub-agents (researcher, planner, executor, verifier); human at discuss/verify | ★★★ |
| **Spec Kitty** | `kitty-specs/<feature>/spec.md`, `plan.md`, `tasks.md`, `wps.yaml`, `meta.json`, `.worktrees/`, checklists | Specify → Plan → Tasks → Implement → Review → Accept → Merge | Hard lane gates: spec accepted before implement; WP lifecycle (`planned`→`claimed`→`in_progress`→`for_review`→`done`) | IC-## concerns → WP refs in `wps.yaml`; FR-style IDs; mission templates | PM/engineering via dashboard; agent executes WPs in isolated worktrees | ★★★ |
| **BMAD Method** | `PRD.md`, `architecture.md`, `project-context.md`, `epics.md`, `{epic}.{story}.story.md`, `sprint-status.yaml` | Analysis → Planning → Solutioning → Implementation (scale-adaptive depth) | Menu-driven pauses; SM story creation gate; QA validation against PRD; `/bmad-help` routing | PRD → architecture → epics → stories → code; explicit context-engineering chain | 12+ personas (PM, Architect, Dev, SM, QA, UX, …); Party Mode multi-agent | ★★★ |
| **AIDE** (Spec-Kit ext.) | 7-step artifact chain (idea → spec → design → tasks → code → test → deploy docs) | 7-step linear AI-driven engineering lifecycle | Extension-defined; inherits Spec-Kit gate patterns | Step-indexed artifact lineage | AI-led with human approval per step | ★★★ |
| **Canon** (Spec-Kit ext.) | Baseline snapshots, drift reports, spec-first or code-first baselines | Spec-first / code-first / spec-drift reconciliation modes | Drift detection triggers re-sync | Baseline ↔ current delta | Maintainer + agent reconciler | ★★☆ |
| **Superpowers** (Claude) | `brainstorming`, `writing-plans`, `subagent-driven-development` skills; plan files in repo | Brainstorm → Write plan → Execute plan → Review → Verify before completion | TDD gate; code review subagent; verification-before-completion skill | Plan tasks → commits → review feedback | Developer + skill-invoked subagents | ★★★ |
| **AgilePlus native** | `kitty-specs/`, `FUNCTIONAL_REQUIREMENTS.md`, `traces/*.json`, `worklog-*.json`, ADRs | Specify (CLI) → WP status → implement → trace-validator → PR quality gate | `cargo test`, clippy, trace-validator, lefthook, drift-check (see `docs/ai-dd-governance.md`) | FR/NFR ID → spec → code anchor → test → `trace.json` (5-layer schema) | Human + agent; Rust CLI + MCP dispatch | ★★★ |
| **Ralph / autonomous loops** | Prompt file, iteration log, test output | Prompt → generate → test → fix loop until pass | Test-green gate; max-iteration budget | Test name ↔ requirement implicit | Autonomous agent; human sets initial prompt | ★★☆ |
| **Karpathy / Agent Skills** | `SKILL.md` files, minimal markdown instructions | Invoke skill → agent follows recipe | Soft: skill author defines checks | Skill name → behavior; no formal FR graph | Skill author + any file-reading agent | ★★☆ |

---

### OpenSpec

| Dimension | Detail |
|-----------|--------|
| **Core artifacts** | Repository-native `openspec/` tree: capability specs, per-change folders under `openspec/changes/` containing `proposal.md`, delta `specs/`, `design.md`, `tasks.md`; archived changes; optional custom schemas in `openspec/schemas/`. |
| **Lifecycle stages** | **OPSX (default):** explore → propose → apply → sync → archive. **Expanded profile:** new → continue → ff → verify → bulk-archive → onboard. Fluid — any action anytime; no mandatory phase order. |
| **Gates / checkpoints** | Artifact dependency DAG (enablers, not hard phase gates). Human agreement before `/opsx:apply`. Optional `/opsx:verify`. CI-friendly JSON validation (`openspec validate --all --json`). |
| **Traceability model** | Delta specs isolate change intent; merged into capability library on archive. Brownfield-first: explore workflow maps existing behavior before change. Git PR history = audit chain. |
| **Roles** | Single developer–agent pair; no built-in PM/QA personas. Team collaboration via standard git review. |
| **AI-DD fit** | ★★★ — Designed for 20+ AI assistants via slash commands; brownfield delta pattern minimizes context rot; schema-driven extensibility. |

**Strengths:** Brownfield change isolation, fluid iteration, living specs in-repo.  
**Weaknesses:** Light governance for enterprise compliance; roles/trace IDs less prescriptive than Spec Kitty or AgilePlus FR graph.

---

### GitHub Spec-Kit

| Dimension | Detail |
|-----------|--------|
| **Core artifacts** | `.specify/memory/constitution.md` (project principles); per-feature `specs/<NNN-name>/spec.md`, `plan.md`, `tasks.md`, optional `research.md`, `data-model.md`, `contracts/`; templates in `.specify/templates/`. |
| **Lifecycle stages** | Constitution → Specify → Clarify (required) → Plan → Validate plan → Tasks → Implement. Community extensions replace entire SDD process (AIDE, Canon, Product Forge, MAQA, …). |
| **Gates / checkpoints** | Explicit sequential gates: no plan without clarified spec; no tasks without validated plan; `/speckit.implement` checks all prerequisites. Quality checklists and cross-artifact analysis built-in. |
| **Traceability model** | Constitution → spec → plan → tasks → code. Feature directory as unit of trace. Extension ecosystem for drift and multi-agent QA. |
| **Roles** | Human as spec owner; AI as generator/implementer. MAQA extension adds orchestrated QA agents. |
| **AI-DD fit** | ★★★ — `specify-cli` scaffolds deterministic structure; prompts in `.github/prompts/` constrain probabilistic generation; 105+ community extensions. |

**Strengths:** Mature templates, strong constitution pattern, clearest linear SDD path.  
**Weaknesses:** Linear flow can feel heavy for small changes; less native worktree/lane isolation than Spec Kitty.

---

### GSD (Get Sh*t Done)

| Dimension | Detail |
|-----------|--------|
| **Core artifacts** | `.planning/` root: `PROJECT.md`, `REQUIREMENTS.md` (REQ-XX), `ROADMAP.md`, `STATE.md`, `config.json`; per-phase `CONTEXT.md`, `RESEARCH.md`, `PLAN.md`, `SUMMARY.md`, `VERIFICATION.md`; spikes/sketches subdirs; atomic git commits per task. |
| **Lifecycle stages** | **Per phase:** Discuss → Plan → Execute → Verify → Ship. **New project:** questions → research (4 parallel agents) → synthesis → requirements → roadmap. Quick mode skips ceremony for ad-hoc tasks. |
| **Gates / checkpoints** | Plan checker validates 8 dimensions (loop ≤3×). Optional post-execution verifier (`VERIFICATION.md`). Manual UAT in verify-work with auto-diagnosis. Atomic commits enable rollback. |
| **Traceability model** | REQ-XX → roadmap phases → PLAN must-haves → SUMMARY outcomes → VERIFICATION pass/fail. Nyquist validation layer maps test coverage. STATE.md persists decisions across sessions. |
| **Roles** | Thin orchestrator; fresh-context sub-agents (researcher, planner, checker, executor, verifier). Human owns discuss and verify stages. |
| **AI-DD fit** | ★★★ — Meta-prompting framework explicitly solving context rot; 14+ agent runtime integrations; sub-agent isolation is best-in-class for long-horizon agent work. |

**Strengths:** Context engineering, parallel execution waves, session-persistent STATE.  
**Weaknesses:** `.planning/` convention not universal; less PM dashboard than Spec Kitty; governance is project-local not org-wide.

---

### Spec Kitty

| Dimension | Detail |
|-----------|--------|
| **Core artifacts** | `kitty-specs/<feature>/` (`meta.json`, `spec.md`, `plan.md`, `tasks.md`, `wps.yaml`, `research.md`, checklists); `.kittify/` templates and missions; `.worktrees/` execution workspaces; optional `constitution.md`. |
| **Lifecycle stages** | Specify → Plan → (Research) → Tasks → Implement → Review → Accept → Merge. Kanban lanes: planned, claimed, in_progress, for_review, done, blocked, canceled. |
| **Gates / checkpoints** | Spec acceptance before implementation fan-out. WP lane transitions enforced. `spec-kitty accept` and merge helpers. Dashboard for live visibility. |
| **Traceability model** | Implementation Concern Map (IC-##) in plan → `plan_concern_refs` in `wps.yaml` → task prompts. Mission-scoped templates. Worktree isolation per lane. |
| **Roles** | Delivery control plane for mixed human/agent teams; 12 agent integrations; local-first CLI + dashboard. |
| **AI-DD fit** | ★★★ — AgilePlus already uses `kitty-specs/`; strongest git-worktree + WP model; explicit accept/merge governance. |

**Strengths:** Parallel lanes, WP granularity, team-visible delivery state, merge workflow.  
**Weaknesses:** Python CLI dependency; overlap with Spec-Kit artifact names requires convention discipline.

---

### BMAD Method

| Dimension | Detail |
|-----------|--------|
| **Core artifacts** | `_bmad-output/`: `PRD.md`, `architecture.md`, `project-context.md`, `epics.md`, sharded docs, `{epic}.{story}.story.md`, `sprint-status.yaml`, UX specs. |
| **Lifecycle stages** | **Phase 1 — Analysis:** brainstorming, product brief. **Phase 2 — Planning:** PRD, UX. **Phase 3 — Solutioning:** architecture, epics/stories. **Phase 4 — Implementation:** sprint planning, dev story, code review, QA. Scale-adaptive depth (bug fix → enterprise). |
| **Gates / checkpoints** | Menu-driven agent pauses at decision points. SM creates story gate before dev. QA validates against PRD. `bmad-shard-doc` when context limits hit. |
| **Traceability model** | Explicit chain: PRD → architecture → epics → stories → code → QA sign-off. `project-context.md` as coding constitution for all agents. |
| **Roles** | 12+ specialized personas (PM John, Architect Winston, Dev Amelia, SM Bob, QA Quinn, UX Sally, …). Party Mode for multi-persona sessions. Module ecosystem (BMM, TEA, BMGD, CIS). |
| **AI-DD fit** | ★★★ — Enterprise-grade agent roleplay; context engineering between phases; `/bmad-help` intelligent routing. |

**Strengths:** Full SDLC coverage, enterprise scale-adaptive planning, QA module (TEA).  
**Weaknesses:** Ceremony-heavy for small tasks; artifact sprawl without strict ID schema unless configured.

---

### Other AI-DD Processes (condensed)

| Process | Artifacts | Stages | Gates | Traceability | AI-DD fit |
|---------|-----------|--------|-------|--------------|-----------|
| **AIDE** | 7 artifact types across full lifecycle | 7 linear steps | Per-step approval | Step chain | ★★★ |
| **Canon** | Baseline, drift report | Spec-first / code-first / drift | Drift threshold | Baseline diff | ★★☆ |
| **Product Forge** (Spec-Kit) | PM-oriented specs, roadmaps | PM-spec → dev handoff | PM review | Feature → epic | ★★☆ |
| **MAQA** (Spec-Kit) | Multi-agent QA reports | Implement → multi-agent QA | QA gate before merge | Test ↔ spec | ★★★ |
| **Superpowers** | Plan markdown, skill outputs | Brainstorm → plan → execute → verify | TDD + review subagent | Task ↔ commit | ★★★ |
| **AgilePlus native** | FR/NFR, kitty-specs, trace.json, worklogs | Specify → WP → gate → PR | CI quality gate + trace-validator | 5-layer FR graph | ★★★ |
| **Ralph / AI-RPI loops** | Prompt, logs | Generate ↔ test loop | Tests green | Implicit via tests | ★★☆ |
| **Karpathy Skills** | SKILL.md | On invoke | Author-defined | None formal | ★★☆ |

---

## Part II — Traditional Software Engineering Frameworks

### Summary Matrix

| Framework | Core artifacts | Lifecycle stages | Gates / checkpoints | Traceability model | Roles | AI-DD fit |
|-----------|----------------|------------------|---------------------|----------------------|-------|-----------|
| **Scrum** | Product backlog, sprint backlog, increment, DoD, burndown | Backlog refine → Sprint plan → Daily → Review → Retro (repeat) | Sprint boundary; DoD for increment; PO acceptance | PB item → sprint item → increment; user story mapping | PO, SM, Dev Team | ★★☆ |
| **Kanban (SWE)** | Kanban board, WIP limits, cycle-time metrics, service classes | Pull flow: requested → in progress → done (continuous) | WIP limits; explicit policies per column; classes of service | Card ID → commit/PR (tool-dependent) | Team owns flow; optional service manager | ★★☆ |
| **SAFe** | Portfolio epics, ARTs, PI objectives, program backlog, enablers | Portfolio → Program Increment (PI) → Iteration → Release (4–12 week PI) | PI Planning gate; WSJF prioritization; MVP / release gate | Epic → feature → story → task; hierarchical ALM | RTE, PO, SM, System Architect, Business Owner | ★☆☆ |
| **XP** | User stories, acceptance tests, task board | Plan → test-first → pair → integrate → release (1–3 week cycles) | All tests green; continuous integration; customer acceptance | Story → acceptance test → code | Customer, Dev, Coach | ★★☆ |
| **Waterfall** | BRD, SRS, design doc, test plan, release notes | Requirements → Design → Implement → Verify → Maintain (sequential) | Phase-exit reviews; sign-off per document | Req ID → design section → test case → code module | BA, Architect, Dev, QA, PM (separate) | ★☆☆ |
| **RUP / UP** | Vision, use-case model, Glossary, SAD, test cases, iteration plan | Inception → Elaboration → Construction → Transition (iterations within) | Lifecycle milestones; architecture baseline at elaboration exit | Use case ↔ classes ↔ tests (trace matrix in tools) | Analyst, Architect, Developer, Tester, PM | ★☆☆ |

---

### Scrum

| Dimension | Detail |
|-----------|--------|
| **Core artifacts** | Product Backlog, Sprint Backlog, Increment (potentially shippable), Definition of Done, optionally Sprint Goal and burndown/burnup charts. |
| **Lifecycle stages** | Continuous product discovery/refinement; fixed-length sprints: planning → daily scrum → development → review → retrospective. |
| **Gates / checkpoints** | Sprint timebox; DoD checklist for increment; PO accepts or rejects backlog items. |
| **Traceability model** | Story/task IDs in ALM tools; weak native link to code unless enforced (tags, PR templates). |
| **Roles** | Product Owner (what), Scrum Master (process), Developers (how). |
| **AI-DD fit** | ★★☆ — Agents can implement sprint items if specs exist; Scrum itself doesn't define spec artifacts. Maps well to Spec Kitty WPs as sprint backlog items. |

---

### Kanban (Software)

| Dimension | Detail |
|-----------|--------|
| **Core artifacts** | Kanban board, WIP limits, explicit policies, cycle/lead time, throughput, Cumulative Flow Diagram. |
| **Lifecycle stages** | Continuous flow; no prescribed sprints. Work pulled when capacity available. |
| **Gates / checkpoints** | WIP limit enforcement; pull criteria per column; SLA classes (expedite, fixed date, standard, intangible). |
| **Traceability model** | Card → branch/PR when integrated with dev tools; metrics-based not requirements-ID-based. |
| **Roles** | Self-organizing team; optional Kanban cadences (replenishment, delivery, risk). |
| **AI-DD fit** | ★★☆ — Spec Kitty lanes and GSD phase status are Kanban-compatible; agents fill "in progress" columns. |

---

### SAFe (Scaled Agile Framework)

| Dimension | Detail |
|-----------|--------|
| **Core artifacts** | Portfolio canvas, epics, capabilities, features, stories; PI Objectives; ART backlog; enabler epics; Solution Intent (specifications at scale). |
| **Lifecycle stages** | Portfolio strategy → PI Planning (8–12 weeks) → iteration execution → Inspect & Adapt → release. |
| **Gates / checkpoints** | PI Planning commitment; WSJF prioritization; architectural runway; MVP milestones; release approval. |
| **Traceability model** | Hierarchical ALM (epic → feature → story); Solution Intent for fixed/variable requirements at scale. |
| **Roles** | Business Owner, RTE, PO, SM, System Architect, Agile Teams. |
| **AI-DD fit** | ★☆☆ — Heavy ceremony; AI assists at story level. BMAD epics/stories map conceptually to SAFe features/stories. |

---

### Extreme Programming (XP)

| Dimension | Detail |
|-----------|--------|
| **Core artifacts** | User stories, acceptance tests, unit tests, task cards, release plan. |
| **Lifecycle stages** | Short release cycles; inner loop: write test → code → refactor → integrate. |
| **Gates / checkpoints** | All tests pass (CI); pair review implicit; customer demo acceptance. |
| **Traceability model** | Story → acceptance test → unit tests; strongest in TDD shops. |
| **Roles** | Customer (on-site preferred), Developers, Coach. |
| **AI-DD fit** | ★★☆ — Superpowers TDD skill and GSD verification align with XP test-first ethos; agents excel at test generation. |

---

### Waterfall

| Dimension | Detail |
|-----------|--------|
| **Core artifacts** | Business Requirements Document, Software Requirements Specification, High/Low Level Design, Test Plan, Test Reports, User Manuals. |
| **Lifecycle stages** | Requirements → System Design → Implementation → Integration & Testing → Deployment → Maintenance (strict sequence). |
| **Gates / checkpoints** | Phase-exit reviews; stakeholder sign-off before next phase; change control board for scope changes. |
| **Traceability model** | Requirements traceability matrix (RTM): Req ID → design → code → test case (often tool-managed, e.g., DOORS). |
| **Roles** | Distinct BA, Architect, Developer, QA, PM — handoffs between phases. |
| **AI-DD fit** | ★☆☆ — Agents can draft SRS/RTM but process assumes document-complete phases; poor fit for iterative agent loops. |

---

### RUP / Unified Process

| Dimension | Detail |
|-----------|--------|
| **Core artifacts** | Vision document, Use-Case Model, Supplementary Specifications, Software Architecture Document, Iteration Plan, Test Model. |
| **Lifecycle stages** | Inception (vision) → Elaboration (architecture baseline) → Construction (iterative builds) → Transition (release). Iterations within phases. |
| **Gates / checkpoints** | Lifecycle milestones (LCO, LCA, IOC, OR); architecture baseline before construction; iteration assessment. |
| **Traceability model** | Use case ↔ realizations ↔ test cases; trace matrices in Rose/DOORS-style tools. |
| **Roles** | Analyst, Architect, Developer, Tester, Project Manager (RUP role definitions). |
| **AI-DD fit** | ★☆☆ — Use-case rigor valuable as spec input; ceremony exceeds typical AI-DD velocity. |

---

## Part III — Project / Product / General Management Frameworks

### Summary Matrix

| Framework | Core artifacts | Lifecycle stages | Gates / checkpoints | Traceability model | Roles | AI-DD fit |
|-----------|----------------|------------------|---------------------|----------------------|-------|-----------|
| **PMBOK (7th ed.)** | Project charter, scope/WBS, schedule, budget, risk register, deliverables, lessons learned | Initiating → Planning → Executing → Monitoring & Controlling → Closing | Phase/gate reviews; change control; acceptance of deliverables | WBS ID → work package → deliverable; benefits linkage | PM, Sponsor, Stakeholders, Team | ★☆☆ |
| **PRINCE2** | Business case, PID, stage plans, RAID log, end-stage reports | Starting → Initiating → Stage control (repeat) → Closing | Stage boundaries; exception process; highlight reports | Product-based planning: product description → quality criteria | Project Board, PM, Team Manager | ★☆☆ |
| **OKRs** | Objectives, Key Results (metrics), check-ins | Set (annual/quarterly) → Track (weekly/monthly) → Score/Reset | Mid-quarter review; KR measurability gate | Objective → KR metric → initiative/project (optional) | Owner per O/KR; leadership alignment | ★★☆ |
| **Shape Up (Basecamp)** | Pitch, bet, appetite, circuit, scope map, hill chart | Shaping (6 weeks) → Betting (cool-down) → Building (6 weeks) → Cool-down | Betting table gate; fixed appetite; scope hammering | Pitch → bet → tasks on hill chart (not story backlog) | Shapers, Builders, Betting Table (management) | ★★☆ |
| **Lean (product)** | Value stream map, hypothesis, MVP, metrics | Build → Measure → Learn (loop); eliminate waste | Pivot/persevere decision; validated learning | Hypothesis → experiment → metric | Product team, no fixed roles | ★★☆ |
| **Six Sigma (DMAIC)** | SIPOC, VOC, CTQ, statistical process data, control plan | Define → Measure → Analyze → Improve → Control | Tollgate reviews per phase; statistical significance | CTQ ↔ process step ↔ measurement | Black Belt, Green Belt, Champion | ☆☆☆ |
| **GTD** | Inbox, next actions, projects, contexts, weekly review | Capture → Clarify → Organize → Reflect → Engage | Weekly review; 2-minute rule; project = outcome + next action | Project ↔ next actions (personal, not team RTM) | Individual knowledge worker | ★☆☆ |
| **Kanban-PM (Personal/Team)** | Kanban board, WIP, commitment point | Visualize → Limit WIP → Manage flow → Make policies explicit → Improve | WIP limits; replenishment meeting | Card → outcome (lightweight) | Individual or team | ★★☆ |

---

### PMBOK

| Dimension | Detail |
|-----------|--------|
| **Core artifacts** | Charter, scope statement, WBS, schedule baseline, cost baseline, risk register, stakeholder register, deliverable acceptance records. |
| **Lifecycle stages** | Performance domains replace rigid 5 groups in PMBOK 7, but classic: Initiating → Planning → Executing → M&C → Closing. |
| **Gates / checkpoints** | Gate reviews at phase boundaries; formal change control; deliverable acceptance. |
| **Traceability model** | WBS decomposition; requirements → deliverables; benefits realization (post-project). |
| **Roles** | Project Manager central; Sponsor accountable; functional managers provide resources. |
| **AI-DD fit** | ★☆☆ — Strong for charter/scope/risk artifacts agents can draft; weak for iterative agent coding loops. |

---

### PRINCE2

| Dimension | Detail |
|-----------|--------|
| **Core artifacts** | Business Case, Project Initiation Document (PID), Stage Plans, Work Packages, End Stage Reports, Lessons Log, RAID. |
| **Lifecycle stages** | Starting Up → Initiating → Controlling a Stage (repeat) → Managing Product Delivery → Closing. |
| **Gates / checkpoints** | Stage boundary approval by Project Board; tolerance thresholds trigger exception process. |
| **Traceability model** | Product descriptions with quality criteria; work package → product. |
| **Roles** | Project Board (Executive, Senior User, Senior Supplier), PM, Team Manager. |
| **AI-DD fit** | ★☆☆ — Governance vocabulary useful for enterprise; heavy for AI-native teams. |

---

### OKRs

| Dimension | Detail |
|-----------|--------|
| **Core artifacts** | Objectives (qualitative), Key Results (measurable), optional Initiatives; check-in notes. |
| **Lifecycle stages** | Annual/strategic OKRs → quarterly cadence → weekly check-ins → end-of-quarter scoring (0.0–1.0). |
| **Gates / checkpoints** | KR must be measurable; mid-quarter adjustment; avoid binary grading culture. |
| **Traceability model** | O → KR → initiative/project/epic (manual mapping); aligns portfolio to outcomes not outputs. |
| **Roles** | OKR owner; leadership sets company OKRs; teams cascade or align. |
| **AI-DD fit** | ★★☆ — KRs can reference delivery metrics (trace coverage, cycle time); agents don't natively "do OKRs" but roadmap phases map to Initiatives. |

---

### Shape Up (Basecamp)

| Dimension | Detail |
|-----------|--------|
| **Core artifacts** | Pitch (problem + appetite + solution sketch), Bet, Circuit (cool-down discoveries), Scope map, Hill chart (figured out vs. execution). |
| **Lifecycle stages** | **Shaping** (senior, no execution) → **Betting Table** → **Building** (fixed cycle, typically 6 weeks) → **Cool-down** (2 weeks). |
| **Gates / checkpoints** | Betting table selects pitches; fixed appetite caps scope; scope hammering during build; no backlogs. |
| **Traceability model** | Pitch → bet → hill scopes; intentional rejection of fine-grained RTM. |
| **Roles** | Shapers (design pitches), Builders (implement), Betting Table (commit). |
| **AI-DD fit** | ★★☆ — Appetite maps to GSD phase sizing; pitches resemble OpenSpec proposals; anti-backlog fits agent quick mode. |

---

### Lean (Startup / Product)

| Dimension | Detail |
|-----------|--------|
| **Core artifacts** | Business Model Canvas, Lean Canvas, hypothesis statements, MVP, innovation accounting metrics, pivot/persevere memo. |
| **Lifecycle stages** | Build → Measure → Learn loop; validated learning over feature factory. |
| **Gates / checkpoints** | Experiment result gate; pivot/persevere decision; vanity vs. actionable metrics distinction. |
| **Traceability model** | Hypothesis → experiment → metric (learning trace, not code trace). |
| **Roles** | Cross-functional product team; no prescribed titles. |
| **AI-DD fit** | ★★☆ — Agents accelerate MVP build; Lean validates *what* to build; pairs with BMAD analysis phase. |

---

### Six Sigma (DMAIC)

| Dimension | Detail |
|-----------|--------|
| **Core artifacts** | SIPOC diagram, Voice of Customer, CTQ tree, measurement system analysis, control charts, control plan. |
| **Lifecycle stages** | Define → Measure → Analyze → Improve → Control. |
| **Gates / checkpoints** | Tollgate review at each phase; statistical proof of improvement; control plan handoff to operations. |
| **Traceability model** | CTQ ↔ process step ↔ measurement system; designed for manufacturing/service processes. |
| **Roles** | Executive Champion, Master Black Belt, Black Belt, Green Belt, process owner. |
| **AI-DD fit** | ☆☆☆ — Quality gate *concept* aligns with AgilePlus CI gates; statistical DMAIC mismatched to software spec loops. |

---

### GTD (Getting Things Done)

| Dimension | Detail |
|-----------|--------|
| **Core artifacts** | Inbox, next-action lists, project list, waiting-for, someday/maybe, calendar, weekly review checklist. |
| **Lifecycle stages** | Capture → Clarify (is it actionable?) → Organize → Reflect (weekly review) → Engage. |
| **Gates / checkpoints** | Weekly review; 2-minute rule for immediate actions; project defined as outcome requiring >1 step. |
| **Traceability model** | Personal productivity links; no team requirements matrix. |
| **Roles** | Individual practitioner. |
| **AI-DD fit** | ★☆☆ — Agent task lists resemble next-actions; GTD doesn't scale to team traceability. Useful for human operator hygiene alongside GSD STATE.md. |

---

### Kanban-PM

| Dimension | Detail |
|-----------|--------|
| **Core artifacts** | Visual board, WIP limits, explicit policies, service delivery metrics. |
| **Lifecycle stages** | Continuous flow; cadences for replenishment and delivery planning. |
| **Gates / checkpoints** | WIP limit as primary constraint; definition of workflow per column. |
| **Traceability model** | Lightweight; outcome per card. |
| **Roles** | Team-managed; service delivery manager optional. |
| **AI-DD fit** | ★★☆ — Direct mapping to Spec Kitty dashboard lanes and GitHub Projects; natural visualization layer for agent WPs. |

---

## Part IV — Synthesis

### 4.1 The Common Spine

Every framework — from Waterfall RTM to OpenSpec deltas — implements variations of one delivery spine:

```text
INTENT → SPEC → PLAN → EXECUTE → VERIFY → EVIDENCE
   │        │      │        │         │         │
   │        │      │        │         │         └─ audit log, tests, trace.json, merge record
   │        │      │        │         └─ DoD, acceptance, verification.md, QA gate
   │        │      │        └─ code, increment, atomic commits, WPs
   │        │      └─ tasks, WBS, stories, PLAN.md, architecture
   │        └─ requirements, spec.md, PRD, use cases, delta specs
   └─ charter, pitch, objective, problem statement, constitution
```

**Cross-framework invariant:** durable artifacts at each hop beat chat-only intent. AI-DD frameworks differ mainly in *how strictly* they enforce hop order and *where* artifacts live (repo-native vs. ALM vs. agent session).

| Spine stage | Strongest sources |
|-------------|-------------------|
| **Intent** | OKRs (outcome), Shape Up pitches (appetite), Lean hypothesis, BMAD analysis |
| **Spec** | Spec-Kit constitution + spec.md, OpenSpec delta specs, Spec Kitty IC-## concerns, Waterfall SRS |
| **Plan** | GSD PLAN.md + checker, Spec-Kit plan.md, BMAD architecture, SAFe PI objectives |
| **Execute** | Spec Kitty worktrees + WPs, GSD parallel waves, XP/TDD, Scrum sprint backlog |
| **Verify** | GSD VERIFICATION.md, AgilePlus trace-validator, XP acceptance tests, Six Sigma control (concept) |
| **Evidence** | AgilePlus trace.json + worklogs, atomic git commits (GSD), PR merge (all git-native) |

---

### 4.2 Where Each Family Is Strongest

| Family | Peak capability | Typical failure mode |
|--------|-----------------|----------------------|
| **AI-DD / Spec-driven** | Repo-native agent context, rapid iteration, brownfield deltas | Tool fragmentation; overlapping conventions (`specs/` vs `kitty-specs/` vs `.planning/`) |
| **Traditional SWE** | Team cadence, role clarity, proven scale patterns (SAFe) | Underspecified artifacts for agents; weak machine-readable trace |
| **PM / Product** | Outcome alignment, portfolio governance, scope/time boxing | Output-not-outcome drift; documents disconnected from code |

**AI-DD leaders by concern:**

| Concern | Best-in-class |
|---------|---------------|
| Brownfield change isolation | OpenSpec (delta specs) |
| Linear SDD discipline | GitHub Spec-Kit |
| Context rot / long-horizon agents | GSD |
| Parallel delivery + merge governance | Spec Kitty |
| Enterprise role coverage | BMAD |
| Machine-verifiable FR trace | AgilePlus + Tracera (trace.json, TraceLink graph) |

**Traditional leaders by concern:**

| Concern | Best-in-class |
|---------|---------------|
| Team cadence | Scrum |
| Flow efficiency | Kanban |
| Portfolio scale | SAFe |
| Quality via tests | XP |
| Compliance RTM | Waterfall / RUP |
| Time-boxed commitment | Shape Up |

---

### 4.3 Recommended Unified Process Model (AgilePlus + Tracera)

A merged operating model should **not** pick one framework wholesale. It should compose a **layered stack**:

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

#### Unified lifecycle (single spine)

| Stage | Unified name | Primary artifacts | Gate | Tooling bias |
|-------|--------------|-------------------|------|--------------|
| 1 | **Charter** | OKR/initiative link, pitch or `proposal.md`, constitution | Problem + appetite approved | Shape Up / OpenSpec propose |
| 2 | **Specify** | `kitty-specs/<id>/spec.md`, FR/NFR IDs, acceptance criteria | Spec review accepted (Spec Kitty accept) | Spec Kitty / Spec-Kit |
| 3 | **Plan** | `plan.md`, IC-## map, `architecture.md` or `design.md` | Plan checker or architect sign-off | GSD planner / BMAD Winston |
| 4 | **Decompose** | `tasks.md`, `wps.yaml`, REQ-XX or WP IDs | WIP/lane capacity available | Spec Kitty / GSD |
| 5 | **Execute** | Code in `.worktrees/`, atomic commits | DoD per WP; no `--no-verify` | Agent + local hooks |
| 6 | **Verify** | Tests, `VERIFICATION.md`, trace-validator pass | CI quality gate green | AgilePlus gates + GSD verifier |
| 7 | **Evidence** | `trace.json`, Tracera TraceLink, worklog, merged PR | Trace coverage ≥ threshold | Tracera + agileplus-trace |
| 8 | **Archive** | Delta merged to main specs, phase SUMMARY, retro notes | Archive / close lane | OpenSpec archive / GSD ship |

#### Traceability union (AgilePlus ∩ Tracera)

| Layer | AgilePlus | Tracera | Unified rule |
|-------|-----------|---------|----------------|
| Requirement ID | FR-xxx, NFR-xxx | TraceLink node | Single canonical ID namespace |
| Spec | kitty-specs | — | Spec is source of intent |
| Design | plan.md IC-## | TraceLink edge (implements) | IC-## ↔ WP ↔ module |
| Code | anchor comments | confidence-scored link | Validator + graph projection |
| Test | test name in trace.json | TraceLink edge (verifies) | Every new function: test or explicit waiver |
| Evidence | worklog JSON, PR | audit/event store | Hash-chained append-only log (ADR-004) |

#### Role model (minimum viable)

| Role | Responsibility | Framework source |
|------|----------------|------------------|
| **Outcome Owner** | OKR/KR alignment, betting approval | OKRs, Shape Up |
| **Spec Owner** | spec.md acceptance, IC-## completeness | Spec Kitty PO analog |
| **Architect** | constitution, plan.md, ADRs | Spec-Kit, BMAD |
| **Agent Operator** | WP execution in worktree, atomic commits | GSD executor |
| **Verifier** | trace-validator, CI, QA against spec | AgilePlus, XP |
| **Trace Curator** | TraceLink graph health, impact analysis | Tracera |

#### AI-DD fit of the unified model: ★★★

The unified model is agent-native because:

1. **Repo-native artifacts** — no ALM-only specs; agents read/write markdown + YAML in git.
2. **Worktree isolation** — Spec Kitty lanes prevent agent cross-contamination.
3. **Fresh-context delegation** — GSD-style sub-agents for research/plan/verify; thin human session.
4. **Delta specs for brownfield** — OpenSpec pattern for mature AgilePlus codebase.
5. **Machine gates** — trace-validator, lefthook, and Tracera links replace trust-me PRs.
6. **Scale-adaptive ceremony** — BMAD depth for epics; GSD quick mode for chores; Shape Up appetite caps planning time.

#### Anti-patterns to avoid in merge

| Anti-pattern | Why | Mitigation |
|--------------|-----|------------|
| Triple spec roots (`specs/`, `kitty-specs/`, `.planning/`) | Agent context fragmentation | Single canonical root: `kitty-specs/` with OpenSpec deltas nested or linked |
| Chat-only intent | Untraceable drift | Every feature: charter artifact before WP claim |
| SAFe ceremony on 1-dev agent loops | Velocity collapse | Use SAFe vocabulary at portfolio only; Spec Kitty at execution |
| Waterfall phase gates on every bugfix | Blocking | GSD quick mode + OpenSpec fluid apply for small changes |
| Evidence after merge | Unrecoverable audit | trace.json required in WP branch before `for_review` |

---

### 4.4 Framework Selection Guide (by change type)

| Change type | Recommended primary framework | Supporting layers |
|-------------|------------------------------|-------------------|
| Bug fix / chore | GSD quick mode or OpenSpec delta | L0 evidence only |
| Single feature (greenfield) | Spec Kitty full lane | Spec-Kit constitution, GSD verify |
| Brownfield refactor | OpenSpec explore + apply | Tracera impact analysis |
| Enterprise epic | BMAD PRD → epics → stories | SAFe PI alignment (L4), Spec Kitty WPs |
| Portfolio initiative | OKRs + Shape Up pitch | BMAD analysis, AgilePlus charter |
| Compliance-heavy | Waterfall RTM vocabulary on unified spine | Tracera graph, FR-024 gates |

---

## References

| Source | URL / location |
|--------|----------------|
| OpenSpec | https://openspec.dev/ · https://github.com/Fission-AI/OpenSpec |
| GitHub Spec-Kit | https://github.github.io/spec-kit/ |
| GSD | https://github.com/gsd-build/get-shit-done · https://github.com/open-gsd/gsd-core |
| Spec Kitty | https://spec-kitty.ai/ · https://github.com/Priivacy-ai/spec-kitty |
| BMAD Method | https://github.com/bmad-code-org/BMAD-METHOD |
| AgilePlus AI-DD governance | `docs/ai-dd-governance.md` |
| AgilePlus traceability | `docs/TRACEABILITY_MATRIX.md`, ADR-004 |
| Tracera FR reference | `docs/requirements/tracera-frnfr.md` |
| Shape Up | Ryan Singer, *Shape Up* (Basecamp) |
| Scrum Guide | scrumguides.org |
| SAFe | scaledagileframework.com |
| PMBOK / PRINCE2 | PMI / AXELOS standard references |

---

*Document version: 1.0 — harmonize/framework-analysis — 2026-06-25*
