# Emergent Garden Project Gallery — Wave 1

**Campaign:** `eg-nested-corpus-2026-09`  
**Status:** creator-project identity and implementation map, partial  
**Observation date:** 2026-09-04

## Purpose

The creator site is a project graph, not merely a portfolio page. The gallery names thirteen projects that connect multiple videos to reusable implementations, earlier versions, research papers, interactive demos, and adjacent creator repositories.

This file separates confirmed implementation identity from plausible name matching. A project is not assigned to a repository solely because their names resemble one another.

## Gallery inventory

The creator gallery currently names:

1. Life Engine;
2. Lenia;
3. Neural Patterns;
4. Evoloop;
5. Functions in Hyperspace;
6. Mindcraft;
7. Langton's Ant Colony;
8. Neural Hill Climber;
9. Biomorphs 3D;
10. Picbreeder;
11. Game of Life;
12. Germs Genetic Algorithm;
13. Elementary CA.

**Creator root:** <https://emergentgarden.io/>

## Identity states

```text
CONFIRMED
  A creator-controlled source directly identifies the project and target.

PROBABLE
  Strong repository/path/title correspondence exists, but the creator-side
  outbound edge has not yet been preserved from the live description/gallery.

AMBIGUOUS
  Several candidates exist or the apparent target lacks direct creator evidence.

UNRESOLVED
  No defensible implementation target has yet been recovered.
```

## Project records

### EG-PROJ-LIFEENGINE — Life Engine

**Identity:** `CONFIRMED`  
**Interactive project:** <https://thelifeengine.net/>  
**Source repository:** <https://github.com/MaxRobinsonTheGreat/LifeEngine>  
**Predecessor:** <https://github.com/MaxRobinsonTheGreat/EvolutionSimulator>

The Life Engine is a cellular automaton whose organisms eat, reproduce, mutate, compete, and die. Selection is endogenous to the simulated environment rather than a separate manually computed task score.

The repository also documents eyes, movement, mutable perception-action mappings, and compact brains. This makes the project a bridge between artificial life and the channel's later embodied-agent work, but the controller remains far smaller and more constrained than an LLM agent.

**Primary portfolio edges:** Civis, Benchora, Tracera, hwLedger/physical engineering.

**Open work:** recover versioned parameters and experiments associated with the 2025 evolved-brain video.

### EG-PROJ-LENIA — Lenia

**Identity:** `UNRESOLVED`

The creator gallery names Lenia, but Wave 1 has not preserved the creator-side target URL or a creator-owned implementation repository. External Lenia implementations are therefore context sources, not automatically the creator's artifact.

**Research relevance:** continuous cellular automata, self-organizing morphologies, robustness under perturbation, and soft-body-like dynamics.

**Stop rule:** do not attach an external Lenia repository until the gallery/description edge or creator attribution is recovered.

### EG-PROJ-NEURALPATTERNS — Neural Patterns

**Identity:** `CONFIRMED`  
**Interactive project:** <https://neuralpatterns.io/>  
**Source repository:** <https://github.com/MaxRobinsonTheGreat/NeuralPatterns>  
**Video:** <https://www.youtube.com/watch?v=3H79ZcBuw4M>

The creator describes this as a browser-based neural cellular-automata toy. Its core is a 3×3 convolution followed by an activation function at each pixel, executed through WebGL.

**Primary portfolio edges:** Agentora local-policy experiments, Civis morphogenesis, Benchora perturbation tests, PhenoObservability spatial-state metrics.

**Open work:** recover trained/manual preset distinction and measure damage recovery versus ordinary smoothing or diffusion.

### EG-PROJ-EVOLOOP — Evoloop

**Identity:** `UNRESOLVED`

The gallery names Evoloop, but Wave 1 has not recovered a direct creator-controlled implementation edge. The name suggests self-reproducing cellular-automata lineage, but that interpretation remains a research hypothesis.

**Potential relevance:** self-reproduction, genotype/phenotype coupling, local construction, and error accumulation.

**Stop rule:** no architectural claims until the direct page, description, or source repository is captured.

### EG-PROJ-HYPERDIMENSIONS — Functions in Hyperspace

