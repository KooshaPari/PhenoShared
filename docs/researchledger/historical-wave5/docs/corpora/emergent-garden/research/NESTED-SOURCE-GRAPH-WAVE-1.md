# Emergent Garden Nested Corpus — Wave 1 Source Graph

**Campaign:** `eg-nested-corpus-2026-09`  
**Wave:** 1  
**Graph status:** partial direct-source graph plus prioritized recursive frontier

This document records what was actually discovered in Wave 1, how the sources relate, why some links were expanded, and why others were stopped. It is not the final channel inventory.

## 1. Root nodes

| Node ID             | Type                 | Canonical URI                                    | Role                                                         | Evidence status                                                                               |
| ------------------- | -------------------- | ------------------------------------------------ | ------------------------------------------------------------ | --------------------------------------------------------------------------------------------- |
| `EG-ROOT-YT`        | YouTube channel      | `https://www.youtube.com/@EmergentGarden/videos` | Creator video corpus root                                    | Current external indexes indicate 74 videos; official uploads-playlist reconciliation pending |
| `EG-ROOT-SITE`      | Creator site         | `https://emergentgarden.io/`                     | Creator identity, project gallery, and philosophical framing | Direct creator source                                                                         |
| `EG-ROOT-GH`        | GitHub account       | `https://github.com/MaxRobinsonTheGreat`         | Creator-controlled implementation lineage                    | 30 public repositories enumerated in Wave 1                                                   |
| `EG-ROOT-PATREON`   | Patreon creator page | `https://www.patreon.com/emergentgarden`         | Chronological title/project discovery                        | Discovery only; not treated as canonical video inventory                                      |
| `EG-ROOT-MINDCRAFT` | Project organization | `https://github.com/mindcraft-bots`              | Current Mindcraft/MineCollab implementation lineage          | Direct project source                                                                         |

## 2. High-information video nodes

