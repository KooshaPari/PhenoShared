# Emergent Garden Nested Corpus — Wave 1 Concept Ontology

**Campaign:** `eg-nested-corpus-2026-09`  
**Wave:** 1  
**Status:** provisional ontology derived from anchor videos, creator repositories, and the MineCollab paper

This ontology normalizes recurring mechanisms independently of the words used in any one video. It is not a claim that the creator endorses these exact labels or relations. Creator vocabulary, implementation vocabulary, and portfolio vocabulary are preserved as aliases rather than silently replaced.

## 1. Core causal chain

```text
SUBSTRATE
  ├── STATE
  ├── BUILDING_BLOCK
  ├── LOCAL_RULE / UPDATE_FUNCTION
  ├── ACTION / AFFORDANCE
  ├── ENVIRONMENT
  ├── OBSERVATION
  └── RESOURCE / CONSTRAINT
        ↓ repeated interaction
DYNAMICS
  ├── RECURRENCE
  ├── FEEDBACK
  ├── INTERACTION_TOPOLOGY
  ├── VARIATION / MUTATION
  └── SELECTION / EVALUATION
        ↓
PHENOTYPE / GLOBAL_BEHAVIOR
  ├── ORDER
  ├── CHAOS
  ├── ADAPTATION
  ├── COORDINATION
  ├── CONFLICT
  ├── NOVELTY
  └── FAILURE
        ↓ observed and retained through
EVIDENCE SYSTEM
  ├── TELEMETRY
  ├── ARTIFACT
  ├── CHECKPOINT
  ├── REPLAY
  ├── BASELINE / INCUMBENT
  └── PROVENANCE
        ↓ informs
INTERVENTION
  ├── RULE CHANGE
  ├── REPRESENTATION CHANGE
  ├── OBJECTIVE CHANGE
  ├── TOOL / ABSTRACTION CHANGE
  ├── RESOURCE / BUDGET CHANGE
  ├── GOVERNANCE CHANGE
  └── HUMAN INTERVENTION
```

## 2. Stable concept records

### EG-CON-001 — Substrate

**Definition:** The minimal state, primitives, update/action interfaces, environmental rules, and constraints from which behavior is generated.

**Creator/project aliases:** building blocks, cells, state table, tools, commands, function tree, strategy script, world rules.  
**Portfolio aliases:** runtime contract, domain model, capability substrate, execution environment.  
**Sources:** Emergent Complexity, LifeEngine, Turmites, NeuralPatterns, Mindcraft, hyperdimensions.  
**Relations:** contains `STATE`, `RULE`, `ACTION`, `ENVIRONMENT`; constrains `REACHABLE_BEHAVIOR`.  
**Anti-conflation:** a substrate is not the same as its resulting behavior or one particular policy.

### EG-CON-002 — Building block

**Definition:** A composable unit whose combinations and interactions create a larger possibility space.

**Examples:** cellular-automaton cells, organism cell types, ant states, high-level Minecraft commands, mathematical function nodes.  
**Relations:** part of `SUBSTRATE`; composes into `HIGHER_LEVEL_STRUCTURE`.  
**Risk:** treating every implementation module as a meaningful emergent building block.

### EG-CON-003 — State

**Definition:** Information retained at a point in an evolving process and available to later transitions or decisions.

**Subtypes:**

- environmental state;
- agent/internal state;
- shared state;
- hidden state;
- stale state;
- derived observation;
- checkpointed state.

**Sources:** Turmites, LifeEngine, Mindcraft, Minecraft completion work, SessionLedger relevance.  
**Relations:** read and changed by `RULE` or `ACTION`; observed through `SENSOR/QUERY`; versioned by `CHECKPOINT`.  
**Risk:** confusing the true environment state with an agent's observation of it.

### EG-CON-004 — Local rule / update function

**Definition:** A transition applied to bounded local state, often repeatedly and homogeneously.

