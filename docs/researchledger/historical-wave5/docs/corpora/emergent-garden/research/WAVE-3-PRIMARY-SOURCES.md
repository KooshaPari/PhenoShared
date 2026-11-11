# Wave 3 primary-source review depth

Campaign `eg-nested-corpus-2026-09`. These are original analyst notes with source locators. A metadata retrieval is not a full source review, and no paper result is represented as independently reproduced. Fourteen selected sources were inspected at the explicit depths below.

## S01 — ASAL

[2412.17799v2](https://arxiv.org/html/2412.17799v2), methods and discussion. The Init/Step/Render interface separates simulation components. Prompt alignment, temporal novelty and illumination are different objectives. Foundation-model scores are proxies; unconstrained image-producing systems can score well without providing useful scientific models. Our translation: version the renderer, evaluator, representation and selection policy separately, and test objective alignment independently of visual appeal.

## S02 — POET

[1901.01753v3](https://arxiv.org/html/1901.01753v3), methods and transfer mechanism. Environment generation, local optimization and cross-environment transfer are coupled, with admission criteria and bounded populations. A stepping stone can become useful elsewhere. Our translation: a diversity archive and deployment incumbent are different stores and policies. Test transfer benefits against added evaluation cost; a finite experiment does not prove endless improvement.

## S03 — Darwin Gödel Machine

[2505.22954v3](https://arxiv.org/html/2505.22954v3), methods, limitations and objective-hacking discussion. Coding-agent implementations are searched and retained in an archive. Validation is empirical, not a formal correctness proof or demonstrated foundation-model weight training. Our translation: isolate candidate-writable code from trusted result production, hold out tasks, and pin evaluator revisions.

## S04 — OMNI-EPIC

[2405.15568](https://arxiv.org/abs/2405.15568) and the [primary repository](https://github.com/maxencefaldor/omni-epic). Read depth is abstract and repository overview, not full paper: full-paper retrieval failed in this pass. The system generates learning environments and rewards using notions of interestingness. Our translation: generated environments and rewards are candidates needing solvability, safety and validity checks; no reproduction conclusion is supported.

## S05 — Observer-relative open-endedness

[2406.04268v1](https://arxiv.org/html/2406.04268v1), definitions and limitations. Novelty and learnability are relative to an observer; unpredictable output alone is insufficient. Our translation: include observer, loss, horizon and archive in any novelty claim. The thesis about intelligence is not an experimentally established universal scaling law.

## S06 — Growing Neural Cellular Automata

[Primary article](https://distill.pub/2020/growing-ca/), shared update rule, stochastic updates and state-pool training. Achieving a target once is weaker than maintaining it. Recycling evolved states changes the learning problem toward persistence. Our translation: test long horizons and disturbed/restarted states. Do not assign this training method to visually similar random-weight aesthetic NCA systems.

## S07 — Self-organized control

[Authors' project article](https://alexandrevariengien.com/self-organized-control/), associated with arXiv:2106.15240. Read depth covers controller mechanism, curriculum and perturbation discussion. The study uses a cellular controller on simulated cart-pole, with repeated local updates, input clamping and output interpretation. Our translation: this is a robotics lead, not a real-hardware safety result. Measure latency and perturbation behavior before transfer. Discovery was audience comment EG-W3-C09, not creator endorsement or historical Life Engine ancestry.

## S08 — MineCollab

[2504.17950v1](https://arxiv.org/html/2504.17950v1), framework, skill interface and evaluation scope. Collaboration is coupled to action execution through a substantial high-level tool interface. Our translation: freeze actuator capabilities when comparing coordination; changed vision, observation scope or low-level control must not be credited automatically to topology.

## S09 — Generative Agents

[2304.03442v2](https://arxiv.org/html/2304.03442v2), memory, reflection and evaluation framing. Retrieved memories and generated reflections differ in origin. The target includes believable behavior, not engineering correctness. Our translation: preserve observation-versus-inference provenance and require independent acceptance evidence rather than persuasive narrative.

## S10 — Project Sid

[2411.00114v1](https://arxiv.org/html/2411.00114v1), architecture, single-agent discussion, limitations and selected methods. Concurrent modules use a bottlenecked controller to reduce speech/action incoherence. Vision, spatial reasoning and motivational limitations are explicit; models already contain human social knowledge, so this is not de novo emergence of those institutions. Our translation: coordinate independently paced modules while distinguishing intention, communication and measured action. Simulated social proxies are not validation of real governance.

## S11 — Voyager

[2305.16291v2](https://arxiv.org/html/2305.16291v2), curriculum, skill library and execution feedback. Accumulating executable skills differs from updating foundation-model weights. Our translation: semantic retrieval identifies a candidate skill, not permission or proof that its prerequisites hold in the present environment. Pin skill versions and revalidate execution context.

## S12 — Engineering criteria for virtual artificial life

[Stepney review](https://pmc.ncbi.nlm.nih.gov/articles/PMC12489504/), DOI:10.1098/rstb.2024.0298; conceptual sections on requirements, designs and implementations. A mechanism satisfying one property does not establish every criterion attributed to life. Our translation: desired behavior, architecture and measured evidence are different levels. Do not equate a lively visualization with autonomy or self-maintenance. This is conceptual analysis, not a reproduced experiment.

## S13 — Fourier Features

[2006.10739v1](https://arxiv.org/html/2006.10739v1), sections 3–5. In low-dimensional coordinate regression, feature mappings change the effective kernel and frequency-learning behavior. Bandwidth affects fit and generalization; theoretical limiting assumptions matter. Our translation: control representation and validation split before attributing differences to an optimizer, and do not transfer coordinate-regression results wholesale to agent planning.

## S14 — Instant Neural Graphics Primitives

[Primary project overview](https://nvlabs.github.io/instant-ngp/), associated with 2201.05989v2 metadata. Read depth is the project's technical overview, not an independent training reproduction. Multiresolution encoding and execution design jointly matter for acceleration. Our translation: measure setup, throughput and the actual workload bottleneck. This source alone does not establish recursive self-improvement or general robotics acceleration.

## Original direct papers still metadata-only in this wave

`1412.0233`, `1809.11096`, `2006.11239`, `2103.05247`, `2105.05233`, `2105.13290`, `2301.12050`, `2303.17580`, and `2012.03016` remain metadata-only here unless a prior artifact separately records deeper review. OMNI-EPIC and Instant-NGP have the limited depths stated above. They are not silently marked irrelevant.

Versioned paper URLs and section scopes are retained; no exact primary HTML-byte hashes are invented. Current repository identity, a paper version, a release and a video date are separate facts. A newly related paper does not retroactively become an influence.
