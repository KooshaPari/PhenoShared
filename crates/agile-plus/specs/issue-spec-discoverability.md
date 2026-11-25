# chore: improve issue-to-spec discoverability

## Goal
Add a tiny local workflow to make open GitHub issues and unresolved AgilePlus specs visible together, so contributors can decide quickly what to pick up next.

## Why now
- The repo README and AGENTS already split attention between shelf-wide context and local implementation work.
- Open issues are currently not surfaced alongside local issue-like spec files, causing duplicate effort and missed handoff context.
- This is a low-risk quality-of-life improvement and can be reverted if not adopted.

## Proposed change (small scope)
- Add a new file at `specs/issue-spec-discoverability.md` that:
  - Defines a one-line process: check open GitHub issues, then check local `kitty-specs` markers, then choose a candidate.
  - Includes a compact copy-paste command snippet using `gh issue list` and `rg`.
  - Notes a minimal decision checklist for scope, dependency risk, and reversibility.
- This is intentionally documentation-only and does not change product behavior.

## Success criteria
- New feature exists in the repo at `specs/issue-spec-discoverability.md`.
- Contributors can follow it in under 2 minutes before starting implementation.

## Revert plan
- Delete the file if it does not improve triage efficiency.

## UX research question
- Which source (open GitHub issues vs local specs) is more useful for kickoff decisions for first-time contributors?