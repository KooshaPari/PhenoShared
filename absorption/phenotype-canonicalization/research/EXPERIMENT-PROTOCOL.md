# Outcome-driven language, library and pattern experiments

## Purpose

Explore aggressively without letting novelty, ecosystem fashion or local microbenchmarks become deployment policy. The candidate list is a researched seed set, not an exhaustive inventory of every possible language/library. New candidates enter whenever an actual dissatisfaction record suggests a mechanism that could improve the outcome.

## Required experiment capsule

Record hypothesis; capability and real consumer; baseline source/release; workload/input distribution; required semantics and numerical tolerance; hard latency/memory/cost/target constraints; serious alternatives; supported CPU/GPU/OS/driver/runtime; compiler/build flags; packaging and interop boundary; evaluator identity; measurement protocol; disqualifiers; expected integration and maintenance costs; stop condition; promotion and rollback tests.

Candidate descriptions in `candidates.json` are hypotheses, not measured benefits. No production winner was measured during this audit.

## Ordered exploration

First ask whether the work is needed at all. Then compare an improved algorithm/data representation in the existing implementation, improved use of an existing external/shared library, specialization/vectorization/batching, a narrow native or GPU extraction, a different runtime/language for the bounded component, and only then a wider rewrite when that is genuinely justified. This ordering is a cheap-control strategy, not a ban on a radical solution with strong evidence.

Compiler configuration, allocation, serialization, data layout, scheduling, IO strategy, persistence semantics and removal of unnecessary copies are part of the search. A novel language is only one axis.

## Measurement matrix

For each candidate run correctness and applicable failure cases first. Then measure useful workload throughput, p50/p95/p99 latency, startup/compilation, steady/peak memory, host/device transfer, FFI calls and copies, build/test iteration, artifact size and dependency closure. Retain raw samples and machine/tool identity. Use equivalent workloads and tolerances. Do not compare one warmed GPU kernel with an uncached end-to-end baseline.

Represent actual target combinations separately: the user's described Windows/Linux/native/VM and Apple-Silicon environments are not one interchangeable target. Discover actual hardware/driver capabilities on the target instead of assuming every kernel advertised for a newer GPU works on the available device. Qualification on an idle host is not a realtime-coexistence guarantee.

## Decision

Reject semantic/security/target incompatibility before weighted convenience tradeoffs. Prefer a Pareto comparison: a candidate can trade memory for latency only within accepted budgets and with visible consequences. An apparent gain smaller than measurement uncertainty is inconclusive, not a winner. A small reproducible gain at large volume can be valuable; a large isolated gain can be irrelevant to the real request path.

Include integration, migration, qualification, operation and future maintenance/repair in the cost horizon. Record the horizon and assumptions. Do not turn unknown future maintenance into a fake precise dollar estimate.

## Promotion

Package the candidate; install it in a real consumer outside its source tree; run the consumer's contract and required journeys; retain release/source/evaluator identity; verify rollback. Only then update the selected profile and stage adoption. Experimental code can remain in an isolated research worktree or retained artifact without becoming a permanent production dependency.

For every promoted implementation retain a counterexample or scenario where an alternative is preferable. That becomes a branch predicate or a supported profile, not a contradiction to hide.