| Node ID                 | Video                                                                                           |       Date | Direct implementation/source edges                                         | Wave status                                         |
| ----------------------- | ----------------------------------------------------------------------------------------------- | ---------: | -------------------------------------------------------------------------- | --------------------------------------------------- |
| `EG-VID-EMERGENCE`      | [Emergent Complexity](https://www.youtube.com/watch?v=0HqUYpGQIfs)                              | 2025-11-22 | cellular automata/Wolfram references; creator projects                     | Anchor analyzed                                     |
| `EG-VID-NCA`            | [What are neural cellular automata?](https://www.youtube.com/watch?v=3H79ZcBuw4M)               | 2021-11-21 | `NeuralPatterns`; `webgl-convolution`                                      | Anchor analyzed                                     |
| `EG-VID-LIFE-BRAINS`    | [Evolving Brains in the Life Engine](https://www.youtube.com/watch?v=DksO3mqh0kg)               | 2025-08-09 | `LifeEngine`; original `EvolutionSimulator`                                | Anchor analyzed; controller rationale provisional   |
| `EG-VID-TURMITES`       | [Langton's Ants and Turing Machines](https://www.youtube.com/watch?v=7x9J7rsLC50)               | 2025-06-07 | `turmites`; interactive demo; Wolfram/MathWorld/Turing-machine sources     | Anchor analyzed                                     |
| `EG-VID-GRADIENT`       | [Gradient Descent vs Evolution](https://www.youtube.com/watch?v=Anc2_mnb3V8)                    | 2025-03-01 | `hillclimbers`; `mandelbrotnn`; `ManimApproximations`; optimization papers | Anchor analyzed                                     |
| `EG-VID-CHAOS`          | [The Chaos of AI Agents](https://www.youtube.com/watch?v=2YYjPs8t8MI)                           | 2025-07-26 | `agent_prompts`; shared-image/shared-file experiment                       | Anchor analyzed; original run artifacts pending     |
| `EG-VID-VISION`         | [Vision and Vibe Coding — Mindcraft Update](https://www.youtube.com/watch?v=iDJ6GrHNoDs)        | 2025-04-05 | Mindcraft; MineCollab paper                                                | Anchor analyzed                                     |
| `EG-VID-MC-RELIABILITY` | [How Can AI Reliably Beat Minecraft Without Help?](https://www.youtube.com/watch?v=Wh4abvcUj8Q) | 2025-09-21 | Mindcraft/Mineflayer; challenge-world concept                              | Anchor analyzed; direct challenge artifacts pending |
| `EG-VID-RSI`            | [Recursive Self-improvement](https://www.youtube.com/watch?v=t7_ZXgfJVG8)                       | 2026-06-13 | `fractalsearch`; Karpathy `autoresearch`; `mandelbrotnn`                   | Anchor analyzed                                     |
| `EG-VID-ALIFE`          | [Artificial Life](https://www.youtube.com/watch?v=2g-CrQfYNtE)                                  | 2026-07-18 | creator artificial-life projects and literature                            | Discovery/provisional; direct text pending          |
| `EG-VID-HD-CREATURES`   | [Creatures In Higher Dimensions](https://www.youtube.com/watch?v=349r0xJFGNw)                   | 2025-12-20 | `hyperdimensions`                                                          | Anchor analyzed from code and creator-linked page   |
| `EG-VID-HD-EVOLUTION`   | [Evolution In Higher Dimensions](https://www.youtube.com/watch?v=DB-TD3s3MZ0)                   | 2026-02-28 | `hyperdimensions` evolution experiments                                    | Anchor analyzed; run methodology pending            |
| `EG-VID-AOE`            | [AI plays Age of Empires II](https://www.youtube.com/watch?v=ZBdAe3ZwKds)                       | 2026-08-15 | `AgentsOfEmpires`                                                          | Anchor analyzed                                     |
| `EG-VID-AI-WAR`         | [AI For War (in Minecraft)](https://www.youtube.com/watch?v=Ipcr5heLOJ8)                        | 2026-03-21 | Mindcraft lineage; multi-agent competition                                 | Inventory/frontier only                             |

## 3. Creator GitHub inventory

Wave 1 enumerated 30 public repositories owned by `MaxRobinsonTheGreat`. This is a GitHub account inventory, not proof that every repository belongs to the Emergent Garden media corpus.

### 3.1 Priority A — direct corpus implementations

| Repository                                                                          | Graph role                                      | Primary related concepts                                            | Expansion decision                |
| ----------------------------------------------------------------------------------- | ----------------------------------------------- | ------------------------------------------------------------------- | --------------------------------- |
| [`LifeEngine`](https://github.com/MaxRobinsonTheGreat/LifeEngine)                   | Cellular artificial-life simulator              | ecology, mutation, endogenous selection, state-machine brains       | Expanded                          |
| [`EvolutionSimulator`](https://github.com/MaxRobinsonTheGreat/EvolutionSimulator)   | Historical predecessor to LifeEngine            | lineage, simulation evolution                                       | Expand for history/delta          |
| [`NeuralPatterns`](https://github.com/MaxRobinsonTheGreat/NeuralPatterns)           | Neural cellular-automata web toy                | homogeneous local update, recurrent dynamics                        | Expanded                          |
| [`turmites`](https://github.com/MaxRobinsonTheGreat/turmites)                       | Langton/turmite simulator                       | state machines, universality, local-to-global dynamics              | Expanded                          |
| [`mandelbrotnn`](https://github.com/MaxRobinsonTheGreat/mandelbrotnn)               | Neural approximation of Mandelbrot set          | gradient optimization, infinite-detail target                       | Expanded                          |
| [`hillclimbers`](https://github.com/MaxRobinsonTheGreat/hillclimbers)               | Gradient-free neural optimization demo          | local mutation, evaluator search                                    | Expanded shallowly; sparse README |
| [`ManimApproximations`](https://github.com/MaxRobinsonTheGreat/ManimApproximations) | Visualization/animation source                  | optimization pedagogy                                               | Expanded shallowly                |
| [`fractalsearch`](https://github.com/MaxRobinsonTheGreat/fractalsearch)             | Agent-driven code improvement                   | weak RSI, incumbent, evaluator, rollback                            | Expanded                          |
| [`agent_prompts`](https://github.com/MaxRobinsonTheGreat/agent_prompts)             | Direct prompts for open-ended agent experiments | autonomy, shared state, coordination failure                        | Expanded                          |
| [`hyperdimensions`](https://github.com/MaxRobinsonTheGreat/hyperdimensions)         | Generative function/phenotype explorer          | representation, function trees, high-dimensional search             | Expanded                          |
| [`CodeEvolver`](https://github.com/MaxRobinsonTheGreat/CodeEvolver)                 | Source for evolvecode web project               | code evolution, online demo lineage                                 | Expand in Wave 2                  |
| [`StableDiffEvolution`](https://github.com/MaxRobinsonTheGreat/StableDiffEvolution) | Stable-diffusion evolution experiment           | human/aesthetic selection, generative search                        | Expand in Wave 2                  |
| [`AgentsOfEmpires`](https://github.com/MaxRobinsonTheGreat/AgentsOfEmpires)         | AoE II GUI/tournament automation                | real-environment evaluator, artifacts, heartbeat, strategy mutation | Expanded                          |
| [`mindcraft`](https://github.com/MaxRobinsonTheGreat/mindcraft)                     | Creator fork/history node for Mindcraft         | embodied agents, project lineage                                    | Expand against organization repo  |
| [`mineflayer-dev`](https://github.com/MaxRobinsonTheGreat/mineflayer-dev)           | Low-level Minecraft-agent development lineage   | action abstraction, actuator reliability                            | Expand selectively                |
| [`slopcity`](https://github.com/MaxRobinsonTheGreat/slopcity)                       | Shared-artifact agent experiment candidate      | collective generation, interference                                 | Expand in Wave 2                  |

### 3.2 Priority B — likely relevant historical or conceptual nodes

| Repository                                                                      | Likely role                          | Decision                                  |
| ------------------------------------------------------------------------------- | ------------------------------------ | ----------------------------------------- |
| [`tsp-genetic`](https://github.com/MaxRobinsonTheGreat/tsp-genetic)             | Early genetic-algorithm optimization | Expand for historical concept evolution   |
| [`FruitFly`](https://github.com/MaxRobinsonTheGreat/FruitFly)                   | Game/simulation candidate            | Inspect README/history before classifying |
| [`AntiGoat`](https://github.com/MaxRobinsonTheGreat/AntiGoat)                   | Game/agent project candidate         | Inspect for emergence or AI relevance     |
| [`Holodeck`](https://github.com/MaxRobinsonTheGreat/Holodeck)                   | Simulation/visual project candidate  | Inspect for creator lineage               |
| [`RRT`](https://github.com/MaxRobinsonTheGreat/RRT)                             | Planning algorithm candidate         | Expand only if linked from video/project  |
| [`simple-classifier`](https://github.com/MaxRobinsonTheGreat/simple-classifier) | ML learning history                  | Historical context only                   |
| [`gameofur`](https://github.com/MaxRobinsonTheGreat/gameofur)                   | Game implementation                  | Stop unless creator corpus links it       |
| [`Derelict`](https://github.com/MaxRobinsonTheGreat/Derelict)                   | Older game project                   | Stop unless relevant edge found           |
| [`KillerKlicker`](https://github.com/MaxRobinsonTheGreat/KillerKlicker)         | Older interactive project            | Stop unless relevant edge found           |

### 3.3 Priority C — currently incidental/account-history nodes

| Repository                                                                                              | Reason for stopping after inventory                    |
| ------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| [`creative_project_1`](https://github.com/MaxRobinsonTheGreat/creative_project_1)                       | No material campaign relation established              |
| [`SpookySpookers`](https://github.com/MaxRobinsonTheGreat/SpookySpookers)                               | No material campaign relation established              |
| [`MovieSearch`](https://github.com/MaxRobinsonTheGreat/MovieSearch)                                     | Generic application; no emergence/agent edge found     |
| [`MongoBurger`](https://github.com/MaxRobinsonTheGreat/MongoBurger)                                     | Generic application; no campaign edge found            |
| [`maxrobinsonthegreat.github.io`](https://github.com/MaxRobinsonTheGreat/maxrobinsonthegreat.github.io) | Historical site; inspect only for redirects/provenance |

## 4. Expanded nested subgraphs

### 4.1 Artificial-life lineage

```text
EG-ROOT-SITE
  ├─AUTHOR_DIRECT→ EG-VID-ALIFE
  ├─AUTHOR_DIRECT→ EG-VID-LIFE-BRAINS
  └─AUTHOR_DIRECT→ LifeEngine
                       ├─SUPERSEDES→ EvolutionSimulator
                       ├─IMPLEMENTATION→ cell/environment/reproduction/mutation rules
                       ├─CONTEXT→ evolutionary algorithms
                       └─CONTEXT→ state-machine controller literature
```

**Why expanded:** central creator theme, direct implementation, strong portfolio relevance.  
**Wave 2 frontier:** exact brain representation/mutation code; historical version delta; linked artificial-life literature; Lenia/Evoloop project nodes from creator site.

### 4.2 Cellular computation lineage

```text
EG-VID-EMERGENCE
  ├─PRIMARY_SOURCE→ Wolfram cellular-automata framing
  ├─CONTEXT→ Conway-style cellular automata
  └─AUTHOR_DIRECT→ EG-VID-TURMITES
                         ├─IMPLEMENTATION→ MaxRobinsonTheGreat/turmites
                         ├─CONTEXT→ Langton's ant
                         ├─PRIMARY_SOURCE→ Turing-machine/universality sources
                         └─EXTENSION→ multi-ant / evolved-rule experiments
```

**Why expanded:** direct bridge from philosophical thesis to executable state-transition systems.  
**Stop condition:** do not recursively ingest the general cellular-automata literature without a claim or contradiction requiring it.

### 4.3 Neural local-rule lineage

```text
EG-VID-NCA
  ├─IMPLEMENTATION→ NeuralPatterns
  │                    └─DEPENDENCY→ webgl-convolution
  ├─PRIMARY_SOURCE→ neural cellular-automata literature
  └─CONTEXT→ differentiable local update rules
```

**Wave 2 frontier:** identify exact paper/version inspirations and whether models are trained, manually parameterized, or randomly explored in each demo.

### 4.4 Optimization-method lineage

```text
EG-VID-GRADIENT
  ├─IMPLEMENTATION→ hillclimbers
  ├─IMPLEMENTATION→ mandelbrotnn
  ├─IMPLEMENTATION→ ManimApproximations
  ├─PRIMARY_SOURCE→ backpropagation / universal approximation / loss surfaces
  └─EXTENSION→ EG-VID-RSI
                   └─IMPLEMENTATION→ fractalsearch
                                          ├─INFLUENCE→ karpathy/autoresearch
                                          └─CONTEXT→ mandelbrotnn target
```

**Why expanded:** it connects classical optimization, discrete artifact search, and autonomous coding loops.  
**Wave 2 frontier:** pinned autoresearch design, evaluator code, retained candidate history, and evidence of metric gaming or generalization failure.

### 4.5 Multi-agent coordination lineage

```text
EG-VID-CHAOS
  └─IMPLEMENTATION→ agent_prompts
                      ├─city_instructions.txt
                      ├─open_ended_instructions.txt
                      ├─art_instructions.txt
                      └─thumbnail_instructions.txt

EG-VID-VISION
  └─IMPLEMENTATION→ Mindcraft
       ├─PRIMARY_SOURCE→ MineCollab paper
       ├─DEPENDENCY→ Mineflayer
       ├─EXTENSION→ current mindcraft-bots/mindcraft develop branch
       └─RELATED→ EG-VID-MC-RELIABILITY
```

**Why expanded:** strongest direct and controlled evidence for the local-competence/global-coherence problem.  
**Wave 2 frontier:** frozen paper revision versus current code; task generator; message protocol; action library; hidden-plan ablation; successful-trajectory training data.

### 4.6 Real-environment strategy search

```text
EG-VID-AOE
  └─IMPLEMENTATION→ AgentsOfEmpires
       ├─OBSERVES→ screen capture / image templates
       ├─ACTS_THROUGH→ real mouse and game UI
       ├─EVALUATES_WITH→ match outcomes / parsed recordings
       ├─PRESERVES→ screenshots / recordings / status / heartbeats / strategy archives
       └─MUTATES→ game AI scripts
```

**Why expanded:** this is a direct analogue for physical/GUI closed loops and shows why observability is part of the experiment.  
**Stop condition:** do not treat creator-reported final strategy quality as reproduced until the game/version/configuration can be recreated.

### 4.7 Generative phenotype search

```text
EG-VID-HD-CREATURES
  ├─IMPLEMENTATION→ hyperdimensions/index.html
  ├─IMPLEMENTATION→ function_trees.js
  └─EXTENSION→ EG-VID-HD-EVOLUTION
                    ├─IMPLEMENTATION→ experiments/evo_sim.html
                    ├─IMPLEMENTATION→ experiments/image_evolution.html
                    └─IMPLEMENTATION→ experiments/symbolic_regression.html
```

**Why expanded:** representation design is visible and materially changes the search neighborhood.  
**Wave 2 frontier:** distinguish automated objective selection from human aesthetic selection and document genotype-to-phenotype transforms.

## 5. Primary technical sources

| Source ID                  | Source                                                                                                                 | Relation                                  | Status                                       |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- | -------------------------------------------- |
| `EG-PAPER-MINECOLLAB`      | [Collaborating Action by Action: A Multi-agent LLM Framework for Embodied Reasoning](https://arxiv.org/abs/2504.17950) | `PRIMARY_SOURCE` for Mindcraft/MineCollab | Expanded                                     |
| `EG-REPO-MINDCRAFT`        | [mindcraft-bots/mindcraft](https://github.com/mindcraft-bots/mindcraft)                                                | Current implementation lineage            | Expanded README/metadata; code delta pending |
| `EG-UPSTREAM-MINEFLAYER`   | Mineflayer                                                                                                             | Low-level Minecraft action substrate      | Selective dependency frontier                |
| `EG-UPSTREAM-AUTORESEARCH` | [karpathy/autoresearch](https://github.com/karpathy/autoresearch)                                                      | Direct inspiration for fractalsearch      | Wave 2 expansion                             |
| `EG-THEORY-CA`             | Wolfram/cellular-automata sources linked in descriptions                                                               | Theory/context                            | Select only claim-relevant pages             |
| `EG-THEORY-OPT`            | Backpropagation, universal-approximation, and loss-surface sources linked by creator                                   | Optimization primary/context              | Wave 2 expansion                             |

## 6. Frontier policy applied in Wave 1

### Positive expansion signals

- creator-owned artifact: `+6`;
- explicitly linked implementation: `+6`;
- paper or cited primary source: `+5`;
- appears across multiple videos/projects: `+4`;
- required to verify a high-impact claim: `+5`;
- direct portfolio experiment analogue: `+4`;
- provides negative or contradictory evidence: `+4`.

### Negative signals

- generic navigation/social/support link: `−6`;
- duplicate/syndicated page: `−5`;
- no established path to a research question: `−5`;
- low-information landing page without source/artifact: `−3`;
- broad bibliography branch not needed for a claim: `−4`;
- inaccessible, ambiguous, or unclear-rights content: quarantine rather than score.

### Result

Wave 1 deliberately favored:

1. direct creator repositories;
2. one controlled primary paper;
3. implementation chains behind high-information videos;
4. negative results and coordination failures;
5. projects that expose evaluator and run-artifact design.

It stopped before:

- recursively crawling every paper bibliography;
- treating Patreon/search indexes as transcript authorities;
- ingesting unrelated account-history repositories;
- opening portfolio PRs from semantic similarity alone.

## 7. Coverage and gaps

### Covered

- creator self-description and project framing;
- 14 high-information/recent video nodes identified;
- 13 anchors analyzed to varying depth;
- 30 public creator-owned GitHub repositories enumerated;
- 16 direct implementation repositories classified as Priority A;
- Mindcraft current organization repository identified;
- MineCollab primary paper analyzed;
- direct open-ended agent prompts analyzed;
- selected current KooshaPari repositories inspected for applicability.

### Not yet covered

- official YouTube uploads-playlist inventory;
- every video description and chapter list;
- every permitted transcript/script;
- Shorts/live-stream distinction;
- deleted/private/unlisted gap reconciliation;
- full creator-project site graph;
- Lenia, Evoloop, Biomorphs 3D, Picbreeder, Neural Hill Climber, Germs Genetic Algorithm, and Elementary CA implementation paths;
- all description-linked papers and project pages;
- current-versus-paper Mindcraft code delta;
- direct run artifacts for Chaos, fractalsearch, and AgentsOfEmpires;
- reproducible builds or experiment reruns.

## 8. Wave 2 ranked frontier

| Rank | Target                                        | Why                                               | Required output                                                          |
| ---: | --------------------------------------------- | ------------------------------------------------- | ------------------------------------------------------------------------ |
|    1 | Official YouTube uploads playlist             | Replace secondary count with reconciled inventory | immutable channel ID, every upload ID, gaps, cache expiry                |
|    2 | All creator descriptions                      | Descriptions are the primary nested-link source   | versioned descriptions, chapters, typed links                            |
|    3 | Permitted transcript/script coverage          | Promote or reject transcript-derived claims       | acquisition route, timestamp confidence, hashes                          |
|    4 | `Artificial Life` direct text/references      | Current taxonomy claim is provisional             | creator-controlled source and mechanism taxonomy                         |
|    5 | Mindcraft paper revision vs current `develop` | Determine implementation drift                    | source-to-paper delta and benchmark-validity report                      |
|    6 | `fractalsearch` evaluator/run history         | Test weak-RSI and metric-gaming claims            | candidate lineage, evaluator version, retained failures                  |
|    7 | AgentsOfEmpires public run evidence           | Separate plumbing claims from reproducibility     | environment/config/run-artifact manifest                                 |
|    8 | LifeEngine brain implementation/history       | Promote controller-choice claim                   | code paths, mutation representation, commit rationale                    |
|    9 | Remaining creator web toys                    | Complete creator-owned implementation corpus      | source identity and video/project edges                                  |
|   10 | Counter-literature                            | Attack our preferred synthesis                    | multi-agent scaling, Goodhart, open-ended evolution, emergence critiques |

## 9. Graph-quality rules for subsequent waves

- Every source node requires immutable identity plus mutable version records.
- Every edge requires discovery source and locator.
- Original and canonicalized URIs are both retained.
- No secondary transcript mirror becomes a creator-direct source through repetition.
- A repository name match does not prove a video/project relationship.
- A dependency edge does not imply intellectual influence.
- A philosophical analogue does not authorize a project change.
- A source can contradict, supersede, or narrow an earlier source without deleting it.
- Frontier stops are recorded, not silently forgotten.