**Examples:** CA neighborhood rule, 3×3 neural convolution plus activation, turmite read/write/turn/move transition, organism mutation/reproduction rule.  
**Relations:** transforms `STATE`; repeated by `RECURRENCE`; may produce `EMERGENT_BEHAVIOR`.  
**Counter-concept:** global planner or externally scripted trajectory.

### EG-CON-005 — Action / affordance

**Definition:** A permitted state-changing operation exposed to an actor.

**Examples:** Mindcraft high-level commands, Mineflayer primitives, agent tools, code edit, game strategy command, Life Engine movement.  
**Relations:** changes `ENVIRONMENT`; bounded by `AUTHORIZATION`; selected by `POLICY`; observed in `TRACE`.  
**Key distinction:** a high-level affordance can remove irrelevant implementation noise but can also hide the capability under test.

### EG-CON-006 — Environment

**Definition:** The external state and transition context within which actors act, receive consequences, compete, cooperate, or reproduce.

**Examples:** cellular grid, Life Engine ecology, Minecraft world, Age of Empires match, codebase plus test harness.  
**Relations:** provides `OBSERVATION`, `RESOURCE`, and `SELECTION_PRESSURE`; accepts `ACTION`; generates `OUTCOME`.  
**Portfolio implication:** the environment is part of the evaluated system, not a neutral backdrop.

### EG-CON-007 — Observation

**Definition:** A partial representation of environment or system state supplied to a controller.

**Subtypes:**

- structured textual query;
- image/screenshot;
- privileged game state;
- event stream;
- metric;
- human visual inspection.

**Relations:** produced by `SENSOR/QUERY`; consumed by `POLICY`; may be stale or lossy.  
**Sources:** Mindcraft, Vision and Vibe Coding, Minecraft-completion analysis, AgentsOfEmpires.  
**Anti-conflation:** more bytes or modalities do not necessarily mean more task-relevant information.

### EG-CON-008 — Feedback

**Definition:** Information about consequences that influences later behavior or system design.

**Subtypes:** immediate environment response, evaluator score, survival/reproduction, human selection, benchmark result, error screenshot.  
**Relations:** closes `ITERATION_LOOP`; informs `SELECTION` or `INTERVENTION`.  
**Risk:** delayed, noisy, non-causal, or gameable feedback.

### EG-CON-009 — Recurrence

**Definition:** Repeated application of a transition, policy, or improvement loop through time.

**Examples:** CA ticks, neural CA updates, organism generations, agent action loops, code-edit/evaluate/revert cycles.  
**Relations:** amplifies local rules; enables `MEMORY`, `ADAPTATION`, and `PATH_DEPENDENCE`.  
**Risk:** repeated activity is not cumulative progress.

### EG-CON-010 — Interaction topology

**Definition:** The pattern by which actors, state, resources, and messages can affect one another.

**Subtypes:** shared grid, shared file, pairwise chat, blackboard, resource competition, isolated worktree, manager/worker hierarchy.  
**Relations:** determines `COORDINATION_COST`, `INTERFERENCE`, and possible `COLLECTIVE_BEHAVIOR`.  
**Sources:** multi-ant systems, Life Engine ecology, Chaos prompts, MineCollab.  
**Portfolio implication:** agent count without topology is an incomplete experimental variable.

### EG-CON-011 — Emergence

**Definition:** A macroscopic property or behavior arising from repeated interaction among lower-level components and not conveniently specified as a direct sequence of outcomes.

**Subtypes used in this corpus:**

- structural emergence;
- behavioral emergence;
- computational emergence;
- adaptive/ecological emergence;
- collective-agent emergence;
- apparent or observer-ascribed emergence.

**Relations:** arises from `SUBSTRATE` plus `DYNAMICS`; may be useful, neutral, or harmful.  
**Anti-conflation:** emergence is not synonymous with intelligence, autonomy, improvement, decentralization, or goodness.

### EG-CON-012 — Computational irreducibility

**Definition:** The bounded proposition that some future behavior lacks a substantially cheaper exact predictive shortcut than executing or simulating the process.

