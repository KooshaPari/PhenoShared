# Implementation Strategy

## Approach

Use a fresh current-head worktree instead of reusing stale prepared evidence.
Keep the downstream change limited to README badge evidence and session
documentation.

## Boundaries

- Do not modify canonical rich-cli-kit during the refresh.
- Do not reuse stale `docs/rich-cli-kit-sladge-current` evidence.
- Do not apply broad formatter or dependency changes unless validation proves
  they are necessary for this scoped update.
