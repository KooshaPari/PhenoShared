# Emergent Garden Creator Chronology — Wave 1

**Campaign:** `eg-nested-corpus-2026-09`  
**Status:** partial chronology, not a complete upload census  
**Observation date:** 2026-09-04

## Purpose

This chronology tracks how the creator's working method changes across projects. It is not merely a release list. The important sequence is the movement from compact artificial-life substrates, through neural and evolutionary search, into embodied LLM agents, multi-agent coordination, recursive artifact improvement, and real-game evaluation.

Dates below are backed by public video indexes, creator-controlled repositories, creator site pages, or public Patreon post metadata. Patreon posts are evidence of project chronology and supporting material; they are not assumed to correspond one-to-one with public YouTube uploads.

## Phase 0 — Pre-channel and historical foundations

### 2018–2020: evolutionary toys and persistent environments

Creator-owned repositories from this period include `EvolutionSimulator`, `FruitFly`, `Derelict`, `KillerKlicker`, `tsp-genetic`, `AntiGoat`, `Holodeck`, `RRT`, and `simple-classifier`.

The strongest surviving lineage is:

```text
EvolutionSimulator
→ LifeEngine
→ evolved perception/controller experiments
```

The key pattern is already present: define a compact world, allow repeated local action, preserve state over time, and inspect behavior that was not individually authored.

**Evidence:**

- <https://github.com/MaxRobinsonTheGreat/EvolutionSimulator>
- <https://github.com/MaxRobinsonTheGreat/LifeEngine>

### 2021: neural local rules

`What are neural cellular automata?` and `NeuralPatterns` shift the substrate from hand-written state transitions to a learned homogeneous local update: a small convolution and activation repeatedly applied to each pixel.

This matters because the learned rule remains local while the visible behavior becomes global and persistent. It is an early bridge between cellular automata, neural networks, morphogenesis, and later agent systems.

**Evidence:**

- <https://www.youtube.com/watch?v=3H79ZcBuw4M>
- <https://github.com/MaxRobinsonTheGreat/NeuralPatterns>
- <https://neuralpatterns.io/>

## Phase 1 — Search over representations

### 2022: evolutionary selection applied to generative models

Public Patreon metadata records `Stable Diffusion Evolution` on 2022-09-06 and `Thought Breeder` on 2022-12-04. The creator repository `StableDiffEvolution` preserves the corresponding technical lineage.

The shift is not from evolution to AI. It is from evolving explicit organisms to evolving representations, prompts, images, and latent artifacts.

**Evidence:**

- <https://github.com/MaxRobinsonTheGreat/StableDiffEvolution>
- <https://www.patreon.com/emergentgarden>

### 2023: selection becomes both technical and participatory

Public Patreon metadata includes `AI Art That Evolves` on 2023-01-29, neural-network material in November, and thought-evolution material in December. Creator repositories such as `mandelbrotnn`, `ManimApproximations`, and `CodeEvolver` expose three recurring search modes:

1. gradient-based fitting;
2. population-based mutation and selection;
3. human aesthetic selection over a generative representation.

This is the direct prehistory of `Gradient Descent vs Evolution` and the later hyperdimensional function-tree projects.

**Evidence:**

- <https://github.com/MaxRobinsonTheGreat/mandelbrotnn>
- <https://github.com/MaxRobinsonTheGreat/ManimApproximations>
- <https://github.com/MaxRobinsonTheGreat/CodeEvolver>
- <https://www.patreon.com/emergentgarden>

## Phase 2 — Embodied agents and environmental grounding

### 2024: Mindcraft becomes the dominant agent laboratory

Public Patreon metadata shows a rapid sequence:

- `AI Talks To AI in Minecraft` — 2024-10-19;
- `4 AIs Survive 10 Days in Minecraft` — 2024-10-28;
- `GPT O1 Preview: Building a Villager Utopia` — 2024-11-11;
- `AI Plays Minecraft Forever` — 2024-11-23.

This is a substantive change in the experimental unit. The system is no longer only a rule or genotype. It is an agent with observations, memory, tools, a changing world, and long-horizon failure modes.

The creator's old `MaxRobinsonTheGreat/mindcraft` repository and the current `mindcraft-bots/mindcraft` repository provide lineage evidence. The current project warns that generated code can be unsafe, disables code writing by default, and treats sandboxing as risk reduction rather than proof of safety.

**Evidence:**

- <https://github.com/MaxRobinsonTheGreat/mindcraft>
- <https://github.com/mindcraft-bots/mindcraft>
- <https://www.patreon.com/emergentgarden>