**Relations:** motivates `EXECUTION_AS_EVIDENCE`, `REPLAY`, and empirical search.  
**Risk:** being used rhetorically for merely complicated or poorly understood systems.  
**Required evidence:** specify the behavior, fidelity, and shortcut class under discussion.

### EG-CON-013 — Variation / mutation

**Definition:** A process that creates candidate differences in structure, parameters, policy, code, or behavior.

**Examples:** organism anatomy mutation, state-machine transition mutation, parameter perturbation, source-code edit, strategy-script edit.  
**Relations:** generates candidates for `SELECTION`; locality depends on `REPRESENTATION`.  
**Risk:** destructive or non-local mutation that makes search effectively random.

### EG-CON-014 — Selection / evaluation

**Definition:** A rule that determines which candidates persist, reproduce, replace an incumbent, or count as successful.

**Subtypes:**

- environmental survival/reproduction;
- scalar loss or score;
- tournament outcome;
- unit/acceptance test;
- human aesthetic selection;
- novelty criterion;
- multiobjective gate.

**Relations:** creates `SELECTION_PRESSURE`; depends on `EVALUATOR`; shapes `ADAPTATION`.  
**Key principle:** the effective evaluator is part of the architecture.

### EG-CON-015 — Selection pressure

**Definition:** The differential consequence produced by an environment or evaluator that makes some variants persist more than others.

**Sources:** LifeEngine, gradient/evolution comparison, fractalsearch, AgentsOfEmpires.  
**Relations:** induced by `ENVIRONMENT` and `EVALUATOR`; drives `ADAPTATION`; can cause `METRIC_GAMING`.  
**Anti-conflation:** an implicit pressure is not objective-free.

### EG-CON-016 — Representation / genotype

**Definition:** The encoded form that an optimizer, mutation operator, or human directly changes.

**Examples:** neural weights, transition table, cell arrangement, function tree, code patch, prompt, strategy script.  
**Relations:** maps through `DEVELOPMENT/EXECUTION` to a `PHENOTYPE`; determines mutation neighborhood.  
**Sources:** LifeEngine, Turmites, NeuralPatterns, hyperdimensions, fractalsearch.  
**Risk:** a compact representation may be expressive but difficult to search or interpret.

### EG-CON-017 — Phenotype / realized behavior

**Definition:** The executed structure, artifact, or behavior produced by a representation in an environment.

**Examples:** organism anatomy/behavior, rendered surface, gameplay strategy, benchmark trajectory, generated city image.  
**Relations:** evaluated by `EVALUATOR`; preserved as `ARTIFACT` or `REPLAY`; may differ across environments.  
**Anti-conflation:** source-code or genotype improvement does not guarantee phenotype improvement on held-out environments.

### EG-CON-018 — Adaptation

**Definition:** Persistent change in a population, policy, or artifact that improves survival or measured performance under a particular pressure.

**Relations:** requires `VARIATION`, `SELECTION`, and persistence; may overfit.  
**Anti-conflation:** adaptation is not necessarily open-ended progress or general intelligence.

### EG-CON-019 — Open-endedness

**Definition:** Continued generation of materially novel structures, strategies, or behaviors without a single known terminal optimum.

**Sources:** artificial-life framing, LifeEngine, open-ended agent prompts.  
**Relations:** supported by diverse `REPRESENTATION`, changing `ENVIRONMENT`, novelty, and non-terminal selection.  
**Risk:** being confused with endless execution or unbounded resource use.

### EG-CON-020 — Search

**Definition:** Exploration of candidate representations or actions under information from an evaluator or environment.

**Subtypes:** gradient-guided search, random/local mutation, evolutionary population search, tree/search planning, language-model proposal, human-guided search.  
**Relations:** operates over `SEARCH_SPACE`; uses `EVALUATION_SIGNAL`; constrained by `BUDGET`.  
**Anti-conflation:** calling two processes search does not make their information efficiency equivalent.

### EG-CON-021 — Gradient-guided optimization

