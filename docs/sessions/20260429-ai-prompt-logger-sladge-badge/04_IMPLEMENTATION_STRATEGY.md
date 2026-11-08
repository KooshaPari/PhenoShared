# Implementation Strategy

## Approach

Use the smallest possible documentation-only change:

- Insert the badge immediately after the README title.
- Add session docs under `docs/sessions/`.
- Avoid dependency, code, generated artifact, or package metadata changes.

## Git Strategy

Because the canonical repo was dirty, use:

`PhenoObservability-wtrees/ai-prompt-logger-sladge-badge`

This keeps the prepared commit isolated from unrelated work.
