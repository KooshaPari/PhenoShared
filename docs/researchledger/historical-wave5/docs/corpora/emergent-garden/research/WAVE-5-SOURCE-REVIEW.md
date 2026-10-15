# Wave 5: evidence of progress, not the appearance of progress

Campaign `eg-nested-corpus-2026-09`. Work tracking: KooshaPari/AgilePlus#1073. This is a selected-method review, not a reproduction of the papers' systems. Each inference below is our engineering interpretation, not an attributed creator statement.

## R01 — OMNI-EPIC: the outstanding direct-paper methods gap

Source: Faldor, Zhang, Cully and Clune, [arXiv:2405.15568v3](https://arxiv.org/abs/2405.15568v3), ICLR 2025. The actual 126-page PDF was captured through a fixed public-source job after the web reader exceeded its response-size limit. PDF SHA-256: `ae55917c5173a03c64418e819d70dfad0dce33da52f9f0fa828fd8d0fd90306e`. See [capture receipts](../data/wave-5-intake-receipts.json).

Read scope: main methods 3.1–3.6, experiments 4–6, discussion 7, and selected appendix material C, G, H, J, K and O. Figures 1, 2 and 4 and the hyperparameter tables were inspected visually. The long supplementary code listings were not exhaustively reviewed or executed.

### Source-supported distinctions

Section 4's 200-task long run **does not train RL agents**: completion is assumed to show task generation. Section 5 separately reports five shorter runs with RL training. Section 3.5 uses specialist policies, initialized from a nearby learned task for new tasks; this is not a single demonstrated generalist.

Section 3.6 says preliminary VLM success detectors were insufficiently accurate. The used route is an LLM-generated `get_success` function, distinct from shaped reward. The reported 72.7% human/detector alignment is agreement, not a calibrated false-positive rate.

The archive contains learned and failed tasks. Retrieval, executable-code repair, interestingness checks, training, success assessment and task revision are separate stages. Figure 4's diversity and learned-progress plots also have different evidence bases. Appendix K makes the training cost concrete: two million steps and approximately one hour on two RTX 6000 Ada GPUs per task, not a cheap metadata-only operation.

### Our deductions and tests to require

Do not let generated environments, accepted code, assumed success and observed mastery increment the same counter. Preserve the unsuccessful attempts and denominators. Distinguish an archive of specialists from one fixed policy tested across tasks. A success predicate produced with the environment can share a generator's misconception even when it differs from the training reward. Require external checks for the particular claim; a second function name is not proof of evaluator independence.

Failed tasks may be useful retrieval examples rather than disposable noise. Preserve their failure causes and revisions while keeping unsafe execution artifacts quarantined. A novelty score and promotion to deployment have different acceptance conditions.

The direct arXiv inventory now has selected-method records for all 19 identified works across Waves 3–5. That does not mean all appendices, code, experiments, cited works or transcripts are complete.

## R02 — MineRL Diamond 2021: task interface is part of the result

Source: Kanervisto et al., [PMLR 176 paper](https://proceedings.mlr.press/v176/kanervisto22a/kanervisto22a.pdf). Direct description link from _Can AI (actually) beat Minecraft?_. Read scope: track definitions, environment/actions, evaluation and results; result figure and track tables visually inspected.

The research and introductory tracks allow different domain knowledge, reward engineering and compute. The research track obfuscates interfaces and constrains interaction/training resources; the introductory track is less restrictive. The reported evaluation uses unseen environments and 100 episodes. The paper explicitly warns that the tracks are not directly comparable.

Our implication: a Mineflayer command interface, an obfuscated learning benchmark, and pixel-level gameplay are different treatments. Report model, prior knowledge, actuator library, observations, reward construction and budget together. A better score across those treatments does not isolate planning quality or coordination topology. Record task-specific conventional baselines where available.

## R03 — Picbreeder 2011: asynchronous branching is not shared-state consensus

Source: Secretan et al., _Picbreeder: A Case Study in Collaborative Evolutionary Exploration of Design Space_, DOI `10.1162/EVCO_a_00030`. The [UCF institutional record](https://stars.library.ucf.edu/facultybib2010/1881/) verifies the work identity. The original description URL and the institutional download were inaccessible in this reader; the [Santa Fe Institute manuscript mirror](https://wiki.santafe.edu/images/1/1e/Secretan_ecj11.pdf) was readable. It is a 30-page prepublication manuscript, not a claimed byte-identical final publisher PDF.

Read scope: representation and branching (2.6–3.6), architecture (4), observational study (5), and limitations (6–7); Figure 7 inspected visually. Users fork an evolvable representation while parent and descendants remain separately available. Search does not require averaging everyone into one preference. The published-image statistics omit abandoned series and intermediate unpublished images. Generations and graph complexity correlate weakly with ratings; this is not a randomized demonstration that more operators monotonically improve quality.

Our implication for operator-human scaling: let operators explore branches against their own bounded evaluation criteria, retain reusable ancestry and explicit promotion/merge decisions, and measure abandoned effort as well as selected results. This is an alternative to forcing a common conversation or aggregating every preference into one scalar. The source does not prove that this will outperform other operating models in Tracera or software work.

## R04 — Step size can change the system being studied

Discovery path: the creator's Lenia demo link → [Lenia project references](https://chakazul.github.io/lenia.html) → Davis and Bongard, [arXiv:2205.12728v1](https://arxiv.org/pdf/2205.12728v1), _Step Size is a Consequential Parameter in Continuous Cellular Automata_. This is a nested research extension, not a direct video citation or proof of creator influence.

Read scope: the complete three-page paper's text, with the [authors' supporting explanation](https://rivesunder.github.io/yuca/step_size.html). PDF screenshot attempts failed; no independently inspected figure measurements are claimed. The examples report disappearance at step sizes that are too small as well as too large; one pattern changes qualitative movement with step size. Initial placement, grid and numerical precision can also matter.

Our implication: timestep, update schedule, precision and boundary conditions are experimental parameters, not harmless implementation details. Record both modeled duration and integration-step budget. This does not establish that smaller timesteps generally harm physical simulations, nor that a particular Lenia pattern transfers to robotics.

## R05 — Historical Mindcraft capability is time-indexed

Source: Kolby Nottingham and Max Robinson, [creator-authored UCI article, 2024-10-30](https://sites.uci.edu/kolbynottingham/2024/10/30/mindcraft/). Read depth: article sections describing interfaces, capabilities and limitations. The authors describe higher-level Mineflayer commands and automatic behaviors, and at that time qualify evaluation maturity and the absence of vision/online learning. These are historical claims, not the capabilities of every later revision.

The [new lineage evidence](WAVE-5-LINEAGE-AND-TRANSFER.md) connects historical URL identities with present repository identities without backdating later features. A repository alias, ancestor relationship, API capability, and experiment configuration need separate records.

## Evidence-admission controls executed

The accompanying [offline checker](../../../../scripts/research/assess_research_evidence.py) tests four claims independently: generation, learned task, shared-policy generalization and independent reproduction. It also compares nine declared controls. It never executes a source or decides that a cited receipt is truthful.

All 32 synthetic cases matched their expected outcomes: 5 admissions/comparisons accepted, 27 rejected. They include simulated success mislabeled learning, multiple specialists mislabeled a generalist, paper reports mislabeled reproduction, missing results and mismatched timestep/interface/evaluator controls. These are software negative controls, not OMNI-EPIC trajectory replays or a live Benchora experiment. See [results](../data/wave-5-admission-results.json).

## Retained uncertainty

Full transcripts remain unacquired; the raw comment archive was not reread this wave. The earlier one-comment discrepancy, broad recursive reading and live agent benchmarks remain open. No paper's reported result is promoted to our independent result. Source metadata and hashes identify records; they do not establish correctness, completeness or permission to deploy.