## Phase 3 — Coordination, scaffolding, and evidence

### 2025-03-01: Gradient Descent vs Evolution

The video makes search topology itself the object of explanation. Gradient descent exploits local derivative information; evolutionary search tolerates discontinuity and arbitrary mutation but spends more evaluations.

Portfolio consequence: a single optimization ideology is unjustified. The right search method depends on representation, observability, evaluator cost, smoothness, and rollback.

**Evidence:** <https://www.youtube.com/watch?v=Anc2_mnb3V8>

### 2025-04-05: Vision and Vibe Coding — Mindcraft Update

The project investigates richer sensing and generated actions. The important negative result is that more raw perception is not equivalent to better grounding. Structured state and reliable action abstractions can outperform a more human-like sensory channel.

**Evidence:** <https://www.youtube.com/watch?v=iDJ6GrHNoDs>

### 2025-05-10: Official Mindcraft Paper

A creator post points to `Collaborating Action by Action: A Multi-agent LLM Framework for Embodied Reasoning`. The paper formalizes a move away from loosely communicating agents toward action-level collaboration and controlled experiments.

This is a key contradiction to any simplistic reading of the channel as advocacy for unconstrained swarm emergence. The empirical work adds central structure when unstructured communication performs poorly.

**Evidence:**

- <https://www.patreon.com/posts/official-paper-128570700>
- <https://arxiv.org/abs/2504.17950>
- <https://github.com/mindcraft-bots/mindcraft>

### 2025-06-07: Langton's Ants and Turing Machines

A minimal local state machine is used to demonstrate that tiny rule sets can support unexpectedly rich computation. The associated `turmites` repository preserves presets and implementation code.

**Evidence:**

- <https://www.youtube.com/watch?v=7x9J7rsLC50>
- <https://github.com/MaxRobinsonTheGreat/turmites>

### 2025-07-26: The Chaos of AI Agents

The experiment gives agents broad autonomy over shared artifacts. The result is not stable collective intelligence. It is a mix of creation, overwriting, interference, opportunistic coordination, and unbounded activity.

The accompanying prompt files make the mechanism unusually explicit: agents repeatedly inspect and modify a shared artifact, communicate through append-oriented files, and continue without a terminating task.

**Evidence:**

- <https://www.youtube.com/watch?v=2YYjPs8t8MI>
- <https://github.com/MaxRobinsonTheGreat/agent_prompts>

### 2025-08-09: Evolving Brains in the Life Engine

The Life Engine lineage gains mutable sensing and controller behavior. This is not equivalent to an LLM agent: the controller is intentionally compact and strongly coupled to the environment's endogenous survival pressures.

**Evidence:**

- <https://www.youtube.com/watch?v=DksO3mqh0kg>
- <https://github.com/MaxRobinsonTheGreat/LifeEngine>

### 2025-09-21: Minecraft reliability challenge

The focus shifts from interesting behavior to repeatable task completion. Planning quality alone is insufficient when state is stale, pathfinding is brittle, and low-level actions fail.

**Evidence:** <https://www.youtube.com/watch?v=Wh4abvcUj8Q>

### 2025-11-22: Emergent Complexity

The channel's implicit method is stated directly: choose building blocks and rules, let interactions unfold, and treat execution as necessary because complex consequences are not always compressible into prior reasoning.

The surrounding corpus prevents a romantic reading. Making emergence useful requires observability, selection, intervention, and containment.

**Evidence:** <https://www.youtube.com/watch?v=0HqUYpGQIfs>

### 2025-12-20: Creatures in Higher Dimensions

`hyperdimensions` turns function trees into mutable generative phenotypes. It includes direct function editing, random generation, saved exemplars, Biomorphs, Picbreeder, image evolution, and symbolic-regression experiments.

The recurring method is search over a representation that can express both recognizable structure and surprising variation.

**Evidence:**

- <https://www.youtube.com/watch?v=349r0xJFGNw>
- <https://github.com/MaxRobinsonTheGreat/hyperdimensions>

## Phase 4 — Recursive engineering and real environments

### 2026-01-24: Nature Sanctuary in Stardew Valley

The game becomes a constrained design environment rather than merely a task benchmark. This extends the channel's use of existing worlds as rich evaluators of agent behavior.

**Evidence:** <https://www.youtube.com/watch?v=LxVQra1Z_jA>

### 2026-02-28: Evolution in Higher Dimensions

The higher-dimensional representation is subjected to explicit evolutionary search. The representation, mutation operators, evaluator, and human selection pressure jointly determine what can emerge.

