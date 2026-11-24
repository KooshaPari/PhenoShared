# Plan

## Objective
Codify an autograder contract binding FR → spec → docs → test → lint → journey.

## Scope
All kitty-specs, doc sites, test suites, and CI gates.

## Implementation Steps
1. Define FR metadata schema.
2. Define test↔spec citation contract.
3. Define docs↔FR/test reference contract.
4. Author BDD narrative template (Given/When/Then).
5. Enforce TDD order in PR template.
6. Wire XDD runnable examples into doc-site.
7. Stub journey gif placeholders and capture scripts.
8. Implement `make autograde` aggregator.
9. Validate against eco-017, eco-018, eco-019.
