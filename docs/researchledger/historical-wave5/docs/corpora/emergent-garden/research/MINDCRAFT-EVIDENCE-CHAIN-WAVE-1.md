# Mindcraft Evidence Chain — Wave 1

**Campaign:** `eg-nested-corpus-2026-09`  
**State:** bounded evidence chain; repository lineage and full experiment reproduction remain incomplete

## Why Mindcraft is central

Mindcraft is the channel's clearest transition from visually emergent toy systems to agents that must perceive, remember, plan, act, recover, and coordinate inside a persistent environment.

It is also the strongest correction to a romantic interpretation of the channel. The public evidence does not support “add agents and let intelligence emerge.” It supports a more conditional claim:

```text
agent capability
+ environment grounding
+ reliable action abstractions
+ explicit task/evaluation contracts
+ controlled coordination topology
+ preserved execution evidence
```

## Source chain

### Historical creator repository

- <https://github.com/MaxRobinsonTheGreat/mindcraft>

This is retained as a historical creator-controlled node. Wave 1 has not yet proven the exact Git ancestry, transfer, or extraction relationship to the current organization repository.

### Current implementation repository

- <https://github.com/mindcraft-bots/mindcraft>

The current repository identifies the system as Minecraft AI built with LLMs and Mineflayer. It exposes model/provider profiles, separate chat/code/vision/embedding roles, deterministic task files, initial inventories, target items, timeouts, blocked actions, agent counts, and task depth.

It also preserves an important security boundary:

- model-written code can execute on the operator's computer;
- coding is disabled by default;
- prompt injection remains a risk;
- containerization is recommended as risk reduction, not a guarantee;
- public-server use with coding enabled is explicitly discouraged.

### Primary paper

- <https://arxiv.org/abs/2504.17950>
- `Collaborating Action by Action: A Multi-agent LLM Framework for Embodied Reasoning`

The paper is linked from the current implementation repository and creator publication material. Its central research direction is action-level collaboration in an embodied environment. Wave 1 treats this as primary evidence that coordination topology is an experimental variable rather than assuming loosely communicating agents are superior.

### Public video/release sequence

The current chronology contains these Mindcraft-related nodes:

- `AI Talks To AI in Minecraft` — creator-post chronology, 2024-10-19;
- `4 AIs Survive 10 Days in Minecraft` — creator-post chronology, 2024-10-28;
- `GPT O1 Preview: Building a Villager Utopia` — creator-post chronology, 2024-11-11;
- `AI Plays Minecraft Forever` — creator-post chronology, 2024-11-23;
- `Vision and Vibe Coding | Mindcraft Update` — <https://www.youtube.com/watch?v=iDJ6GrHNoDs>;
- official Mindcraft paper publication material — 2025-05;
- Minecraft reliability challenge — <https://www.youtube.com/watch?v=Wh4abvcUj8Q>;
- `AI for War in Minecraft` — <https://www.youtube.com/watch?v=Ipcr5heLOJ8>.

Creator-post dates are chronology evidence. They are not assumed to be exact public YouTube release dates or one-to-one video identities until the official upload inventory is reconciled.

## Mechanism map

### Environment as external state

Minecraft supplies durable state and consequences not authored by the agent runtime. This creates a stronger grounding test than evaluating text against text.

**Failure alternative:** the environment can also add noise. Pathfinding, latency, partial observability, stale state, and low-level action failures can dominate the model's reasoning quality.

### Structured action layer

Mineflayer and task-specific actions reduce the gap between a language-level plan and game mechanics.

**Failure alternative:** generated code or overly general actions expand capability while increasing injection, validation, and sandbox risk.

### Profiles and examples as policy shaping

Profiles configure model roles, prompts, and examples. Embeddings can retrieve examples, with word-overlap fallback when an embedding backend is unavailable.

**Failure alternative:** profile tuning can encode benchmark-specific shortcuts or hide that the environment/task interface, rather than the model, is responsible for the observed gain.

### Task files as experimental contracts

Task JSON records goal item, quantity, initial inventory, agent count, target, depth, timeout, blocked actions, and missing dependencies.

This is directly reusable as a research pattern: environment and evaluator configuration must be versioned beside agent configuration.

### Coordination topology as an intervention

The paper's action-level collaboration framing implies that when and how agents share state/actions matters. “More communication” and “more agents” are not monotonic improvements.

### Safety switches as part of the architecture

