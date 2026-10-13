# Emergent Garden Nested Corpus — Wave 1 Portfolio Applicability

**Campaign:** `eg-nested-corpus-2026-09`  
**Wave:** 1  
**Status:** evidence-gated applicability map; no product-code authorization

This document maps Wave 1 findings against repositories as they currently describe themselves. A conceptual resemblance is not sufficient. Every positive mapping must identify a mechanism, a real portfolio problem, an owner, an experiment or document change, and evidence that could reject the mapping.

## 1. Classification vocabulary

| Class                       | Meaning                                                                                |
| --------------------------- | -------------------------------------------------------------------------------------- |
| `DIRECTLY_ADOPT`            | The repository already owns a concern needed to operationalize the finding             |
| `ARCHITECTURAL_ANALOGUE`    | The finding clarifies an existing role or boundary but does not mandate implementation |
| `EXPERIMENT`                | A controlled test is warranted before architecture or product change                   |
| `RESEARCH_LEAD`             | Worth preserving centrally; project fanout is premature                                |
| `PHILOSOPHICAL_CONVERGENCE` | Shared design worldview with no immediate product action                               |
| `CONTRADICTION`             | The corpus exposes a current claim, architecture, or process tension                   |
| `NOT_APPLICABLE`            | No material project relationship established                                           |
| `ALREADY_IMPLEMENTED`       | The relevant mechanism is already materially present                                   |
| `SUPERSEDED_BY_PORTFOLIO`   | Portfolio practice is already more rigorous or specific                                |
| `INSUFFICIENT_EVIDENCE`     | Similarity exists, but source or repository evidence is too weak                       |

## 2. Portfolio-wide decisions

### Adopt now as research/governance contracts

1. **Version the whole evaluated system.** Model, prompts, tools, observation/action schemas, environment, evaluator, budgets, and coordination topology are one experimental configuration.
2. **Measure agent-count scaling rather than assuming it.** At minimum evaluate 1, 2, 3, and 5 agents on matched tasks and total resource budgets.
3. **Separate planner, observer, synchronizer, actuator, and evaluator failures.** “The agent failed” is not a useful root cause.
4. **Preserve incumbent and rollback evidence.** Autonomous improvement needs candidate lineage, rejected runs, and exact evaluator versions.
5. **Treat negative results as durable research.** Vision that does not help, communication that hurts, and additional agents that regress are first-class outputs.
6. **Require hard oracles beside model judges.** Soft assessment alone cannot distinguish a persuasive narrative from correct behavior.
7. **Make HITL optionality explicit.** Human inspection/approval/repair points must be typed control surfaces, not invisible rescue dependencies.
8. **Bound open-ended loops.** WIP, action, time, token, cost, and mutation budgets are architecture, not operational afterthoughts.

### Do not adopt from Wave 1

- “Decentralize everything.”
- “More agents are better.”
- “Natural selection removes the need for product objectives.”
- “Vision is unnecessary.”
- “State machines are generally better than neural or language models.”
- “Recursive self-improvement has been demonstrated in the strong sense.”
- “Computational irreducibility makes specifications or formal reasoning pointless.”
- “Every repo needs an artificial-life metaphor.”

## 3. Repository relevance matrix

