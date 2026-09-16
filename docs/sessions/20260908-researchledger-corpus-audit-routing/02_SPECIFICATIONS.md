# Specifications

## Functional requirements

1. Route each non-ResearchLedger finding with a `VERIFIED` destination to an owner-repository artifact plus a registry link. `HISTORICAL` and `UNKNOWN` entries remain unresolved and must not be auto-routed; `MISSING` means unlinked in the inspected corpus, not demonstrated absent.
2. Keep the full corpus WBS authoritative in ResearchLedger; registry content may only cover routing, ownership, dependencies, and evidence limits.
3. Distinguish local committed/unpublished artifacts from remote/published files.
4. Preserve catalog records without schema or disposition changes.

## Acceptance criteria

- [ ] `07_CROSS_PROJECT_SYNC.md` names the repo-relative Benchora artifact path and its hosted/pinned status.
- [ ] No registry catalog, schema, code, or owner-repository source change is part of this session.
- [ ] ResearchLedger and Benchora are separate lanes with no cross-project pass inference.
- [ ] A later implementation PR links a real AgilePlus spec ID or remains governance-blocked.

## Out of scope

Benchora remediation, CI dispatch, scanner disposition, corpus acquisition, merge/push activity, and catalog reconciliation.