**Evidence:** <https://www.youtube.com/watch?v=DB-TD3s3MZ0>

### 2026-03-21: AI for War in Minecraft

The Mindcraft line is applied to competitive multi-agent behavior. This is a frontier node rather than a completed Wave 1 analysis; direct text and run artifacts remain outstanding.

**Evidence:** <https://www.youtube.com/watch?v=Ipcr5heLOJ8>

### 2026-05-23: The Brain Eating Machines

This remains a frontier node pending direct text and implementation mapping. It is retained because its title and placement suggest a continuation of embodied artificial-life/controller work, but no architectural claim is accepted from the title alone.

**Evidence:** <https://www.youtube.com/watch?v=kVjhV-In25c>

### 2026-06-13: Recursive Self-improvement

`fractalsearch` turns a toy ML problem into an artifact-centered research loop. The human changes the research prompt rather than directly changing code; the agent changes code, runs it, and is evaluated on an external Mandelbrot-fitting objective.

The creator explicitly says the system is adapted from `karpathy/autoresearch`, all project code was AI-generated, and the repository is not being maintained as a general product. That sharply limits any inference from successful footage to production readiness.

**Evidence:**

- <https://www.youtube.com/watch?v=t7_ZXgfJVG8>
- <https://github.com/MaxRobinsonTheGreat/fractalsearch>
- <https://github.com/karpathy/autoresearch>

### 2026-07-18: Artificial Life

The channel returns to artificial life after the agent-heavy period. This supports continuity rather than a clean topic pivot: artificial organisms, neural local rules, LLM agents, and recursive code search are treated as different substrates for the same experimental question.

Direct transcript and implementation mapping remain incomplete.

**Evidence:**

- <https://www.youtube.com/watch?v=2g-CrQfYNtE>
- <https://www.patreon.com/emergentgarden/posts/artificial-life-163746134>

### 2026-08-15: AI plays Age of Empires II

`AgentsOfEmpires` exposes the full real-environment loop:

```text
mutate strategy
→ install it into the game
→ drive the foreground GUI
→ preserve heartbeat, results, errors, screenshots, and recordings
→ score tournaments
→ retain the strongest incumbent
```

It also exposes the operational cost: the automation controls the real cursor, cannot run as a normal background task, relies on screen templates, and is described by its author as footage-oriented and messy.

**Evidence:**

- <https://www.youtube.com/watch?v=ZBdAe3ZwKds>
- <https://github.com/MaxRobinsonTheGreat/AgentsOfEmpires>

## Supported longitudinal interpretation

Across the chronology, the recurring object is not a specific model class. It is an executable search space:

```text
representation
+ local or agent-level operators
+ environment
+ persistence
+ evaluator or selection pressure
+ repeated execution
```

The creator repeatedly changes one or more terms:

- hand-written rules become learned updates;
- endogenous survival becomes explicit objective scoring;
- compact organisms become tool-using language agents;
- simulation becomes an existing game or real GUI;
- aesthetic human choice becomes automated tournaments;
- single artifacts become shared multi-agent workspaces;
- manual iteration becomes recursive code modification.

## Strongest counter-interpretations

### The unity may be methodological rather than philosophical

The corpus clearly shares an experimental method. It does not yet prove one accepted metaphysics, organizational theory, or universal architecture.

### The media format may select for emergence

Unexpected visual behavior makes compelling videos. That selection pressure can overrepresent generative demonstrations relative to routine engineering, maintenance, and negative results.

### Later scaffolding partially rejects earlier openness

Mindcraft's action-level collaboration, deterministic tasks, structured state, blocked actions, and safety switches are not merely implementations of open-ended emergence. They are corrections to failure modes observed in looser systems.

### Production applicability is uneven

The research loops are highly relevant to Benchora, ResearchLedger, phenotype-journeys, Tracera, Agentora, Civis, and physical-engineering iteration. They do not automatically justify autonomous infinite loops, shared mutable workspaces, or foreground GUI control in production systems.

## Next chronological work

1. Reconcile the official uploads playlist rather than treating public indexes or Patreon posts as the channel census.
2. Acquire direct descriptions and permitted transcript text for all 2024 Mindcraft videos.
3. Map Patreon raw-footage/project posts to public releases without assuming one-to-one identity.
4. Recover the exact transition from `MaxRobinsonTheGreat/mindcraft` to `mindcraft-bots/mindcraft`.
5. Expand the 2022–2023 generative-evolution lineage through `StableDiffEvolution`, `CodeEvolver`, and `ManimApproximations`.
6. Determine whether the 2026 artificial-life return changes or merely restates the earlier theory.