**Identity:** `CONFIRMED`  
**Source repository:** <https://github.com/MaxRobinsonTheGreat/hyperdimensions>  
**Explanatory video:** <https://www.youtube.com/watch?v=349r0xJFGNw>

The repository exposes mutable high-dimensional function trees whose outputs are visualized as colored parametric surfaces. It includes saved phenotypes, random function generation, Biomorphs, Picbreeder, image evolution, symbolic regression, and supporting tree viewers.

This is not merely a visualization repository. It is a representation laboratory: the function language determines what variation can be generated, mutated, selected, and interpreted.

**Primary portfolio edges:** ResearchLedger representation studies, Benchora search-space experiments, Agentora policy representation, Civis procedural phenotypes, physical-design generation.

**Open work:** recover mutation operators, parent/child lineage, selection interface, and saved-artifact provenance.

### EG-PROJ-MINDCRAFT — Mindcraft

**Identity:** `CONFIRMED_WITH_LINEAGE_WORK`  
**Historical creator repository:** <https://github.com/MaxRobinsonTheGreat/mindcraft>  
**Current repository:** <https://github.com/mindcraft-bots/mindcraft>  
**Paper:** <https://arxiv.org/abs/2504.17950>

Mindcraft connects language models to Minecraft through Mineflayer, profiles, tools, memory, generated actions, multimodal inputs, and multi-agent collaboration.

The current repository is explicit about risk: model-written code can execute locally, coding is disabled by default, injection remains possible, and containerization reduces rather than eliminates risk. It also exposes deterministic task files, initial inventories, target items, timeouts, blocked actions, and multi-agent counts.

The paper is a critical counterweight to the channel's open-ended experiments. It reports controlled action-level collaboration rather than assuming more free-form communication will improve a team.

**Primary portfolio edges:** Agentora, Tracera, SessionLedger, Benchora, phenotype-journeys, thegent, Helios family.

**Open work:** complete Git lineage from the creator fork to the organization repository and reproduce paper-task configuration semantics.

### EG-PROJ-TURMITES — Langton's Ant Colony

**Identity:** `PROBABLE`  
**Source repository:** <https://github.com/MaxRobinsonTheGreat/turmites>  
**Video:** <https://www.youtube.com/watch?v=7x9J7rsLC50>

The repository contains a browser implementation, presets, and a substantial simulation script. Its title differs from the gallery label, so the source edge should remain `PROBABLE` until the creator description/gallery link is captured directly.

**Primary portfolio edges:** decentralized state machines, stigmergic coordination, deterministic replay, and topology experiments.

**Open work:** extract preset state machines, interaction semantics, and computational demonstrations into a machine-readable catalog.

### EG-PROJ-HILLCLIMBER — Neural Hill Climber

**Identity:** `PROBABLE`  
**Candidate repository:** <https://github.com/MaxRobinsonTheGreat/hillclimbers>

The repository's README contains only its title. The name match is strong but insufficient to establish functionality, video linkage, or current status.

**Potential relevance:** online local search, policy perturbation, cheap evaluators, and incumbent retention.

**Stop rule:** no implementation claims until repository contents, creator link, and associated video are recovered.

### EG-PROJ-BIOMORPHS — Biomorphs 3D

**Identity:** `CONFIRMED_AS_HYPERDIMENSIONS_SURFACE`  
**Source path:** <https://github.com/MaxRobinsonTheGreat/hyperdimensions/blob/main/biomorphs.html>

`hyperdimensions` exposes Biomorphs as a first-class navigation target beside Picbreeder. Wave 1 treats it as a surface within the hyperdimensions authority rather than an independent repository.

**Primary portfolio edge:** human-in-the-loop evolutionary selection over compact generative representations.

**Boundary decision:** do not create a separate project node with independent lifecycle unless the creator gallery exposes independent state, saves, or release history.

### EG-PROJ-PICBREEDER — Picbreeder

**Identity:** `CONFIRMED_AS_HYPERDIMENSIONS_SURFACE`  
**Source path:** <https://github.com/MaxRobinsonTheGreat/hyperdimensions/blob/main/picbreeder.html>

This surface belongs to the same function-tree/search representation family as Biomorphs and Functions in Hyperspace.

**Primary portfolio edge:** interactive evolutionary search where a human supplies the fitness signal.

