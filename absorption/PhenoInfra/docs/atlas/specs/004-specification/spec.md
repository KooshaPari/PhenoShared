# SPEC-04 — Granular contracts and traceability

Status: proposed program contract; no engine transition or product verification claimed.

## REQ-04-01 Native format reuse

Read actual AgilePlus/subject schemas and adapt richer existing records.

Acceptance: No generated schema claims official compatibility without a verified contract version.

## REQ-04-02 Capability decomposition

Expand actors, state, inputs, errors, recovery, support and lifecycle systematically.

Acceptance: A broad requirement such as resume is decomposed into testable relevant behaviors.

## REQ-04-03 Typed contracts

Represent data, API, UX, performance, security and delivery obligations distinctly.

Acceptance: Artifact count alone cannot satisfy a contract family.

## REQ-04-04 Stable identifiers

Assign stable IDs and explicit relation types with provenance.

Acceptance: Duplicate or dangling IDs fail consistency validation.

## REQ-04-05 Bidirectional traceability

Link source intent through requirement/decision/work/test/run/artifact and reverse gaps.

Acceptance: An orphan implementation and an unimplemented requirement are both detected.

## REQ-04-06 Critical invariants

Define non-negotiable behavior and ownership separately from optimization targets.

Acceptance: A throughput gain cannot compensate for a safety invariant failure.

## REQ-04-07 Versioned public contracts

Track schema/API/config/save compatibility and actual support profiles.

Acceptance: A breaking change requires migration/support decision, not merely passing new tests.

## REQ-04-08 No record padding

Let counts reflect the real product rather than fixed FR/ADR/entity quotas.

Acceptance: Generated templates are not counted as accepted product requirements.

## Scope discipline

Apply the actual subject support/role contract. Preserve richer existing source formats and authority. Generated spec bundles do not certify native AgilePlus compatibility; inspect the installed engine/schema first. Unknowns and failures remain explicit.
