# xDD-first: specs and tests before implementation

**Status:** adopted · **Applies to:** all feature and bugfix work.

## Convention

Write the spec and the test **before** the implementation. The org practices the full xDD family:

- **TDD** — failing unit test first, then code to green.
- **BDD** — behavior described as scenarios for user-facing flows.
- **SDD** — spec-driven: a SPEC.md / ADR exists before non-trivial work starts (ADRs live in PhenoSpecs).
- **CDD** — contract-driven: API contracts pinned before integration.
- **DDD** — domain-driven: the domain model and ubiquitous language lead the design.
- **PDD** — prompt-driven: the agent prompt/task spec is itself a reviewed artifact.

Architecture is **hexagonal** (ports & adapters) and non-negotiable: domain logic depends on ports, never on concrete adapters. Follow **SOLID** and **DRY**.

## Libification threshold

Extract shared code into a package at the **2nd** similar use, not the 3rd. Two call sites that do the same thing is the signal to lift a port + adapter, not a copy.

## Why

Tests/specs written first define "done" before code biases it. Hexagonal boundaries keep the domain testable without infrastructure and let adapters be swapped (the basis for wrap-over-handroll). See [wrap-over-handroll](wrap-over-handroll.md).

## Don't

- Don't write the implementation and backfill a test that merely re-asserts what the code already does.
- Don't reach into an adapter from the domain to "save a layer" — that is the layer.
