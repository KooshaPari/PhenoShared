# Emergent Garden Nested Corpus — Wave 1 Claim Ledger

**Campaign:** `eg-nested-corpus-2026-09`  
**Wave:** 1  
**Observed through:** 2026-09-04  
**Status:** partial, source-pinned claim register

This ledger separates direct creator statements, implemented mechanisms, controlled technical evidence, transcript-derived propositions, and our own synthesis. It is intentionally stricter than a summary: every material claim includes a plausible competing interpretation and a condition that would weaken or overturn it.

## Status vocabulary

| Status                  | Meaning                                                                     |
| ----------------------- | --------------------------------------------------------------------------- |
| `SUPPORTED`             | Direct or primary evidence supports the bounded wording below               |
| `SUPPORTED_WITH_LIMITS` | Supported, but scope/generalization limits are material                     |
| `PROVISIONAL`           | Evidence is indirect, incomplete, or transcript-derived and needs promotion |
| `ANALYST_INFERENCE`     | Our synthesis across sources; not something the creator explicitly asserted |
| `CONTESTED`             | Material evidence supports more than one live interpretation                |
| `GAP`                   | Required evidence has not yet been acquired                                 |

## Evidence vocabulary

| Evidence type        | Meaning                                                                         |
| -------------------- | ------------------------------------------------------------------------------- |
| `CREATOR_DIRECT`     | Creator-controlled site, repository, prompt, or description                     |
| `PRIMARY_TECHNICAL`  | Paper, benchmark, code, fixtures, or direct implementation artifact             |
| `TRANSCRIPT_DERIVED` | Timestamped transcript/summary mirror; useful but below creator-controlled text |
| `SECONDARY_INDEX`    | Search/index record used for inventory or discovery only                        |
| `PORTFOLIO_OBSERVED` | Current KooshaPari repository documentation/code at a pinned revision           |
| `ANALYST_SYNTHESIS`  | Inference across several sources                                                |

---

## EG-CLM-001 — Emergent complexity is a real creator-level through-line

**Claim:** Max Robinson explicitly identifies emergent complexity—simple things combining under rules to produce complex things—as his central fascination, and groups artificial life, artificial intelligence, games, simulations, and web toys under that interest.

