# Plan — eco-034

## Objective
Establish a single canonical `FUNCTIONAL_REQUIREMENTS.md` registry that the eco-024 trace matrix references.

## Scope
- Create the registry file with the required schema.
- Migrate active FRs from existing specs and READMEs.
- Wire eco-024 to consume the registry.

## Implementation Steps
1. Define the registry schema (id, title, owner, spec_slug, spec_anchor, status, test_path, journey_stub, trace_path).
2. Create `AgilePlus/FUNCTIONAL_REQUIREMENTS.md` with the schema header and seed rows for active specs.
3. Update eco-024 trace matrix loader to read the registry.
4. Document PR workflow for adding/updating FRs.