**Definition:** Search using local derivative information about an objective with respect to parameters.

**Relations:** subtype of `SEARCH`; effective when objective/representation are differentiable and gradients informative.  
**Counterpart:** `GRADIENT_FREE_SEARCH`.  
**Risk:** local minima, brittle objectives, differentiability constraints, and high compute requirements.

### EG-CON-022 — Evolutionary / gradient-free search

**Definition:** Candidate variation and selection without relying on an exact derivative of the objective.

**Relations:** subtype of `SEARCH`; compatible with discrete artifacts and black-box environments.  
**Risk:** poor sample efficiency, evaluator overfitting, mutation locality problems.  
**Anti-conflation:** not every repeated trial or agent loop is evolutionary.

### EG-CON-023 — Controller / policy

**Definition:** A stateful or stateless mapping from observations and internal state to actions.

**Examples:** state machine, neural network, LLM agent, hand-written game AI.  
**Relations:** receives `OBSERVATION`; chooses `ACTION`; may hold `INTERNAL_STATE`.  
**Design principle:** choose the simplest controller satisfying capability, cost, compatibility, and interpretability requirements.

### EG-CON-024 — Abstraction level

**Definition:** The semantic granularity of observations and actions exposed to a controller or evaluator.

**Examples:** raw pixels and mouse movement versus structured world queries and `craft_item`; source-code edit versus parameter mutation.  
**Relations:** changes `TASK_DIFFICULTY`, `FAILURE_SURFACE`, and validity of capability claims.  
**Risk:** privileged abstractions can make a benchmark look solved while bypassing the target capability.

### EG-CON-025 — Partial observability

**Definition:** The actor cannot directly inspect complete current environment state.

**Relations:** increases need for memory, communication, active querying, belief state, and uncertainty.  
**Sources:** MineCollab hidden plans, Minecraft visual/text observations, GUI automation.  
**Counter-concept:** privileged/full-state access.

### EG-CON-026 — State synchronization / freshness

**Definition:** The degree to which observations, shared records, and action assumptions match the environment's current state.

**Relations:** prerequisite for reliable planning and coordination; failures produce stale actions and accidental undoing.  
**Sources:** Minecraft-completion analysis, shared-file Chaos experiment, multi-agent work.  
**Portfolio implication:** version shared state and report freshness/conflict errors independently.

### EG-CON-027 — Coordination

**Definition:** Processes by which multiple actors allocate work, share relevant state, avoid destructive interference, and converge on compatible outcomes.

**Subtypes:** implicit stigmergy, pairwise communication, shared plan, manager/worker decomposition, ownership/locking, market/resource allocation.  
**Relations:** required when `INTERACTION_TOPOLOGY` creates dependencies; incurs `COORDINATION_COST`.  
**Anti-conflation:** communication volume is not coordination quality.

### EG-CON-028 — Coordination cost

**Definition:** Delay, tokens, conflicts, duplicate work, state-maintenance burden, and decision overhead introduced by multiple actors.

**Sources:** MineCollab agent-count and plan-communication ablations, Chaos experiment.  
**Relations:** can exceed parallel work benefit; measured by `COORDINATION_CURVE`.  
**Required metrics:** success, wall time, total compute/tokens, duplicate actions, conflicts, reversions, interventions.

### EG-CON-029 — Interference

**Definition:** One actor's action invalidates, destroys, duplicates, or reduces the value of another actor's work.

**Examples:** overwriting an image, gathering the same resource, consuming shared materials, undoing a build.  
**Relations:** caused by shared state/resources and weak ownership; detected by traces and diffs.  
**Mitigations:** isolation, locking, ownership, transactional updates, merge protocols, conflict-aware scheduling.

### EG-CON-030 — Observability

**Definition:** The ability to reconstruct what happened, when, under which state, configuration, actor, and environment.

**Artifacts:** structured events, metrics, screenshots, recordings, diffs, heartbeats, traces, state hashes.  
**Relations:** supports `DEBUGGING`, `REPLAY`, `EVALUATION`, and causal claims.  
**Sources:** AgentsOfEmpires, Mindcraft, portfolio Tracera/SessionLedger relevance.

