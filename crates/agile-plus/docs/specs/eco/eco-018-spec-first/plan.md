# Plan: Spec-First

## Objective
Codify and enforce the rule that no code change ships without an approved kitty-spec.

## Scope
- PR template updates.
- CI validation.
- Spec directory schema enforcement.

## Implementation Steps
1. Update PR template to add required `spec:` field linking to an `eco-*` slug.
2. Add CI check validating the field references an active spec in `AgilePlus/kitty-specs/`.
3. Validate that any new spec directory contains `spec.md`, `plan.md`, `tasks.md`, `meta.json`.
4. Document enforcement in contributor guide.
5. Roll out per work package (WP-01..WP-03).
