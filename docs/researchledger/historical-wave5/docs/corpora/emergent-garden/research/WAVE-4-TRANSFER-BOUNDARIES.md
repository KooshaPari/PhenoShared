# Wave 4: what follows, what does not, and what to test

Campaign `eg-nested-corpus-2026-09`. Source-specific observations live in [the method reviews](WAVE-4-METHODS-REVIEW.md). The statements below are our deductions and proposed research controls, not creator quotations or already-implemented product features.

## Existence is not an execution guarantee

An existence theorem, a constructive algorithm, a tractable implementation, an optimizer that finds it, and a method that generalizes from finite observations are five different achievements. A paper supporting one cannot silently discharge acceptance criteria for the other four.

A simple contradiction checks one tempting transfer claim. Suppose an ordinary finite network built only from affine transformations and continuous activations exactly represented the step function on an interval containing zero. That network is continuous by composition, but the target jumps. The premise fails. More strongly, if a continuous approximation had uniform error strictly below one half, its negative-side values would remain below one half near zero, while its value at zero for the right-continuous step would exceed one half. Continuity makes those requirements incompatible. The uniform error is therefore at least one half.

This is **not** a refutation of Ismailov's theorem: its specialized target-dependent outer functions are not restricted to the ordinary continuous-activation network in this counterexample. Nor does the argument prohibit fitting finite samples, approximation in another norm, or representing discontinuities with a different function class.

For our engineering systems, the corresponding discipline is to specify whether a statement promises existence, approximation, search success, runtime behavior, or measurable reliability. Avoid replacing the last four with a metaphor about expressive building blocks.

## A treatment includes selection and measurement

A candidate generator, budget, ranking procedure, preprocessing pipeline and evaluator together determine a reported result. Holding only the model name fixed does not identify the effect of coordination or representation. A best-of-many result needs its candidate count and selection cost; a transformed image needs the transformation recorded; a tool-using task needs the actual tool and observation interfaces.

Proposed Benchora acceptance fields:

- generator/model and representation revision;
- optimization or search procedure, initial state and data split;
- candidate count, all attempted outcomes, selection rule and selector revision;
- tool/action interface, observation interface and permissions;
- evaluator, preprocessing and resource-accounting revisions.

These are proposed experimental controls. Existing fields should be reused rather than creating a parallel universal schema. A conventional deterministic baseline and a no-change result can be valid competitors.

## An imagined dependency is not an observed transition

Keep a hypothesis graph separate from an execution graph. A plausible recipe or generated plan may predict prerequisites. Observation can then support, contradict or leave them unresolved. Reaching a goal supports a reached-state claim; it does not necessarily identify every causal dependency that the planner imagined.

For Agentora, proposed-action and observed-result evidence should remain distinct. For Tracera, an edge can carry origin, source revision and epistemic status without rewriting the historical hypothesis. None of this requires importing a Minecraft architecture wholesale.

A focused follow-on should submit four fixtures: a plausible plan with a nonexistent resource; a tool response missing the claimed effect; a reached state whose planned intermediate steps were skipped; and an equivalent task solved by a simpler baseline. Accept actual observations, reject unsupported completion, and retain causal uncertainty.

## A package is not complete because its label says so

The previous purported Wave 3 handoff was a three-file status stub. The replacement is built from an actual GitHub-derived export with exact hashes and executed tests. The new `verify_research_bundle.py` checks required research files, listed bytes, SHA-256, JSON validity, duplicate paths, missing/unlisted files, and unsafe paths or symlinks. It does not execute imported source text.

Its negative controls include that status-stub failure, content tampering, a missing required payload, a correct hash over invalid JSON, duplicate paths and path escape attempts. A manifest and passing hash check still prove neither scientific truth nor full corpus completion. The checker is an integrity gate, not a model benchmark or a cryptographic authorship system.

## Priority and non-applicability

These findings directly justify better evidence and comparison controls in the research pipeline. They do not establish a preferred agent count, a universal manager hierarchy, or a need to rewrite Agentora's runtime. Image-generation results are background for treatment design, not direct evidence of robotic safety. Coordinate-regression acceleration is not automatically an inference-stack speedup. A constructive or practical limitation should narrow the transferred claim, not cause the source to be discarded as useless.

The next unresolved content bottleneck remains full video text and deeper recursive-source coverage. Adding more status documents cannot replace that evidence.