### EG-CON-031 — Replay

**Definition:** Re-execution or faithful temporal reconstruction of a prior run from preserved inputs, state, actions, and artifacts.

**Relations:** evidence mechanism for irreducible systems; detects nondeterminism and divergence.  
**Risk:** a visual recording alone may be non-executable and omit hidden state.

### EG-CON-032 — Checkpoint / incumbent

**Definition:** A retained known state or candidate against which later changes can be compared or from which execution can resume.

**Relations:** enables rollback, safe autonomous improvement, and resumability.  
**Sources:** fractalsearch/autoresearch pattern, tournament archives, ResearchLedger crawl leases.  
**Alternative:** population archive or Pareto frontier rather than one incumbent.

### EG-CON-033 — Evaluator

**Definition:** The mechanism that turns an executed candidate or trajectory into acceptance, rejection, score, ranking, or evidence.

**Subtypes:** deterministic test, game result, benchmark metric, human judgment, model judge, survival process.  
**Relations:** implements `SELECTION`; susceptible to `GOODHART_FAILURE`; must be versioned.  
**Portfolio implication:** evaluator code/config/data is a first-class artifact.

### EG-CON-034 — Metric gaming / Goodhart failure

**Definition:** Improvement of the measured proxy without corresponding improvement—and sometimes with degradation—in the intended outcome.

**Relations:** risk of autonomous optimization and fixed evaluators; detected through held-out tests, adversarial checks, and multiobjective review.  
**Anti-conflation:** any score improvement is not automatically gaming; causal evidence is required.

### EG-CON-035 — Robustness

**Definition:** Retention of required behavior across seeds, environments, perturbations, versions, and failure conditions.

**Relations:** distinct from peak score; evaluated by distributions and fault injection.  
**Sources:** reliable Minecraft completion question, tournament variance, portfolio Benchora/journeys relevance.

### EG-CON-036 — Interpretability

**Definition:** The degree to which internal state, representation, decisions, or failures can be inspected and meaningfully explained.

**Examples:** state-machine transitions, explicit rule tables, function trees, event traces.  
**Relations:** supports debugging and intentional intervention; may trade against expressive power.  
**Anti-conflation:** human-readable structure is not proof of correct causal explanation.

### EG-CON-037 — Sandbox / containment

**Definition:** A boundary limiting the damage an autonomous actor or generated program can cause.

**Sources:** Mindcraft code-execution warnings, coding-agent and GUI-automation context.  
**Relations:** enforces authorization around `ACTION`; reduces blast radius but does not guarantee safety.  
**Portfolio implication:** untrusted generated code and tools require explicit capability boundaries.

### EG-CON-038 — Backpressure / budget

**Definition:** Limits on concurrent work, actions, time, tokens, cost, mutations, or frontier expansion.

**Relations:** prevents open-ended systems from turning activity into resource exhaustion; part of governance.  
**Sources:** negative implications of Chaos and MineCollab scaling.  
**Anti-conflation:** a budget does not define what work is valuable; it only bounds exposure.

### EG-CON-039 — Human intervention point

**Definition:** An explicit state at which a human may inspect, redirect, approve, reject, or terminate work without being required for every step.

**Relations:** optional control surface in closed loops; should be typed and observable.  
**Portfolio fit:** user's HITL-optional continuous-loop requirement.  
**Risk:** implicit rescue dependence that makes autonomy claims false.

### EG-CON-040 — Weak recursive self-improvement

**Definition:** An optimizer repeatedly improves an external artifact or policy under a mostly fixed model and evaluator.

**Example:** fractalsearch modifies approximation code and retains improvements.  
**Relations:** subtype of `AUTONOMOUS_OPTIMIZATION`; changes `ARTIFACT`, not necessarily `OPTIMIZER_CORE`.  
**Anti-conflation:** not equivalent to model self-training, objective self-modification, or unrestricted intelligence amplification.

