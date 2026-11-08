# Ruleset Gap Ledger - 2026-04-26

## Scope

Sampled priority active repos during sunset maturity batch 2. This ledger separates
GitHub governance gaps from local drift. Do not apply ruleset changes to dirty repos
until their local state is dispositioned.

## Sampled Repos

| Repo | Maturity | Live ruleset evidence | Local evidence | Next PR |
|---|---|---|---|---|
| `AgilePlus` | strong | active `Main Governance Baseline` | `.github/CODEOWNERS`, policy gate, PR governance gate, ruleset baseline | enable required review-thread resolution if still off |
| `phenoShared` | moderate | active `Main Governance Baseline`; permissive review settings | CODEOWNERS and reusable workflows exist | tighten to 1 approval, CODEOWNER review, thread resolution |
| `thegent` | strong but uneven | active `Main` | broad workflow set; `AGENTS.md` exceeds 500-line guidance; no committed root ruleset baseline | split/trim `AGENTS.md`; add local ruleset source-of-truth |
| `agentapi-plusplus` | blocked | active `Main` and `Mainm` | large dirty vendor/deletion branch | audit duplicate ruleset intent after drift quarantine |
| `Tracera` | unclear | active `Main` on GitHub repo | local `Tracera` path points at `<REDACTED>/PhenoKits` remote | resolve repo identity before governance PR |
| `PhenoMCP` | low | no rulesets returned | CI workflows exist; no root CODEOWNERS/pre-commit found in sample | add CODEOWNERS and baseline ruleset |
| `PhenoProc` | low-to-moderate | no rulesets returned | CI workflows exist; root governance fragmented, dirty local state | root CODEOWNERS/ruleset after drift disposition |
| `PhenoKits` | low root, moderate leaf | no rulesets returned | root doc/quality workflows; nested HexaKit has stronger governance files | add root ruleset or document delegated governance contract |
| `Dino` | blocked | no rulesets returned | local main dirty and far behind | split docs/SDK drift before ruleset |
| `PhenoSpecs` | blocked | no rulesets returned | local main dirty and behind | split registry/archive drift before ruleset |
| `AuthKit` | blocked | no rulesets returned | nested `go` policy question; stale semantic PR history | decide nested repo policy, then baseline |

## Ordered Fixes

1. `phenoShared`: tighten existing ruleset before using it as canonical baseline.
2. `AgilePlus`: sync live ruleset with documented baseline.
3. `thegent`: split oversized `AGENTS.md` and add committed ruleset baseline.
4. `PhenoMCP`: bootstrap CODEOWNERS and ruleset.
5. `PhenoKits`: choose root governance or explicit HexaKit delegation.
6. `PhenoProc`, `Dino`, `PhenoSpecs`, `agentapi-plusplus`: wait for drift
   disposition.
7. `Tracera`: resolve local/remote identity first.

## Acceptance Criteria

- Each active priority repo has exactly one ruleset state: `strong`, `moderate`,
  `low`, `blocked`, or `unclear`.
- Dirty repos are not edited for governance until their drift is split.
- Live GitHub settings and committed local governance docs are reconciled in the same
  PR when a ruleset changes.
