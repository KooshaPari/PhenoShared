# Wave 5: repository identity, Git ancestry and transfer boundaries

Campaign `eg-nested-corpus-2026-09`. Evidence job [33955202084](https://github.com/KooshaPari/ResearchLedger/actions/runs/33955202084) ran source `35380061e75763edeb84139e33e8ee369ac5b976`. The downloaded artifact hash was independently verified as `7af550a852f629eccc9635c9d0a85a2e085bee7917496c3fe8941857b30b1908`. The [machine receipts](../data/wave-5-intake-receipts.json) preserve exact heads, response hashes, ancestry witnesses and sampled commit sets. They do not include the paper itself or fetched application code.

## Positive identity evidence

The old `MaxRobinsonTheGreat/EvolutionSimulatorV2` URL resolves to `MaxRobinsonTheGreat/LifeEngine`, with the same stable repository ID `276193544`. By contrast, `MaxRobinsonTheGreat/EvolutionSimulator` is a different repository, ID `138445656`.

`kolbytn/mindcraft` and `mindcraft-bots/mindcraft` resolve to repository ID `679125280`. `mindcraft-ce/mindcraft-ce` has ID `998229166`, and its GitHub parent/source points to official Mindcraft.

These are observed aliases and repository relationships. They do not establish rename dates or historical authorship by themselves.

## Positive Git ancestry evidence

The bounded fetches for official Mindcraft and CE contain 1,667 common commits. `git merge-base --all` returns the observed official head:

- official: `5f3acc87b479864124173de444f31fa5538f94a6`;
- CE: `cc9b6a3bc149359d8cabf104e377acf58a7c6a03`;
- merge base: `5f3acc87b479864124173de444f31fa5538f94a6`.

Thus that official commit is an ancestor of that CE commit. This is stronger than a name match or README claim. It does not make the implementations behaviorally identical, validate a benchmark on either, or prove the location of a capability at the date of a video.

## Explicit negative boundary

The fetched EvolutionSimulator and LifeEngine histories contain 21 and 210 commits respectively, with no common commit; merge-base returned exit 1. The fetch used a depth limit of 256. No common ancestor in these observations is not proof that no code was copied, no rewrite occurred, or the projects are intellectually unrelated. Keep the relationship unresolved beyond the positive URL identity and observed Git evidence.

A depth bound is not a bound on total commit count in a merged graph: official Mindcraft yielded 1,667 commits and CE 1,714. This distinction prevents false warnings or invented claims of exhaustive repository history.

## How this changes repository records

ResearchLedger should preserve requested URI, stable provider ID, resolved URI, observed revision, parent/source metadata, graph receipt and observation time separately. An alias resolver must not collapse different historical evidence versions into a single current README.

RepoLedger receives references to these facts and the relevant source revisions, not a second research interpretation. For Tracera, `same_provider_identity`, `shared_git_ancestor`, `derived_idea`, `same_behavior`, and `reproduced_result` should not be interchangeable edge types. The existing trace model may already represent some; inspect it before adding schema.

For Agentora and Benchora, the controlled treatment includes the actual skill library, command interface, observation mode, evaluator and revision—not only the LLM label or project family. Conventional baselines and simple independent attempts remain viable alternatives.

## Operator-human and physical-system deductions

Picbreeder provides a concrete example of preserving separately branchable artifacts instead of averaging conflicting preferences. This supports a research hypothesis for bounded operator branches, reusable ancestry and explicit promotion—not a universal organizational prescription. Do not equate branch count or total generations with useful outcomes. Track failed and abandoned work.

The timestep study gives a different warning: altering numerical settings can change a generative substrate rather than simply improve its fidelity. In a physical test loop, record simulator configuration separately from real hardware evidence. Git rollback cannot undo a cut, melted material, shipped prototype or other external effect; recovery/compensation must be modeled independently.

These are proposed transfer constraints. They do not authorize new product runtime code, architecture ownership changes, hardware execution or release.