## 3. Anti-conflation matrix

| Often collapsed terms                         | Required distinction                                                                   |
| --------------------------------------------- | -------------------------------------------------------------------------------------- |
| emergence / intelligence                      | Complex global behavior need not reason, plan, or pursue goals                         |
| emergence / goodness                          | Emergent behavior may be useful, neutral, chaotic, or destructive                      |
| autonomy / progress                           | Independent action can repeat or regress without cumulative evaluation                 |
| activity / work                               | Actions count output volume; work requires movement against an accepted objective      |
| search / learning                             | Search explores candidates; learning persistently changes a policy/model from evidence |
| adaptation / generalization                   | Better fit to one pressure can reduce performance elsewhere                            |
| evolution / iteration                         | Evolution requires variation, differential selection, and persistence/heritability     |
| natural selection / objective-free            | Environment rules create implicit selection pressures                                  |
| self-improvement / model self-modification    | External code optimization is weaker than changing the optimizer itself                |
| multi-agent / parallel                        | Multiple agents may interact and contend; parallel isolated jobs may not               |
| communication / coordination                  | More messages can reduce performance or amplify stale plans                            |
| observability / evidence                      | Logs exist; evidence must resolve a claim under a pinned run/configuration             |
| replay / recording                            | A recording is viewable; replay should reconstruct state/action semantics              |
| rich modality / information                   | Images can contain more data but less usable task state                                |
| universal computation / efficient computation | Expressive possibility says nothing about practical runtime or search cost             |
| interpretable / correct                       | Readable state does not prove causal validity or task success                          |
| deterministic / predictable                   | Deterministic transitions can still be computationally difficult to forecast           |
| open-ended / infinite loop                    | Open-endedness requires continuing novelty, not endless repetition                     |

## 4. Mechanism families

### A. Rule-generated worlds

```text
SUBSTRATE
→ LOCAL_RULE
→ RECURRENCE
→ EMERGENT_BEHAVIOR
→ OBSERVATION / INTERVENTION
```

Representative sources: cellular automata, Turmites, NeuralPatterns, LifeEngine.

### B. Selection-generated adaptation

```text
REPRESENTATION
→ VARIATION
→ EXECUTION_IN_ENVIRONMENT
→ EVALUATION / SURVIVAL
→ RETENTION / REPRODUCTION
→ ADAPTATION
```

Representative sources: LifeEngine, hillclimbers, fractalsearch, AgentsOfEmpires.

### C. Embodied agent loop

```text
ENVIRONMENT_STATE
→ OBSERVATION
→ CONTROLLER / PLAN
→ ACTION_ABSTRACTION
→ ACTUATOR
→ ENVIRONMENT_TRANSITION
→ TRACE / EVALUATION
```

Representative sources: Mindcraft/MineCollab, reliable Minecraft completion, AgentsOfEmpires.

### D. Multi-actor coordination loop

```text
TASK / SHARED_GOAL
→ PARTITION / OWNERSHIP
→ LOCAL_ACTIONS
→ SHARED_STATE + COMMUNICATION
→ CONFLICT / DUPLICATION / COMPLEMENTARITY
→ GLOBAL_EVALUATION
→ REPLAN
```

Representative sources: Chaos prompts, MineCollab, multiple ants/organisms.

### E. Autonomous artifact improvement

```text
INCUMBENT
→ PROPOSAL
→ ISOLATED CHANGE
→ EXECUTION
→ EVALUATOR
→ ACCEPT / REJECT / PARETO ARCHIVE
→ CHECKPOINT
→ NEXT PROPOSAL
```

Representative sources: fractalsearch, AgentsOfEmpires, potential portfolio coding-agent loops.

## 5. Recurrence matrix

