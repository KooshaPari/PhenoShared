# Specifications

## Acceptance Criteria

- The README shows the Sladge badge near the existing status badges.
- The prepared branch is based on current canonical `fix/add-pem-gitignore`.
- Validation records whitespace, badge presence, LFS state, and available Go
  quality-gate results.
- No unrelated local changes are touched.

## ARUs

- Assumption: This is a documentation/governance disclosure only.
- Risk: BytePort has tracked LFS-like build artifacts that can dirty worktrees
  unless smudge is disabled during checkout.
- Uncertainty: Go validation may still be limited by local build cache or disk
  behavior outside the README/session-doc change.
