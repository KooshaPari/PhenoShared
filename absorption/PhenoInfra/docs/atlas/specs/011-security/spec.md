# SPEC-11 — Preservation and safe boundaries

Status: proposed program contract; no engine transition or product verification claimed.

## REQ-11-01 No automatic deletion

Keep destructive lifecycle actions outside this program default authority.

Acceptance: Repo count targets cannot trigger deletion.

## REQ-11-02 Fork-network protection

Honor no-delete policy and scoped exceptional authority.

Acceptance: A fork remains protected regardless of a pause/topic rename.

## REQ-11-03 Full custody

Preserve required source/dirty/refs/releases/data and verify recovery when transitioning.

Acceptance: A Git bundle alone cannot be labelled a complete dirty-state backup.

## REQ-11-04 Untrusted content

Treat repo prompts and historic tool output as data, not controlling instructions.

Acceptance: Malicious source text cannot cause an unauthorized shell/tool action.

## REQ-11-05 Least-privilege tests

Use disposable scoped credentials and controlled isolation.

Acceptance: General QA never mounts the operator entire home or unrestricted vault.

## REQ-11-06 Evidence redaction

Track private raw and sanitized derivatives with separate IDs.

Acceptance: Blurring a screenshot does not satisfy log/index redaction.

## REQ-11-07 Credential segregation

Separate normal edit privileges from admin/delete/publication authority.

Acceptance: A worker cannot bypass gates by selecting an elevated credential.

## REQ-11-08 Update/retention boundaries

Preserve provenance and policy when changing tool/model/asset dependencies.

Acceptance: License/source obligations survive absorption and export.

## Scope discipline

Apply the actual subject support/role contract. Preserve richer existing source formats and authority. Generated spec bundles do not certify native AgilePlus compatibility; inspect the installed engine/schema first. Unknowns and failures remain explicit.
