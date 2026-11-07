# Wave 4: method assumptions and remaining direct papers

Campaign `eg-nested-corpus-2026-09`. Continuation of [Wave 3](WAVE-3-PRIMARY-SOURCES.md). Work tracking: [AgilePlus #1073](https://github.com/KooshaPari/AgilePlus/issues/1073).

Nine previously metadata-only direct papers now have selected-method and limitation reviews. Instant-NGP was deepened from project overview to paper methods. These are scope-bounded readings, not whole-paper reproducibility certifications. The existing source-video edges determine why each paper belongs in this corpus.

## EG-W4-S01 — The Loss Surfaces of Multilayer Networks

[Primary source, 1412.0233v3](https://arxiv.org/html/1412.0233v3). Read scope: Sections 3.2–3.3, assumptions and reduction; discussion. Video: `Anc2_mnb3V8`.

Variable independence, redundant parameterization, approximate uniformity and a spherical constraint support a spin-glass surrogate. The theoretical conclusions are conditional on that model, not a guarantee for every practical neural-network loss surface.

**Our translation:** Keep theorem assumptions separate from architectural similarity. Before using this work to choose an optimizer, record the actual loss, parameterization, initialization, data and budget. A result about a surrogate does not establish that evolution, SGD or a local minimum is always preferable.

**Alternative:** A practical experiment may contradict a transferred prediction without contradicting the conditional theorem.

## EG-W4-S02 — Large Scale GAN Training for High Fidelity Natural Image Synthesis

[Primary source, 1809.11096v2](https://arxiv.org/html/1809.11096v2). Read scope: Sections 3.1–3.2 and 4.1, scaling, truncation and instability. Video: `gvNdCRe3T-g`.

The study combines larger training runs with architectural and regularization changes. Sampling truncation trades diversity for fidelity. Training collapse and interventions with performance costs remain part of the method rather than disappearing at scale.

**Our translation:** Evaluate coverage and fidelity together. Include failed runs, early stopping, sampling settings and total compute when comparing candidates. Do not convert a successful large generator into evidence that an unrelated agent swarm becomes reliable merely by growing.

**Alternative:** A smaller or less truncated system can be preferable under diversity, stability or cost constraints.

## EG-W4-S03 — Denoising Diffusion Probabilistic Models

[Primary source, 2006.11239v2](https://arxiv.org/html/2006.11239v2). Read scope: Sections 2–3.2; training and sampling algorithms. Video: `gvNdCRe3T-g`.

The model learns reverse diffusion using an objective related to a variational bound; the noise-prediction parameterization and simplified training objective matter. Reverse sampling is an iterative inference process, distinct from gradient-based model training.

**Our translation:** Record what changes: weights during training, sample state during inference, or an external artifact during search. Repeated denoising steps are not evidence of online model learning. Specify the schedule, parameterization and sampling budget before transferring claims about iterative improvement.

**Alternative:** A visually better sample need not improve likelihood or establish the correctness of an engineering artifact.

## EG-W4-S04 — Pretrained Transformers as Universal Computation Engines

[Primary source, 2103.05247v2](https://arxiv.org/html/2103.05247v2). Read scope: Section 2; Sections 3.1–3.3 ablations; conclusion. Video: `0QczhVg5HaI`.

The frozen-pretrained-transformer experiments freeze attention and feed-forward parameters but train selected interfaces, normalization and positional parameters for downstream tasks. The reported cross-domain behavior concerns evaluated tasks and particular adaptation choices.

**Our translation:** Frozen backbone must not be labeled no training. Record trainable components, data, adaptation and baseline. The title does not prove arbitrary zero-shot capability, efficient universality, or a guarantee that an agent can execute every new tool or domain.

**Alternative:** Task-specific interfaces or simpler baselines can explain some gains; those alternatives need controlled comparisons.

## EG-W4-S05 — Diffusion Models Beat GANs on Image Synthesis

[Primary source, 2105.05233v4](https://arxiv.org/html/2105.05233v4). Read scope: Section 3 architecture ablations; Section 4 classifier guidance. Video: `gvNdCRe3T-g`.

Architectural improvements and gradients from a noise-aware classifier contribute to guided diffusion results. Guidance changes the sampling distribution and its fidelity/diversity balance. This is classifier guidance, not an interchangeable description of every guidance method.

**Our translation:** Freeze or explicitly vary the guide, sampler, model, compute and evaluation pipeline. Attribute an improvement to the combined treatment actually tested, not automatically to the generator architecture. Candidate filtering can change quality without improving the underlying model.

**Alternative:** Unguided or lower-guidance sampling may be preferable for diversity or when the classifier is misaligned.

## EG-W4-S06 — CogView: Mastering Text-to-Image Generation via Transformers

[Primary source, 2105.13290v3](https://arxiv.org/html/2105.13290v3). Read scope: Sections 2.1–2.3; Section 4.1 evaluation. Video: `gvNdCRe3T-g`.

CogView uses discrete image tokens in an autoregressive text/image model and stabilization methods for training. Its evaluation includes multiple generated candidates, self-ranking and image post-processing; the paper discusses metric sensitivity and comparison conditions.

**Our translation:** Treat candidate count, selection, resizing/blur/contrast choices and language preprocessing as benchmark variables. Compare complete pipelines and report unselected outcomes and selection cost. A best-of-many displayed image does not identify raw generator performance.

**Alternative:** Changing the selector or measurement pipeline can change a ranking even when the model is unchanged.

## EG-W4-S07 — Do Embodied Agents Dream of Pixelated Sheep?

[Primary source, 2301.12050v2](https://arxiv.org/html/2301.12050v2). Read scope: Section 4 / Algorithm 1; Sections 5.1–5.3; comparison caveats. Video: `NTHWMk5pcYs`.

DECKARD separates an imagined abstract world model from exploration that verifies or corrects it. The implementation uses language-derived prerequisites with embodied execution and evaluated skill policies. Experimental comparisons have differing observation and action shortcuts, including crafting interfaces.

**Our translation:** Store hypothetical prerequisites separately from witnessed outcomes. An observed target state does not validate every proposed causal edge. Compare controller, actuator and observation capabilities before crediting a planning method. Record actual failed frontier attempts rather than merely retaining an attractive plan.

**Alternative:** A tool shortcut, inherited skill or changed observation interface can explain gains without stronger reasoning.

## EG-W4-S08 — HuggingGPT

[Primary source, 2303.17580v4](https://arxiv.org/html/2303.17580v4). Read scope: Section 3 pipeline; Section 4.5; Section 5 limitations. Video: `c9c5a4IsjOA`.

HuggingGPT separates planning, model selection, task execution and response generation, with intermediate resources linking dependent tasks. Its evaluation and limitations distinguish well-formed plans from end-to-end outcomes and acknowledge latency and planning/execution failure.

**Our translation:** Validate dependency/resource references and tool results before accepting a final answer. A structurally valid task graph is not an execution certificate. Test missing resources, plausible but invalid plans, failed tools and fluent success messages unsupported by results.

**Alternative:** A narrower deterministic pipeline may be cheaper and more reliable for a fixed task family.

## EG-W4-S09 — A three layer neural network can represent any multivariate function

[Primary source, 2012.03016v2](https://arxiv.org/html/2012.03016v2). Read scope: Theorems 1–2; proof; Section 3 conclusion. Video: `0QczhVg5HaI`.

The existence theorem concerns a special Kolmogorov mapping network with target-dependent univariate outer functions, not just a usual fixed-activation finite-parameter MLP. The discontinuous case uses a nonconstructive argument, and the conclusion explicitly distinguishes existence from practical construction.

**Our translation:** Separate representability, constructibility, optimization, sample efficiency and generalization. Do not turn this theorem into a guarantee that an ordinary ReLU or sigmoid network can exactly express every discontinuity or learn it efficiently. The continuity counterexample in the companion note tests our transfer claim, not the theorem.

**Alternative:** A network can fit a sampled dataset while lacking an exact or uniformly accurate representation between samples.

## EG-W4-S10 — Instant Neural Graphics Primitives

[Primary source, 2201.05989v2](https://arxiv.org/html/2201.05989v2). Read scope: Encoding methods; collision treatment; implementation/evaluation discussion. Video: `t7_ZXgfJVG8`.

Instant-NGP combines a learned multiresolution hash encoding with small networks and efficient execution. Resolution levels and interpolation help manage collisions. The paper separates some remaining rendering-engine questions from encoding/network comparisons.

**Our translation:** Benchmark representation, memory traffic and implementation together, then ablate them. Faster coordinate regression does not directly prove agent planning speedups or safe self-improvement. Record setup cost, throughput, precision, hardware and error on the workload that matters.

**Alternative:** A different bottleneck or transfer task can erase the apparent advantage even when the original graphics result holds.

## One explicit primary-paper exception

[OMNI-EPIC](https://proceedings.iclr.cc/paper_files/paper/2025/hash/d40d7cbe7210f8a13ea0149eeae9c6de-Abstract-Conference.html) remains abstract/repository-overview depth here. The arXiv fetch failed; OpenReview returned a browser-verification page; the proceedings PDF exceeded the web fetch size limit. No challenge was bypassed and no missing methods were inferred from a secondary summary.

The 19-paper direct arXiv frontier therefore has 18 records with selected-method review across Waves 3–4 and one limited-depth exception. Earlier Wave 3 readings are inherited records, not claimed rereads. Non-arXiv links and recursive references remain a separate frontier.

See [machine-readable reviews](../data/wave-4-source-reviews.json). Raw primary-page hashes are not invented: exact paper versions and section scopes are the provenance available for these web readings.