| Repository                      | Current observed role                                                                                   | Classification                             |  Confidence | Wave 1 action                                                                                                                                        |
| ------------------------------- | ------------------------------------------------------------------------------------------------------- | ------------------------------------------ | ----------: | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ResearchLedger`                | Local-first source, provenance, claim, retrieval, and evidence store                                    | `DIRECTLY_ADOPT` + `ALREADY_IMPLEMENTED`   |        high | Extend current source/version/link/crawl substrate for typed nested corpora; preserve full raw corpus locally and Git-safe projections separately    |
| `RepoLedger`                    | Fleet repository/authority/projection ledger                                                            | `DIRECTLY_ADOPT`                           |        high | Register campaign snapshot and every downstream projection; do not duplicate source text                                                             |
| `Benchora`                      | Benchmarking, baselines, regressions, mutation coverage                                                 | `DIRECTLY_ADOPT`                           |        high | Own coordination curves, evaluator robustness, held-out tests, and cost/performance comparisons                                                      |
| `phenotype-journeys`            | User/agent journey recording, hard assertions, visual evidence                                          | `DIRECTLY_ADOPT`                           |        high | Own challenge-world and GUI/CLI trajectory manifests with hard oracles                                                                               |
| `SessionLedger`                 | Lossless agent-session capture/archive/replay                                                           | `DIRECTLY_ADOPT`                           |        high | Preserve session/action/config timelines for irreducible and long-running experiments                                                                |
| `Tracera`                       | Trace, observability, audit, and evidence links                                                         | `DIRECTLY_ADOPT`                           |        high | Model claim → config → action → state → evaluator → promotion/rollback links                                                                         |
| `AgilePlus`                     | Specification, work-package, and governance workflow                                                    | `DIRECTLY_ADOPT`                           |        high | Represent experiments and evidence gates as bounded work packages; no prose completion percentages                                                   |
| `PhenoObservability`            | Instrumentation libraries                                                                               | `ARCHITECTURAL_ANALOGUE`                   | medium-high | Define instrumentation profile for agent/environment/evaluator boundaries after owner audit                                                          |
| `Agentora`                      | Rust agent framework with tools, skills, memory, and lifecycle events                                   | `EXPERIMENT` + `CONTRADICTION`             |        high | Add benchmark contracts for budgets, replay, action authorization, state freshness, and multi-agent coordination before claiming framework advantage |
| `thegent`                       | Broad orchestration/bootstrap/governance/runtime umbrella                                               | `EXPERIMENT` + `CONTRADICTION`             |        high | Measure WIP/coordination and decompose generic authority; avoid one-agent-per-repo fanout                                                            |
| `helios-cli`                    | Codex fork plus queue/rollback/scaling/verification harnesses                                           | `EXPERIMENT` + `ALREADY_IMPLEMENTED`       |        high | Test deterministic primitive reliability, state freshness, rollback, and agent-count scaling using existing harness crates                           |
| `forgecode`                     | Tailcall forgecode fork, session/search/compression additions, disputed `helioslite` identity           | `CONTRADICTION`                            |        high | Do not fan out corpus conclusions until canonical identity and nonexistent/uncertain successor claims are resolved                                   |
| `HeliosLab`                     | Current README says config/flags/secrets/version workspace; accepted intent is desktop coding workbench | `CONTRADICTION`                            |        high | Identity forensics first; no emergence-driven feature work until product role is repaired                                                            |
| `Civis`                         | Deterministic emergent-civilization simulation and godgame                                              | `EXPERIMENT` + `PHILOSOPHICAL_CONVERGENCE` |        high | Use corpus to sharpen emergence evidence, intervention design, replay, and anti-handwaving tests; verify current feature claims independently        |
| `hwLedger`                      | Hardware/system evidence ledger and physical-compute planning                                           | `RESEARCH_LEAD`                            |      medium | Apply observer/actuator/state-freshness and closed-loop evidence contracts to physical-engineering work                                              |
| `Eidolon` / `PlayCua`           | Device/sandbox/automation surfaces                                                                      | `EXPERIMENT`                               |      medium | Build actuator-reliability and privileged-state-vs-human-interface benchmark classes                                                                 |
| `PhenoSpecs`                    | Cross-repo spec/ADR spine, but current instructions restrict new content                                | `CONTRADICTION`                            |        high | Resolve authority conflict before publishing corpus-derived cross-repo contracts here                                                                |
| `PhenoHandbook`                 | Patterns/anti-patterns reference                                                                        | `RESEARCH_LEAD`                            |      medium | Publish only patterns that survive experiments and accepted ADRs; no first-wave philosophy dump                                                      |
| `phenodocs` / profile / landing | Generated narrative/catalog surfaces                                                                    | `NOT_APPLICABLE` as authority              |        high | Generate projections only after canonical evidence and repo decisions exist                                                                          |

## 4. Detailed repository decisions

### 4.1 ResearchLedger

**Observed fit:** ResearchLedger already stores deterministic source documents, content versions, chunks, full-text indexes, provenance, claims with source spans, document links, reference-fetch jobs, crawl runs, leases, and local Markdown/SQLite state.

**Class:** `DIRECTLY_ADOPT` and partially `ALREADY_IMPLEMENTED`.

**Wave 1 requirement:** Extend, do not replace, the existing substrate.

Required additions:

- explicit corpus campaign/snapshot identity;
- typed source-node and source-edge records;
- immutable source-version evidence on every claim;
- transcript/script acquisition and permission class;
- deterministic frontier score and stop decision;
- concept aliases/occurrences and contradiction relations;
- applicability and one-way projection records;
- temporary YouTube API-cache expiry/deletion audit;
- Git-safe publication transform.

**Counterfactual:** A static Markdown research folder might be enough.  
**Why rejected provisionally:** the campaign needs incremental refresh, version-specific claims, bounded recursion, graph impact propagation, and downstream staleness. Markdown remains the human projection, not the only machine authority.

**No product PR beyond current campaign branch until:** migration and schema plan are tested against an existing vault.

### 4.2 RepoLedger

**Observed fit:** RepoLedger is the fleet-wide repository state and audit projection owner.

**Class:** `DIRECTLY_ADOPT`.

It should record:

- campaign ID and canonical ResearchLedger snapshot/hash;
- research authority and current evidence tier;
- destination repository/path/branch/PR for every dossier;
- audited destination commit;
- claim/concept IDs used by the projection;
- generator version;
- review/merge/staleness status;
- rejected or withheld fanout and its reason.

It should not store:

- full transcripts;
- copies of the source graph;
- duplicate project dossiers;
- research conclusions without a canonical ResearchLedger reference.

**Key implication from the corpus:** adding agents or repositories changes coordination topology. RepoLedger should track active work lanes and collisions so portfolio fanout is itself measurable.

### 4.3 Benchora

**Observed fit:** Benchora already owns benchmark execution, baselines, regression detection, mutation testing, and machine-readable reports.

**Class:** `DIRECTLY_ADOPT`.

Benchora should own the reusable experiment envelope for:

- agent-count coordination curves;
- communication ablations;
- action-abstraction levels;
- perception modality comparisons;
- state freshness/actuator fault injection;
- evaluator gaming and held-out generalization;
- autonomous-improvement promotion gates;
- total-resource normalization.

Required benchmark dimensions:

```text
success / correctness
wall-clock latency and tail latency
total model tokens and calls
total CPU/GPU/memory/network
number of actions and retries
duplicate/conflicting/reverted actions
human interventions
state-staleness and actuator errors
trace/evidence completeness
cost
held-out/generalization performance
```

**Counterfactual:** project-local test harnesses are sufficient.  
**Rejection test:** if two or more repositories cannot consume a common report/config schema without project-specific leakage, keep the experiments local and use Benchora only for aggregation.

### 4.4 phenotype-journeys

**Observed fit:** It already distinguishes soft model judgment from hard OCR/content/exit assertions and preserves recorded trajectories.

**Class:** `DIRECTLY_ADOPT`.

Recommended additions or uses:

- agent journey type with observation, decision, tool/action, result, state version, and evaluator links;
- challenge-world fixtures for navigation, stale state, interrupted action, and conflicting actors;
- hard assertions for expected state transitions, not merely screen appearance;
- privileged-state versus human-interface journey profiles;
- replay divergence report.

**Corpus connection:** Mindcraft's high-level actions isolate collaboration, while reliable-Minecraft work shows low-level primitives can be the ceiling. Journey manifests should declare the abstraction layer being tested.

### 4.5 SessionLedger

**Observed fit:** SessionLedger captures, archives, and replays AI sessions.

**Class:** `DIRECTLY_ADOPT`.

Required experiment bundle links:

- model/provider/version;
- system and task prompts;
- agent topology and identities;
- observation/action schema versions;
- environment fixture/seed/version;
- evaluator version;
- all actions, conflicts, retries, and human interventions;
- resource/cost accounting;
- terminal outcome and retained artifacts.

**Corpus connection:** computationally irreducible behavior cannot be represented by a final answer alone. The run is evidence.

**Counterpoint:** replay should not become an excuse to capture secrets or unlimited raw context. Redaction and data-governance profiles remain mandatory.

### 4.6 Tracera

**Observed fit:** Tracera is positioned as the trace, observability, and audit ledger for agentic workflows.

**Class:** `DIRECTLY_ADOPT`.

Proposed trace relation vocabulary:

```text
CLAIM_SUPPORTED_BY_SOURCE_VERSION
RUN_USES_CONFIGURATION
ACTION_READS_STATE_VERSION
ACTION_MUTATES_ARTIFACT
ACTION_CONFLICTS_WITH_ACTION
EVALUATOR_SCORES_ARTIFACT
CANDIDATE_REPLACES_INCUMBENT
CANDIDATE_REJECTED_BY_GATE
HUMAN_INTERVENTION_CHANGES_PLAN
FINDING_GENERATES_WORK_PACKAGE
WORK_PACKAGE_UPDATES_REPOSITORY
PROJECTION_DERIVED_FROM_SNAPSHOT
```

**Corpus connection:** the same final artifact can result from different trajectories, and apparent improvement can hide destructive intermediate actions or evaluator leakage.

### 4.7 AgilePlus

**Observed fit:** AgilePlus owns specs, work packages, and governance state.

**Class:** `DIRECTLY_ADOPT`.

Each corpus-driven experiment should be one bounded feature/work package with:

- source claim IDs;
- hypothesis and alternatives;
- repository and journey scope;
- fixed inputs and budgets;
- acceptance and falsification criteria;
- Benchora/phenotype-journeys configuration;
- SessionLedger/Tracera evidence requirements;
- stop/abort conditions;
- result disposition: adopt, reject, narrow, repeat, or unresolved.

Writing an ADR from an appealing video without this evidence path is prohibited.

### 4.8 Agentora

**Observed fit:** Agentora provides tools, skills, memory, lifecycle events, and hexagonal ports/adapters. The current README also identifies placeholder adapter areas and unverified release identity.

**Class:** `EXPERIMENT` and `CONTRADICTION`.

Direct applicability:

- typed environment/observation/action interfaces;
- explicit controller versus tool/actuator boundary;
- budget, cancellation, idempotency, and resume events;
- state version/freshness metadata;
- deterministic replay fixtures;
- multi-agent topology and conflict events;
- evaluator adapter separate from the optimized agent.

But Wave 1 does **not** support immediately turning Agentora into an artificial-life runtime. The useful transfer is the experimental contract, not the metaphor.

**Critical experiment:** Does Agentora provide a measurable advantage over current major agent frameworks on the same multi-agent coordination and fault-injection corpus?

### 4.9 thegent

**Observed fit:** thegent currently combines platform bootstrap, dotfiles, orchestration, routing, governance, MCP, workstream sync, templates, and many Rust/Python subsystems.

**Class:** `EXPERIMENT` and `CONTRADICTION`.

The corpus reinforces existing concerns:

- broad local competence does not guarantee coherent global authority;
- one shared umbrella increases interaction and context load;
- many agents with broad write access can amplify conflicts;
- agent activity and README progress indicators are not evidence of portfolio progress.

Recommended tests:

- one versus several orchestrator workers under matched total tokens;
- isolated worktrees versus shared-tree editing;
- append-only blackboard versus free-form shared plan;
- manager assignment versus self-selection;
- strict WIP one-lane policy versus broad fanout;
- hard acceptance gates versus narrative self-report.

**Do not infer:** thegent must be deleted or centralized further. Boundary adjudication depends on consumer, release, co-change, and real workload evidence.

### 4.10 helios-cli

**Observed fit:** The harness workspace already names queue, rollback, runner, scaling, schema, teammates, verification, and recording concerns.

**Class:** `EXPERIMENT` and partially `ALREADY_IMPLEMENTED`.

High-value experiments:

- compare direct upstream Codex execution with harnessed execution under injected tool/state faults;
- verify whether rollback restores semantic state, not just files;
- measure one/three/five-agent success and total cost;
- detect stale state between planning and edit application;
- distinguish planner failure from command/tool failure;
- require SessionLedger/Tracera-linked replay bundles.

**Potential win:** The corpus provides a coherent reason for the harness layer: not abstract “agent resilience,” but empirical containment and diagnosis of irreducible, stateful execution.

**Failure condition:** If the harness adds latency/context while not improving recovery, evidence, or success, upstream execution should remain the preferred path.

### 4.11 forgecode

**Observed state:** The repository currently presents itself as `helioslite`, while the owner inventory and prior portfolio analysis do not establish the claimed canonical successor repository consistently.

**Class:** `CONTRADICTION`.

No corpus-derived product dossier should be opened until:

- canonical repository/product/binary/package identity is resolved;
- upstream fork/base/delta/sync policy is verified;
- real consumers and released artifacts are identified;
- helios-cli versus forgecode role boundary is evidence-backed.

The corpus is relevant to session search, compression, subagents, and tool loops, but using it now would legitimize an unresolved identity.

### 4.12 HeliosLab

**Observed state:** Current README describes a configuration/feature-flag/secrets/version-management workspace, which conflicts with the accepted intended role of a desktop coding-agent workbench.

**Class:** `CONTRADICTION`.

The Emergent Garden corpus could eventually inform:

- multi-agent workspace topology;
- temporal replay and world-state inspection;
- optional human intervention controls;
- challenge environments and embodied tool feedback.

But none of that should be added until identity recovery establishes the real product and migration plan. A polished philosophical document on the wrong product would deepen the damage.

### 4.13 Civis

**Observed fit:** Civis explicitly aims to generate life, society, language, culture, markets, and polities from deterministic physical/genomic rules, with replay and emergence metrics.

**Class:** `PHILOSOPHICAL_CONVERGENCE` plus `EXPERIMENT`.

Highest-value transfers:

1. distinguish designed substrate from claimed emergent outcomes;
2. define measurable emergence properties and null models;
3. preserve seed/config/state/action replay;
4. compare intervention regimes and unintended effects;
5. test whether hardcoded era/technology/faction structures pre-author outcomes;
6. separate visual richness from system complexity;
7. validate whether claimed entropy, novelty, mutual-information, and power-law metrics measure anything user-relevant.

Proposed Civis evidence matrix:

| Claim                                    | Required evidence                                                                               |
| ---------------------------------------- | ----------------------------------------------------------------------------------------------- |
| cultures emerge                          | independent state variables and trajectories not reducible to a fixed label table               |
| markets emerge                           | price/allocation behavior under varied shocks and policies, compared with null/random baselines |
| political structures emerge              | rule-invariant diversity across seeds and environments                                          |
| interventions have systemic consequences | reproducible counterfactual paired runs                                                         |
| history is path-dependent                | divergence from controlled perturbations with replayable causal frontier                        |
| complexity increases                     | predeclared metrics plus qualitative artifact review, not one entropy line                      |

**Counterfactual:** Civis may be a richly parameterized scripted strategy simulation rather than an emergent civilization substrate. The experiment must be capable of concluding that.

### 4.14 Physical engineering: hwLedger, Eidolon, PlayCua

**Class:** `RESEARCH_LEAD` / `EXPERIMENT`.

The strongest transfer from Minecraft/AoE work is the separation of:

```text
observer
→ state estimator / synchronizer
→ planner
→ actuator
→ physical environment
→ measurement/evaluator
→ material recovery/recycling
```

Required physical-loop additions:

- calibration and state freshness on every observation;
- action authorization and collision envelope;
- reversible fixture/tooling changes where possible;
- artifact and sensor-log preservation;
- explicit handling of consumables, failed prints, recycling, and reprocessing;
- simulation-to-real gap classification;
- human intervention at safe, typed checkpoints;
- fault injection for sensor dropout, actuator slip, stale geometry, and material variance.

## 5. Proposed experiment program

### EXP-EG-001 — Agent-count coordination curve

**Question:** At what point does adding agents reduce success or increase cost for a shared software task?

- **Owners:** Benchora + Agentora/thegent + SessionLedger + Tracera
- **Treatments:** 1, 2, 3, and 5 agents
- **Controls:** same task corpus, model, total token/cost budget, tools, time, repository snapshot, evaluator
- **Topologies:** isolated tasks, shared blackboard, manager/worker, free-form peer collaboration
- **Measures:** correctness, wall time, total tokens, duplicate edits, conflicts, reversions, human interventions, trace completeness
- **Falsifies preferred view if:** five agents consistently dominate one agent on success, cost, and conflict under realistic shared-state tasks.

### EXP-EG-002 — Communication ablation

**Question:** When does detailed plan sharing help or hurt?

- **Treatments:** no communication; concise intent/status; full hidden plan; structured blackboard; event-only coordination
- **Owners:** Agentora/thegent + Benchora
- **Measures:** success, latency, token overhead, stale-plan actions, duplicate work, plan divergence
- **Corpus basis:** MineCollab's detailed-plan performance drop and Chaos shared-plan failure.

### EXP-EG-003 — Actuator reliability ceiling

**Question:** How much end-to-end success is bounded by observation/state/action reliability rather than model reasoning?

- **Treatments:** perfect mocked tools; deterministic high-level tools; real tools; injected stale observations; injected transient/permanent actuator failures
- **Owners:** phenotype-journeys + Benchora + target product
- **Measures:** planner-valid decisions, action execution success, recovery, final task success
- **Falsifies preferred view if:** planner/model changes dominate outcomes under the same actuator fault rates.

### EXP-EG-004 — Evaluator gaming and held-out generalization

**Question:** Does autonomous improvement optimize the intended outcome or exploit the visible score?

- **Treatments:** visible training evaluator; hidden held-out evaluator; adversarial cases; multiobjective hard gates
- **Owners:** Benchora + ResearchLedger
- **Artifacts:** every candidate, score vector, diff, resource use, rejection reason
- **Acceptance:** promotion requires held-out non-regression and no mandatory-dimension loss.

### EXP-EG-005 — Vision versus structured observation

**Question:** When do screenshots improve agent performance over structured textual state?

- **Treatments:** structured state only; image only; both; active image query; privileged full state
- **Owners:** phenotype-journeys + Eidolon/PlayCua or a bounded GUI task
- **Measures:** success, latency, tokens, state-estimation errors, robustness to layout changes
- **Corpus basis:** Mindcraft vision result and GUI automation constraints.

### EXP-EG-006 — State machine versus LLM controller

**Question:** For a bounded reactive task, does a state machine provide equal capability with lower cost and greater interpretability?

- **Treatments:** hand-authored FSM, evolved FSM, small policy model, LLM controller, hybrid FSM+LLM
- **Environment:** deterministic task world with partial observability and fault injection
- **Measures:** success, compute/cost, recovery, state coverage, explanation fidelity, adaptation to changed rules
- **Falsifies simple-controller preference if:** LLM/hybrid materially dominates mandatory dimensions at acceptable cost.

### EXP-EG-007 — Open-ended loop governance

**Question:** Which controls convert endless agent activity into cumulative artifact quality?

- **Treatments:** open-ended prompt only; plus checkpoints; plus hard evaluator; plus ownership/locks; plus WIP/backpressure; plus optional HITL
- **Artifact:** image, codebase, or simulation with held-out quality measures
- **Measures:** quality over time, destructive actions, repeated actions, resource use, recoverability
- **Corpus basis:** direct Chaos prompts.

### EXP-EG-008 — Replay fidelity and divergence

**Question:** Can an agent run be reproduced or faithfully reconstructed from preserved evidence?

- **Owners:** SessionLedger + Tracera + phenotype-journeys
- **Treatments:** same environment/seed; changed model; changed tool version; missing state snapshot
- **Measures:** action/state divergence frontier, final outcome, missing evidence, replay determinism
- **Acceptance:** every claimed causal conclusion identifies the earliest divergence and relevant configuration change.

### EXP-EG-009 — Civis emergence versus scripted-complexity null model

**Question:** Are Civis's macro structures meaningfully generated by local dynamics rather than fixed progression tables and labels?

- **Treatments:** full system; shuffled/local-rule ablations; scripted null model; reduced-genomic substrate; intervention variants
- **Owners:** Civis + Benchora + ResearchLedger
- **Measures:** diversity, path dependence, novelty, causal sensitivity, metric validity, human blind classification
- **Allowed result:** “current system is primarily scripted.”

### EXP-EG-010 — Physical-loop observer/actuator decomposition

**Question:** Which stage limits autonomous prototype iteration?

- **Stages:** design generation, slicing/planning, fabrication, sensor capture, state estimation, manipulation, inspection, material recovery, evaluator
- **Owners:** hwLedger + physical-engineering project + Benchora/Tracera
- **Measures:** per-stage failure probability, latency, cost, irreversible material loss, human intervention, downstream error amplification
- **Acceptance:** no aggregate “agent success” without stage attribution.

## 6. Required evidence before project PR fanout

A project-specific PR may be opened only when all are true:

1. current destination commit and role were audited;
2. relevant source claims are `SUPPORTED` or explicitly labeled provisional;
3. the mapping names a concrete mechanism, not only philosophical similarity;
4. at least one alternative and falsifier are included;
5. destination authority is not under unresolved identity conflict;
6. no raw transcript/corpus duplication is introduced;
7. the PR proposes research/docs/experiment work, not unauthorized product code;
8. RepoLedger projection record points to the canonical ResearchLedger snapshot/hash.

Wave 1 clears central ResearchLedger documentation and a RepoLedger projection record. It does not yet clear individual product PRs because the official channel census, full description corpus, and canonical source-manifest hash are incomplete.

## 7. Priority order

1. Finish ResearchLedger campaign schema and official inventory.
2. Register the campaign and current partial wave in RepoLedger.
3. Implement/reuse a Benchora experiment envelope for `EXP-EG-001` through `008`.
4. Extend phenotype-journeys only where the common action/state/replay manifest is proven reusable.
5. Resolve HeliosLab and forgecode identity contradictions.
6. Run Agentora/thegent/helios-cli coordination and reliability pilots.
7. Run Civis null-model/emergence pilot.
8. Apply observer/actuator decomposition to the physical-engineering loop.
9. Promote only reproduced general patterns into PhenoSpecs/PhenoHandbook after authority resolution.
