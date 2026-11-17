## Summary

<!-- What changed, why, and how it fits the hard-fork/dual-workspace model.
     Keep it truthful: no "by invitation only" boilerplate here. -->

## Linked requirement and external tracker item

<!-- Required. Cite AP-ITEM:<id> or AP-FEATURE:<slug>/WP<n> from the external
     AgilePlus service. Also reference any in-repo Functional Requirement, e.g.
     docs/functional-requirements/FR-CHK-001_GIT_CHECKPOINT.md. Do not add or
     link AgilePlus tracker artifacts in this repository or its source repo. -->

- External AgilePlus item: `AP-ITEM:<id>` or `AP-FEATURE:<slug>/WP<n>`

- [ ] New FR or spec required (attach proposal)

## Tests

<!-- What was run and the result. Required gate is the rust-ci.yml `workspace`
     job; root-workspace commands: `just check`, `just test`, `just lint`,
     `just fmt-check`. Do NOT claim codex-rs full builds were run unless they were. -->

- [ ] `just check` passes
- [ ] `just test` passes
- [ ] `just lint` passes
- [ ] `just fmt-check` passes
- [ ] `just audit` passes

## Risk & Rollback

<!-- Worst-case failure mode, blast radius, and revert strategy. -->

## Checklist

- [ ] PR description is truthful (no advisory-only CI claims)
- [ ] No scratch files committed (<code>build-\*.txt</code>, <code>\*.bat</code>, <code>\_\_pycache\_\_</code>, etc.)
- [ ] No machine-specific absolute paths added (AGENTS.md rule)
- [ ] CI gates left fail-hard (no `continue-on-error` / `::warning::` swallows)
- [ ] External AgilePlus item is cited; no tracker artifacts were added
- [ ] Tests trace to an FR where one exists
- [ ] Changelog updated if user-visible