| Concept                 |   CA / Turmites   |      LifeEngine       |     NeuralPatterns     | Gradient / evolution |     Chaos agents     |    Mindcraft     |     fractalsearch     |   AgentsOfEmpires   |     Higher dimensions     |
| ----------------------- | :---------------: | :-------------------: | :--------------------: | :------------------: | :------------------: | :--------------: | :-------------------: | :-----------------: | :-----------------------: |
| substrate               |         ✓         |           ✓           |           ✓            |          ✓           |          ✓           |        ✓         |           ✓           |          ✓          |             ✓             |
| local rule              |         ✓         |           ✓           |           ✓            |          —           |          —           |        —         |           —           |          —          |     function grammar      |
| recurrence              |         ✓         |           ✓           |           ✓            |          ✓           |          ✓           |        ✓         |           ✓           |          ✓          |   parameter/time loops    |
| environment             |       grid        |        ecology        |       image grid       |  objective surface   |      filesystem      |    Minecraft     |     code+harness      |       AoE II        |   renderer/search space   |
| variation               | rule/state choice |       mutation        |   weight/rule choice   |   optimizer update   |     agent edits      |  policy/action   |       code edit       |    strategy edit    |     function mutation     |
| evaluation              |  behavior class   | survival/reproduction | visual/target behavior |         loss         |    weak/implicit     | task completion  |  approximation score  |    match outcome    |  human/target similarity  |
| multi-actor interaction |   multiple ants   |      populations      |        optional        |  population methods  |       central        |     central      | usually one optimizer |     competitors     |   optional populations    |
| observability           |   visual trace    |     visual/state      |         visual         |     loss curves      |    image + files     | logs/world state |     score/history     | heartbeat/recording | interactive visualization |
| rollback/incumbent      |  manual presets   |        lineage        |        presets         |      checkpoint      |         weak         |  episode reset   |        central        |  strategy archive   |           saves           |
| interpretability        |    rule table     |     anatomy/state     |        limited         |        mixed         | low global coherence |  action traces   |       code diff       |   scripts/events    |       function tree       |

## 6. Portfolio translation table

| Corpus concept       | Portfolio-level contract candidate                                         |
| -------------------- | -------------------------------------------------------------------------- |
| substrate            | Versioned environment/tool/action schema for every agent evaluation        |
| interaction topology | Explicit ownership, shared-state, lock, and communication model            |
| coordination cost    | Success-versus-agent-count curve with total resource and conflict metrics  |
| state freshness      | Observation timestamp/version and stale-read rejection semantics           |
| action abstraction   | Declared primitive/high-level action layer and capability validity limits  |
| evaluator            | Pinned code/config/data plus negative controls and held-out cases          |
| selection pressure   | Requirement-to-test-to-runtime outcome traceability                        |
| incumbent/checkpoint | Reversible candidate promotion and retained prior evidence                 |
| replay               | SessionLedger/Tracera run bundle resolving actions, state, and artifacts   |
| open-endedness       | Bounded novelty loop with WIP, budget, stop, and human-intervention levers |
| interpretability     | Inspectable policy/controller state where cost-effective                   |
| representation       | Explicit mutation/edit unit and expected locality                          |
| robustness           | Seed/environment/version distributions, not single-run success             |
| metric gaming        | Multiobjective and adversarial evaluator validation                        |

## 7. Open ontology questions

1. Does the creator use “emergence” consistently enough to justify one canonical concept, or should structural, computational, adaptive, and collective emergence remain separate sibling concepts?
2. Does the 2026 `Artificial Life` video define a creator-specific taxonomy that conflicts with this one?
3. Which projects use explicit novelty search versus ordinary fitness optimization?
4. How much of higher-dimensional function evolution is human aesthetic selection rather than automated evaluation?
5. Does Mindcraft's current `develop` branch materially change the action/observation architecture described in the 2025 paper?
6. Which direct project artifacts preserve complete run lineage rather than only final demos?
7. When does a high-level tool clarify the tested capability, and when does it bypass it?
8. What typed intervention model best spans simulation, coding-agent, GUI, and physical-engineering loops?

This ontology must remain versioned. Wave 2 may split, merge, or supersede concepts as direct scripts, descriptions, papers, and implementations are added.
