# Specifications

## Scope

- Add the sladge badge to `ai-prompt-logger/README.md`.
- Do not change package behavior, dependencies, or runtime configuration.
- Preserve unrelated changes in the canonical checkout.

## Acceptance Criteria

- README includes `[![AI Slop Inside](https://sladge.net/badge.svg)](https://sladge.net)`.
- Badge appears near the top-level README title.
- Session docs record the governance rationale.

## Assumptions, Risks, Uncertainties

- Assumption: `ai-prompt-logger` is in scope because its stated purpose is
  multi-agent prompt logging and observability.
- Risk: The prepared worktree cannot be merged until canonical local changes are
  reconciled.
- Mitigation: Record the worktree branch and commit in the projects-landing
  governance ledger.
