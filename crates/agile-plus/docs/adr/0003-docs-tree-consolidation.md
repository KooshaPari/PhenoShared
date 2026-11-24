# ADR-0003: Docs Tree Consolidation

## Status

Accepted

## Context

AgilePlus maintained parallel documentation trees (`kitty-specs/`, `specs/`,
`docs/operations/journeys/`, `traces/`) with overlapping purposes. Agents and
auditors had to search multiple roots for the same artifact type, and path drift
broke traceability validators.

## Decision

Consolidate into one canonical `docs/` layout:

| Artifact type | Canonical path |
|---|---|
| Eco / feature specs | `docs/specs/eco/<slug>/` |
| Crate FR specs + BDD | `docs/specs/crates/<id>-<name>/` |
| ADRs | `docs/adr/` |
| User journeys | `docs/journeys/` |
| FR/NFR requirements | `docs/requirements/` |

Legacy top-level folders (`kitty-specs/`, `specs/`, `traces/`) retain README
redirect stubs only. Content is **moved**, not deleted; archives live under
`docs/_archive/`.

## Consequences

- Single hop for auditors: `docs/` is the spec/docs spine.
- Tooling (`governance_index.py`, CLI `specify`/`implement`) must target
  `docs/specs/eco/`.
- Git history for moved paths is preserved via `git mv` / archive copies.
- Downstream repos referencing `kitty-specs/` need README stub follow-up.