- **Status:** `SUPPORTED`
- **Evidence:** `CREATOR_DIRECT`
- **Source:** [Emergent Garden](https://emergentgarden.io/)
- **Locator:** creator biography / landing-page introduction
- **Confidence:** high
- **Alternative:** the phrase may be an umbrella brand applied retrospectively to otherwise unrelated projects.
- **Would weaken/overturn:** a broader creator archive showing that the theme was recently imposed and is absent from most project motivations, or an explicit creator statement rejecting a unifying interpretation.
- **Allowed implication:** corpus-level philosophical analysis is justified.
- **Disallowed implication:** every project necessarily implements one coherent technical architecture.

## EG-CLM-002 — Tiny local rules can produce qualitatively complex global behavior

**Claim:** Across cellular automata, Langton-style ants, neural cellular automata, and the Life Engine, compact local update rules generate persistent structures, adaptation, disorder, repeating patterns, and behavior not evident from inspecting one update step.

- **Status:** `SUPPORTED_WITH_LIMITS`
- **Evidence:** `CREATOR_DIRECT`, `PRIMARY_TECHNICAL`, `TRANSCRIPT_DERIVED`
- **Sources:**
  - [Emergent Complexity](https://www.youtube.com/watch?v=0HqUYpGQIfs)
  - [Langton's Ants and Turing Machines](https://www.youtube.com/watch?v=7x9J7rsLC50)
  - [What are neural cellular automata?](https://www.youtube.com/watch?v=3H79ZcBuw4M)
  - [NeuralPatterns](https://github.com/MaxRobinsonTheGreat/NeuralPatterns)
  - [LifeEngine](https://github.com/MaxRobinsonTheGreat/LifeEngine)
- **Locator:** update-rule descriptions and implementation READMEs/source
- **Confidence:** high for the examples; medium for broader generalization
- **Alternative:** observers may assign complexity to visually elaborate output even when the mechanism is shallow or repetitive.
- **Would weaken/overturn:** quantitative complexity analysis showing that the highlighted examples collapse to a small repertoire under reasonable measures, or that apparent novelty is renderer noise.

## EG-CLM-003 — Layered emergence creates new effective building blocks

**Claim:** The `Emergent Complexity` presentation treats lower-level structures as components for higher-level organization, allowing complexity to accumulate by composition rather than only by adding base rules.

- **Status:** `SUPPORTED_WITH_LIMITS`
- **Evidence:** creator description plus `TRANSCRIPT_DERIVED`
- **Source:** [Emergent Complexity](https://www.youtube.com/watch?v=0HqUYpGQIfs)
- **Locator:** building blocks, combinatorial explosion, and layered-emergence sections
- **Confidence:** medium-high
- **Alternative:** higher-level “building blocks” may be an explanatory convenience rather than causally autonomous entities.
- **Would weaken/overturn:** direct transcript review showing the source makes only a visual analogy, or implementation evidence showing no reusable higher-level regularities.

## EG-CLM-004 — Computational irreducibility makes execution part of understanding

**Claim:** For some rule systems, a complete shortcut prediction is unavailable or impractical; observing their consequences requires executing or approximating the process.

- **Status:** `SUPPORTED_WITH_LIMITS`
- **Evidence:** creator description/transcript, cited Wolfram framing, implementation examples
- **Source:** [Emergent Complexity](https://www.youtube.com/watch?v=0HqUYpGQIfs)
- **Locator:** computational-irreducibility and chaos sections
- **Confidence:** medium-high for the bounded claim
- **Alternative:** “irreducible” is sometimes used too loosely for systems that merely lack a known convenient analytic shortcut.
- **Would weaken/overturn:** the source using the term only rhetorically, or efficient predictive abstractions being demonstrated for the exact behavior under discussion.
- **Portfolio implication:** preserve replayable executions and empirical evidence.
- **Non-implication:** specifications, invariants, and static reasoning are unnecessary.

## EG-CLM-005 — Universal computation does not imply practical predictability or control

**Claim:** Turmite/Langton-style transition systems can be computationally universal while their macroscopic behavior remains difficult to infer, classify, or steer from the rule table alone.

- **Status:** `SUPPORTED_WITH_LIMITS`
- **Evidence:** `CREATOR_DIRECT`, implementation source, cited theory
- **Sources:**
  - [Langton's Ants and Turing Machines](https://www.youtube.com/watch?v=7x9J7rsLC50)
  - [turmites source](https://github.com/MaxRobinsonTheGreat/turmites)
- **Locator:** Turing-machine/state-transition discussion and simulator implementation
- **Confidence:** high for the distinction; medium for any specific universality construction not yet reproduced
- **Alternative:** the showcased systems may be universal only under carefully engineered configurations, not under typical random rules.
- **Would weaken/overturn:** failure to recover the referenced construction or a mismatch between the implemented simulator and the universality argument.

## EG-CLM-006 — NeuralPatterns uses an unusually compact homogeneous update substrate

**Claim:** NeuralPatterns implements a neural cellular automaton using a repeated 3×3 convolution followed by an activation function at each pixel, producing dynamic global patterns from one local update form.

- **Status:** `SUPPORTED`
- **Evidence:** `CREATOR_DIRECT`, `PRIMARY_TECHNICAL`
- **Sources:**
  - [NeuralPatterns repository](https://github.com/MaxRobinsonTheGreat/NeuralPatterns)
  - [What are neural cellular automata?](https://www.youtube.com/watch?v=3H79ZcBuw4M)
- **Locator:** repository README and simulation source
- **Confidence:** high
- **Alternative:** visual complexity may depend heavily on hand-selected weights/initialization and not on the update substrate alone.
- **Would weaken/overturn:** source inspection showing materially different or non-local processing dominates the rendered behavior.

## EG-CLM-007 — The Life Engine uses environmental survival and reproduction rather than a single explicit task score

**Claim:** The Life Engine allows organisms that survive, reproduce, and out-compete neighbors to propagate, instead of manually selecting the highest scorer for a predetermined external task.

- **Status:** `SUPPORTED`
- **Evidence:** `CREATOR_DIRECT`, `PRIMARY_TECHNICAL`
- **Source:** [LifeEngine](https://github.com/MaxRobinsonTheGreat/LifeEngine)
- **Locator:** README sections on environment, organisms, reproduction, mutation, movement, eyes, and brains
- **Confidence:** high
- **Alternative:** simulator hyperparameters and resource rules still constitute an implicit engineered fitness landscape.
- **Would weaken/overturn:** implementation showing a hidden scalar objective directly selects offspring or populations.
- **Important limit:** endogenous selection does not guarantee alignment with a user's desired outcome.

## EG-CLM-008 — State-machine brains were chosen as a practical controller, not as a universal rejection of neural networks

**Claim:** In the later Life Engine brain work, evolvable state machines were selected because they were inexpensive, inspectable, and compatible with the simulator's existing organisms and mutation model.

- **Status:** `PROVISIONAL`
- **Evidence:** `TRANSCRIPT_DERIVED`; related implementation context
- **Source:** [Evolving Brains in the Life Engine](https://www.youtube.com/watch?v=DksO3mqh0kg)
- **Locator:** controller-choice and mutation sections
- **Confidence:** medium
- **Alternative:** the state-machine choice may have been primarily pedagogical or aesthetic, with performance/compatibility offered after the fact.
- **Would weaken/overturn:** creator-controlled script or source history showing another principal rationale.
- **Promotion requirement:** creator-controlled transcript/script or code/commit evidence that records the decision.

## EG-CLM-009 — Optimization method should follow search-space structure

**Claim:** Gradient descent and evolutionary mutation both search parameter spaces, but gradient information usually provides much greater efficiency in smooth, differentiable, high-dimensional spaces; evolutionary/local search remains useful when gradients are unavailable, unreliable, or the representation is discrete.

- **Status:** `SUPPORTED_WITH_LIMITS`
- **Evidence:** creator description, direct demonstration repositories, established primary literature linked by the creator
- **Sources:**
  - [Gradient Descent vs Evolution](https://www.youtube.com/watch?v=Anc2_mnb3V8)
  - [mandelbrotnn](https://github.com/MaxRobinsonTheGreat/mandelbrotnn)
  - [hillclimbers](https://github.com/MaxRobinsonTheGreat/hillclimbers)
  - [ManimApproximations](https://github.com/MaxRobinsonTheGreat/ManimApproximations)
- **Confidence:** high for the bounded comparison
- **Alternative:** modern gradient-free optimizers and hybrid methods may outperform the simple evolutionary procedures demonstrated.
- **Would weaken/overturn:** controlled tests on the same representation/evaluation budget showing the stated efficiency ordering reverses.

## EG-CLM-010 — Representation determines mutation locality and reachable behavior

**Claim:** Cell anatomies, transition tables, neural weights, function trees, source code, and game strategy scripts create materially different neighborhoods for search; choosing the representation is part of choosing the optimizer.

- **Status:** `ANALYST_INFERENCE`
- **Evidence:** cross-source `ANALYST_SYNTHESIS`
- **Sources:** LifeEngine, Turmites, NeuralPatterns, hyperdimensions, fractalsearch, AgentsOfEmpires
- **Confidence:** high as a synthesis
- **Alternative:** evaluator quality or model capability may dominate representation choice in the observed projects.
- **Would weaken/overturn:** controlled comparisons showing representation changes have negligible effect after holding optimizer/evaluator constant.

## EG-CLM-011 — The Chaos prompts intentionally maximize autonomy while minimizing coordination structure

**Claim:** The direct agent prompts instruct agents to act indefinitely, repeatedly inspect and modify artifacts, avoid waiting for user input, and coordinate through shared append/read files, while providing little ownership, serialization, acceptance, or termination structure.

- **Status:** `SUPPORTED`
- **Evidence:** `CREATOR_DIRECT`
- **Sources:**
  - [agent_prompts repository](https://github.com/MaxRobinsonTheGreat/agent_prompts)
  - `city_instructions.txt`
  - `open_ended_instructions.txt`
- **Confidence:** high
- **Alternative:** the weak coordination is a deliberate experimental treatment rather than a proposed production architecture.
- **Would weaken/overturn:** different prompts actually used in the recorded experiment containing stronger hidden coordination rules.

## EG-CLM-012 — Weakly coordinated agents can destroy or overwrite useful shared work

**Claim:** In the Chaos experiment, agents operating on shared artifacts produced interference, overwrites, degradation, repetitive activity, and descriptions that exceeded the quality of the actual artifact.

- **Status:** `SUPPORTED_WITH_LIMITS`
- **Evidence:** direct prompts plus `TRANSCRIPT_DERIVED` observations
- **Source:** [The Chaos of AI Agents](https://www.youtube.com/watch?v=2YYjPs8t8MI)
- **Confidence:** medium-high for this experiment
- **Alternative:** failures may be caused primarily by the shared-file tool, model weaknesses, or adversarially open-ended prompting rather than multi-agent interaction itself.
- **Would weaken/overturn:** replay artifacts showing independent agents improved quality under the same treatment, or that apparent overwrites were renderer/versioning errors.
- **Non-implication:** multi-agent collaboration is generally ineffective.

## EG-CLM-013 — More agents can reduce task success

**Claim:** In MineCollab's evaluated environments, increasing agent count from two to five can sharply reduce performance, with tested tasks falling from around 90% completion to below 30% as duplication, competition, and accidental undoing increase.

- **Status:** `SUPPORTED_WITH_LIMITS`
- **Evidence:** `PRIMARY_TECHNICAL`
- **Source:** [Collaborating Action by Action: A Multi-agent LLM Framework for Embodied Reasoning](https://arxiv.org/abs/2504.17950)
- **Locator:** agent-count scaling and collaboration-failure analysis
- **Confidence:** high for the reported benchmark; low for unrestricted generalization
- **Alternative:** the decline may be specific to the protocol, task decomposition, shared Minecraft resources, or tested models.
- **Would weaken/overturn:** reproduction at the paper's pinned revision failing to show the curve, or robust alternative coordination reversing it under matched budgets.
- **Portfolio implication:** measure a coordination curve before treating agent count as capacity.

## EG-CLM-014 — Forced detailed-plan communication can harm performance

**Claim:** MineCollab reports a greater-than-15% performance reduction when agents are forced to communicate hidden detailed plans, suggesting that more explicit communication can add delay, stale commitments, or coordination noise.

- **Status:** `SUPPORTED_WITH_LIMITS`
- **Evidence:** `PRIMARY_TECHNICAL`
- **Source:** [MineCollab paper](https://arxiv.org/abs/2504.17950)
- **Locator:** communication ablation
- **Confidence:** high for the reported treatment
- **Alternative:** the specific plan format, timing, token budget, or model instruction may be the harmful element rather than detailed planning itself.
- **Would weaken/overturn:** matched ablations where concise shared plans or blackboard state improve performance without additional confounders.

## EG-CLM-015 — High-level tools isolate collaboration from low-level API recovery

**Claim:** Mindcraft exposes dozens of parameterized high-level tools so the benchmark can test embodied reasoning and collaboration without requiring every model to reconstruct low-level Mineflayer syntax.

- **Status:** `SUPPORTED`
- **Evidence:** `PRIMARY_TECHNICAL`, current project README
- **Sources:**
  - [MineCollab paper](https://arxiv.org/abs/2504.17950)
  - [mindcraft-bots/mindcraft](https://github.com/mindcraft-bots/mindcraft)
- **Confidence:** high
- **Alternative:** high-level tools may conceal capabilities or failure modes needed for claims about general embodied agency.
- **Would weaken/overturn:** tool implementations leaking privileged task solutions or benchmark labels.
- **Design implication:** abstraction level must be declared as part of the benchmark contract.

## EG-CLM-016 — Richer sensing is not automatically better grounding

**Claim:** Adding screenshot/vision input to Mindcraft did not automatically produce a dramatic improvement, and structured textual observations can rival or outperform visual inputs for tested tasks.

- **Status:** `SUPPORTED_WITH_LIMITS`
- **Evidence:** `PRIMARY_TECHNICAL`, creator description
- **Sources:**
  - [Vision and Vibe Coding — Mindcraft Update](https://www.youtube.com/watch?v=iDJ6GrHNoDs)
  - [MineCollab paper](https://arxiv.org/abs/2504.17950)
- **Confidence:** medium-high
- **Alternative:** vision models, prompting, frame selection, or image resolution may have been inadequate; better multimodal integration could reverse the result.
- **Would weaken/overturn:** controlled current-model tests demonstrating consistent task improvement from vision under equal budget.
- **Non-implication:** visual sensing is unnecessary.

## EG-CLM-017 — High-level reasoning cannot compensate indefinitely for unreliable state and actuation

**Claim:** Minecraft-completion experiments identify pathfinding, state freshness, synchronization, and basic tool interaction as hard ceilings: a capable planner still fails when low-level observations or actions are stale, inaccurate, or brittle.

- **Status:** `SUPPORTED_WITH_LIMITS`
- **Evidence:** `TRANSCRIPT_DERIVED`, project context
- **Source:** [How Can AI Reliably Beat Minecraft Without Help?](https://www.youtube.com/watch?v=Wh4abvcUj8Q)
- **Confidence:** medium-high
- **Alternative:** an end-to-end model with sufficient interaction data could learn to compensate for noisy primitives rather than requiring deterministic abstractions.
- **Would weaken/overturn:** matched tests showing planner improvements alone overcome the same state/actuation failures.
- **Portfolio implication:** report planner, observer, synchronizer, and actuator performance separately.

## EG-CLM-018 — `fractalsearch` is weak recursive improvement of an external artifact

**Claim:** `fractalsearch` asks an agent to iteratively modify code for a Mandelbrot approximation, evaluate the result, retain improvements, and continue. The changing object is an external program under a fixed harness, not the model's core weights or objective generator.

- **Status:** `SUPPORTED`
- **Evidence:** `CREATOR_DIRECT`, repository implementation
- **Sources:**
  - [fractalsearch](https://github.com/MaxRobinsonTheGreat/fractalsearch)
  - [Recursive Self-improvement](https://www.youtube.com/watch?v=t7_ZXgfJVG8)
- **Confidence:** high
- **Alternative:** prompt/tool/history changes during repeated runs may indirectly change the effective optimizer, making the boundary less static than stated.
- **Would weaken/overturn:** implementation evidence that the agent autonomously modifies its evaluator, model, or persistent optimization policy.
- **Terminology requirement:** type self-improvement by the object changed: code, prompt, policy, tool, model, objective, or evaluator.

## EG-CLM-019 — Incumbent preservation and rollback are structural parts of autonomous improvement

**Claim:** The recursive-search loop only remains useful when each candidate is evaluated against an incumbent and regressions can be rejected or reverted.

- **Status:** `ANALYST_INFERENCE`
- **Evidence:** `CREATOR_DIRECT`, implementation pattern, `ANALYST_SYNTHESIS`
- **Sources:** fractalsearch/autoresearch lineage, AgentsOfEmpires tournament workflow
- **Confidence:** high
- **Alternative:** population-based or novelty-search systems may preserve diversity without one incumbent/revert relation.
- **Would weaken/overturn:** an alternative search architecture demonstrating equal safety and progress without rollback or retained prior artifacts.

## EG-CLM-020 — A scalar evaluator invites metric gaming and incomplete progress

**Claim:** An agent optimizing one measured score can improve that score while degrading readability, robustness, generalization, resource use, or scientific validity.

- **Status:** `ANALYST_INFERENCE`
- **Evidence:** recursive-search observations, established Goodhart-style concern, multiobjective omissions in toy projects
- **Confidence:** high as a risk; not proven as the dominant failure in every project
- **Alternative:** carefully designed scalar objectives can encode all material constraints or use hard feasibility gates around one optimization target.
- **Would weaken/overturn:** adversarial testing demonstrating that the evaluator and hard constraints fully track the desired outcome over out-of-distribution candidates.
- **Required control:** negative tests, held-out environments, multiobjective ledger, and human-review sampling.

## EG-CLM-021 — AgentsOfEmpires has stronger experimental plumbing than its scientific claim

**Claim:** The AgentsOfEmpires repository includes heartbeats, status JSON, screenshots, game recordings, parsed events, strategy archives, smoke tests, and tournament orchestration, while the creator explicitly characterizes the resulting strategy improvement and repository quality modestly.

- **Status:** `SUPPORTED`
- **Evidence:** `CREATOR_DIRECT`, `PRIMARY_TECHNICAL`
- **Sources:**
  - [AgentsOfEmpires](https://github.com/MaxRobinsonTheGreat/AgentsOfEmpires)
  - [AI plays Age of Empires II](https://www.youtube.com/watch?v=ZBdAe3ZwKds)
- **Confidence:** high
- **Alternative:** committed tooling may not reproduce the recorded run because it depends on GUI state, image templates, local game versions, and untracked artifacts.
- **Would weaken/overturn:** clean-machine reproduction failing or missing the documented artifact chain.
- **Portfolio implication:** copy the evidence discipline, not the headline claim.

## EG-CLM-022 — GUI-driven evaluation requires observability beyond pass/fail

**Claim:** Real GUI environments need heartbeats, screenshots, error captures, recordings, parsed event traces, and environment/version declarations because the same test can fail through perception, timing, state, or actuator drift.

- **Status:** `ANALYST_INFERENCE`
- **Evidence:** AgentsOfEmpires and Minecraft source patterns; portfolio journey tooling
- **Confidence:** high
- **Alternative:** sufficiently instrumented in-process APIs may make visual artifacts redundant for some applications.
- **Would weaken/overturn:** fault-localization studies showing pass/fail plus structured logs recover equivalent diagnostic information at lower cost.

## EG-CLM-023 — Open-ended prompts create activity without guaranteeing cumulative progress

**Claim:** Repeated “act forever” instructions can generate novelty, but without ownership, acceptance oracles, checkpoints, resource limits, and conflict handling they do not guarantee cumulative artifact quality.

- **Status:** `SUPPORTED_WITH_LIMITS`
- **Evidence:** direct prompts plus Chaos observations; `ANALYST_SYNTHESIS`
- **Confidence:** high for the bounded claim
- **Alternative:** open-ended systems with implicit environmental selection may accumulate progress without explicit project governance.
- **Would weaken/overturn:** long-run controlled experiments where minimally governed agents consistently improve held-out quality while structured controls do worse.

## EG-CLM-024 — More actors alter the problem, not merely execution width

**Claim:** Adding ants, organisms, game agents, or coding agents creates new interaction edges, shared-resource contention, interference, and collective dynamics. Agent count is therefore an independent causal variable, not just a throughput knob.

- **Status:** `ANALYST_INFERENCE`
- **Evidence:** Turmites, LifeEngine, Chaos, MineCollab
- **Confidence:** high
- **Alternative:** with perfect task partitioning and isolated state, additional actors may approximate linear independent capacity.
- **Would weaken/overturn:** broad benchmark evidence showing interaction-neutral scaling under realistic shared-state workloads.

## EG-CLM-025 — Environment, tools, tests, and evaluators are part of agent architecture

**Claim:** Agent behavior cannot be attributed to the model alone. Observation format, action abstraction, state synchronization, environmental incentives, evaluator design, rollback, and coordination protocol materially determine outcomes.

- **Status:** `ANALYST_INFERENCE`
- **Evidence:** cross-source synthesis with strong support from Mindcraft, LifeEngine, fractalsearch, and AgentsOfEmpires
- **Confidence:** high
- **Alternative:** sufficiently general end-to-end models may internalize these interfaces and reduce architectural sensitivity.
- **Would weaken/overturn:** controlled experiments showing model choice explains nearly all variance after major environment/tool/evaluator changes.
- **Portfolio implication:** version and evaluate the complete agent–environment system.

## EG-CLM-026 — The creator corpus supports iterative rule-space design, not laissez-faire emergence

**Claim:** The most defensible philosophical synthesis is that Max repeatedly designs a substrate, observes its consequences, and revises rules or selection pressure. The work does not support abandoning boundaries and hoping useful order appears.

- **Status:** `ANALYST_INFERENCE`
- **Evidence:** entire Wave 1 corpus
- **Confidence:** medium-high
- **Alternative A:** the unity is chiefly aesthetic/pedagogical rather than an engineering philosophy.
- **Alternative B:** the corpus primarily argues for open-ended exploration, with governance added only when projects fail.
- **Alternative C:** the examples better support hierarchy and deterministic infrastructure than emergence.
- **Would weaken/overturn:** complete transcript review showing the creator consistently endorses uncontrolled autonomy or rejects iterative intervention.

## EG-CLM-027 — Artificial-life terminology is currently under-specified in the corpus record

**Claim:** Genetic optimization, evolving digital organisms, and life-like local-rule dynamics are distinct mechanisms and should not be collapsed into one “evolutionary” category.

- **Status:** `PROVISIONAL`
- **Evidence:** secondary/transcript-derived notes for the 2026 `Artificial Life` video plus direct project differences
- **Source:** [Artificial Life](https://www.youtube.com/watch?v=2g-CrQfYNtE)
- **Confidence:** medium
- **Alternative:** the video may intentionally define an inclusive family rather than strict mechanism classes.
- **Would weaken/overturn:** creator-controlled transcript showing a different taxonomy.
- **Promotion requirement:** direct description/script/transcript and linked primary references.

## EG-CLM-028 — The current public count is 74 videos, but Wave 1 is not a complete channel census

**Claim:** Current external indexes report 74 channel videos; this wave analyzes selected anchors and direct project sources rather than claiming complete inventory or transcript coverage.

- **Status:** `SUPPORTED_WITH_LIMITS`
- **Evidence:** `SECONDARY_INDEX`, current search results
- **Confidence:** medium-high for current count; low as a permanent identifier
- **Alternative:** Shorts, streams, deleted/private entries, or index lag can make the visible count differ from the uploads playlist.
- **Would weaken/overturn:** official YouTube Data API enumeration returning a different reconciled result.
- **Required next step:** resolve immutable channel ID and uploads playlist through the documented API, preserving gaps.

---

## Cross-claim dependency map

```text
EG-CLM-001 creator through-line
  ├── EG-CLM-002 local-to-global behavior
  │     ├── EG-CLM-003 layered emergence
  │     ├── EG-CLM-004 execution as understanding
  │     └── EG-CLM-005 universality ≠ control
  ├── EG-CLM-007 endogenous selection
  │     ├── EG-CLM-008 controller choice
  │     └── EG-CLM-010 representation shapes search
  ├── EG-CLM-011 weak coordination treatment
  │     ├── EG-CLM-012 destructive interference
  │     ├── EG-CLM-023 activity ≠ progress
  │     └── EG-CLM-024 actor count changes dynamics
  ├── EG-CLM-013 negative agent-count scaling
  │     ├── EG-CLM-014 communication ablation
  │     ├── EG-CLM-015 abstraction isolates variable
  │     └── EG-CLM-016 sensing ≠ grounding
  ├── EG-CLM-017 planner cannot erase actuator ceiling
  ├── EG-CLM-018 weak recursive improvement
  │     ├── EG-CLM-019 incumbent/rollback
  │     └── EG-CLM-020 evaluator gaming
  └── EG-CLM-021 experimental plumbing
        └── EG-CLM-022 GUI observability

EG-CLM-025 whole-system agent architecture
  ← synthesis of EG-CLM-007, 013–022, 024

EG-CLM-026 iterative rule-space design
  ← synthesis of EG-CLM-001–025
```

## Promotion queue

Claims requiring the next evidence wave before being used in project ADRs:

| Claim        | Missing evidence                                                            |
| ------------ | --------------------------------------------------------------------------- |
| `EG-CLM-003` | Creator-controlled transcript or script for layered emergence wording       |
| `EG-CLM-008` | Source/commit or creator-controlled script for state-machine decision       |
| `EG-CLM-012` | Original run artifacts or creator-controlled transcript with exact examples |
| `EG-CLM-016` | Current controlled multimodal ablation at a pinned revision                 |
| `EG-CLM-017` | Original challenge-world artifacts and direct transcript                    |
| `EG-CLM-020` | Candidate/run-level evidence of evaluator exploitation in these projects    |
| `EG-CLM-027` | Creator-controlled `Artificial Life` text and primary references            |
| `EG-CLM-028` | Official API uploads-playlist census                                        |

No `PROVISIONAL` claim may independently justify a product-code change.
