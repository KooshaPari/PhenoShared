## Session Overview

- Project: `AgilePlus`
- Lane: `layer/agileplus-governance-baseline`
- Goal: rebuild the governance baseline as a clean PR lane from `origin/main`

## Scope

- add repo-tracked ruleset baseline documentation
- add PR governance gate workflow
- add repo-tracked GitHub ruleset contract
- restore the missing `scripts/self-merge-gate.sh` helper required by the existing workflow

## Notes

- the previously named governance split branch was not actually split; it pointed at the same mixed commit as the runtime, docs, and CLI lanes
- this lane is rebuilt directly from `origin/main` to keep the PR reviewable and compatible with the repo's layered branch policy
