# Dependency-backed semantic compression

The objective is to reduce custom reasoning, implementation and coordinated maintenance while preserving accepted user value and constraints. Smaller LOC, fewer repos or more dependencies are not objectives by themselves.

## Decision order

Assess a standard facility, maintained dependency, thin adapter, upstream contribution, focused patch stack, independent fork and bespoke implementation. This is a preference for reuse where it fits, not a ban on original work. A candidate can fail due to semantic mismatch, performance, platform, licensing, privacy or lifecycle cost.

For each substantive custom subsystem compare functional fit; ordering/errors/cancellation/consistency; numerical behavior; latency/throughput/memory/startup; build and debugging effort; API/extension burden; security and transitive supply chain; update and patch costs; operations; and exit strategy. Measure the important properties using actual consumers, not marketing.

## Before changing code

Write the preserved contract: outputs, error categories, side effects, ordering, data durability, idempotency, concurrency, isolation, compatibility, numeric tolerance and resource budget. Characterize actual useful behavior and unresolved bugs separately. Do not fossilize an accidental defect into a requirement merely because differential testing observes it.

## Patch governance

Pin upstream provenance and patch series. Each patch names why it cannot be removed, tests, owner, upstream issue/PR where applicable, compatibility range and removal condition. Qualify upgrades on clean consumers and maintain rollback/data migration plans. A patch checksum verifies bytes, not that the patch is wise or upstream-compatible.

## Avoid abstraction inflation

Wrap at actual policy or stability boundaries. Do not mirror a dependency's entire API with renamed methods. Prefer exposing stable native types where acceptable to inventing an inferior universal type. Keep public contracts small, preserve escape hatches deliberately and document what changing the backend cannot promise to preserve automatically.

## Acceptance

A simpler implementation passes the relevant positive, negative, differential/property, consumer and performance checks. The same qualified artifact installs and performs the user task. Record maintenance reduction in concrete terms: custom code/protocol removed, decisions deleted, dependency cycles reduced, fewer coordinated releases, cleaner build or smaller patch burden. Do not claim parity for untested platforms.

## Owned capabilities are part of the reuse search

The decision above applies to our existing work as strongly as to third-party dependencies. The [ecosystem-first evolution policy](ECOSYSTEM-FIRST-EVOLUTION.md) defines current/planned/speculative consumer tiers, cross-repo ownership, proportional impact evidence and continuing reassessment. Before replacing or duplicating a mechanism, assess modifying its present owner and the downstream costs of every option. An internal local workaround is not automatically cheaper than fixing the shared capability; centralization is not automatically cheaper than justified separation.