**Key warning:** human preference can discover useful forms, but it is expensive, inconsistent, and vulnerable to presentation order. It should be treated as an optional evaluator, not the only correctness oracle.

### EG-PROJ-GOL — Game of Life

**Identity:** `PROBABLE_CREATOR_WEBTOY`  
**Observed target:** <https://evolvecode.io/alife/gol.html>

The target appears in a research reference list alongside other Emergent Garden projects. Wave 1 has not yet captured the creator gallery's original outbound edge, so the identity remains probable rather than fully confirmed.

**Primary portfolio edge:** baseline local-rule substrate and a null model for claims about richer learned/evolved systems.

### EG-PROJ-GERMS — Germs Genetic Algorithm

**Identity:** `PROBABLE_CREATOR_WEBTOY`  
**Observed target:** <https://evolvecode.io/alife/aquarium.html>

The target is described in an external research reference list as the Germs genetic algorithm. It should be expanded because it may expose a direct evolutionary-artificial-life lineage absent from the public GitHub repository list.

**Primary portfolio edge:** population dynamics and externally specified mutation/selection.

**Open work:** recover source, license, state schema, fitness mechanism, and creator-side link.

### EG-PROJ-ECA — Elementary CA

**Identity:** `UNRESOLVED`

The gallery names Elementary CA, but Wave 1 has not recovered the target page or implementation repository.

**Primary portfolio edge:** simplest deterministic baseline for local-rule and irreducibility claims.

**Stop rule:** retain as a required gallery gap; do not substitute an arbitrary Wolfram-style implementation.

## Cross-project architecture

The strongest project graph is:

```text
EvolutionSimulator
  → LifeEngine
    → mutable perception and compact brains

NeuralPatterns
  → learned local transition rules

mandelbrotnn
  → gradient-based approximation
    → fractalsearch
      → agent-driven recursive code search

hyperdimensions
  ├─ Functions in Hyperspace
  ├─ Biomorphs
  ├─ Picbreeder
  ├─ image evolution
  └─ symbolic regression

MaxRobinsonTheGreat/mindcraft
  → mindcraft-bots/mindcraft
    → MineCollab paper and action-level collaboration

agent_prompts
  → open-ended shared-artifact agent experiments

AgentsOfEmpires
  → real-GUI execution, tournament artifacts, heartbeat, and rollback
```

## Shared mechanisms

### Substrate before intelligence

Every project starts by choosing a representational substrate: grid cells, local neural updates, function trees, code, Minecraft actions, Age of Empires scripts, or shared files.

### Execution is epistemic

The project does not know the complete result until the system runs. Execution is part of the research method, not merely deployment.

### Selection pressure is architecture

Survival, loss, human choice, challenge success, tournament wins, or artifact persistence each produce materially different behavior.

### Persistent artifacts make iteration possible

Saved organisms, images, prompts, code revisions, recordings, screenshots, status files, and incumbent strategies allow comparison and rollback.

### Coordination is not free

Shared state and communication can help, but they also create overwrites, contention, stale information, and unbounded behavior. Mindcraft's structured tasks and action-level coordination are evidence that emergent teams often need explicit scaffolding.

## Repository-boundary implications

1. Interactive surfaces do not automatically deserve independent repositories.
2. A creator gallery item can be a product, an experiment, a route into a larger repository, or only a named concept.
3. Historical and current repositories must remain separate until Git lineage and authority are proven.
4. External implementations of a named research system are context sources, not creator artifacts.
5. The corpus should preserve original creator edges before normalizing aliases.

## Wave 2 frontier order

1. recover all live gallery outbound URLs and page metadata;
2. resolve Lenia, Evoloop, Neural Hill Climber, and Elementary CA;
3. preserve the direct gallery edges for Langton's Ant Colony, Game of Life, and Germs;
4. extract hyperdimensions mutation, lineage, save, and evaluator contracts;
5. reconstruct Mindcraft repository lineage and task/evaluation schemas;
6. retrieve Life Engine evolved-brain experiment parameters and outputs;
7. classify `CodeEvolver`, `StableDiffEvolution`, `ManimApproximations`, and `hillclimbers` against the gallery;
8. identify publication/license status for each interactive artifact.