`allow_insecure_coding` is off by default. That is not incidental documentation. It is evidence that capability exposure must be explicit and reversible.

## Supported claims

### MC-01 — Embodiment makes actuation reliability part of intelligence evaluation

**Status:** supported.  
**Evidence:** Mindcraft task/runtime structure and the channel's Minecraft reliability work.  
**Alternative:** poor performance may measure Mineflayer/pathfinding/action design more than model reasoning.

### MC-02 — Multi-agent topology requires controlled comparison

**Status:** supported as a research requirement.  
**Evidence:** primary paper framing plus deterministic agent-count/task fields.  
**Alternative:** gains may depend on task decomposition or model allocation rather than action-level collaboration itself.

### MC-03 — Structured state can be more useful than human-like raw perception

**Status:** provisional.  
**Evidence:** the Vision/Vibe project line and current separation of vision from ordinary model/action configuration.  
**Alternative:** an improved multimodal model or better observation compression could reverse the result.

### MC-04 — Generated actions require a stronger security boundary than fixed tools

**Status:** strongly supported.  
**Evidence:** current repository warning, disabled-by-default coding, injection warning, and container recommendation.  
**Alternative:** a capability-safe generated program representation could retain flexibility without general host execution, but that is not demonstrated here.

### MC-05 — Persistent environments expose failures hidden by static benchmarks

**Status:** supported.  
**Evidence:** long-horizon survival, construction, and challenge framing.  
**Alternative:** repeatable static tasks remain necessary to isolate causes and compare systems fairly.

## Portfolio translations

### Agentora

Treat coordination mode, observation schema, action abstraction, capability exposure, budget, and checkpoint policy as first-class runtime contracts. Do not infer that Agentora needs Minecraft-specific code.

### Benchora

Own controlled comparisons across:

- single agent;
- independent parallel agents;
- shared blackboard;
- message-based delegation;
- action-level collaboration;
- manager/worker topology.

Hold model, tasks, tools, retries, timeouts, and evaluator constant where possible.

### phenotype-journeys

Capture environment-facing journeys and hard assertions. A soft language-model judge alone is insufficient for actuation correctness.

### SessionLedger

Preserve run configuration, action stream, observations, checkpoints, tool/code artifacts, intervention events, and terminal outcome.

### Tracera

Link claim → task configuration → observation → action → environment result → evaluator → decision. Distinguish model failure, stale state, tool failure, pathfinding failure, permission denial, and evaluator error.

### Helios family

The relevant lesson is not “add more coding agents.” It is to evaluate coordination topology, generated-code permissions, shared-state conflicts, and rollback under identical code tasks. Identity conflicts in HeliosLab and forgecode remain independent blockers.

## Experiment contract derived from Mindcraft

### EG-EXP-MC-01 — Coordination topology under constant task conditions

**Question:** Which topology improves completed-task correctness without increasing destructive interference, cost, or unrecoverable state?

**Independent variable:** coordination topology.

**Topologies:**

1. one agent;
2. independent parallel attempts with best-of selection;
3. shared append-only blackboard;
4. direct messages/delegation;
5. action-level shared planning;
6. manager/worker hierarchy.

**Controls:**

- same task corpus;
- same model/provider versions;
- same tool and filesystem permissions;
- same context and cost budgets;
- same timeout/retry policy;
- same starting repository/environment state;
- same evaluator and hidden tests;
- same checkpoint interval.

**Measures:**

- task success and hidden-test correctness;
- destructive interference and conflicting writes;
- duplicated work;
- stale-state actions;
- operator interventions;
- recovery success;
- tokens, cost, latency, and wall time;
- evidence completeness;
- security or permission violations.

**Negative controls:**

- inject one stale observation;
- inject one failing tool result;
- remove communication while retaining agent count;
- retain communication while reducing agents to one;
- randomize agent identifiers to detect role-name effects.

**Abort conditions:**

- action outside declared capability scope;
- corrupted shared state without recoverable checkpoint;
- evaluator leakage;
- uncontrolled recursive agent creation;
- unbounded generated-code execution.

## Remaining evidence work

1. establish historical/current Mindcraft Git lineage;
2. preserve exact paper version and experiment tables;
3. map task files used in the paper to current repository paths;
4. recover permitted descriptions and direct text for the 2024–2026 video sequence;
5. distinguish model, action-library, observation, coordination, and evaluator contributions;
6. reproduce at least one bounded task across multiple topologies;
7. record failed and null results, not only successful footage.
