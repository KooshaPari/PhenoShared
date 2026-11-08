# Sunset Maturity Batch 2 Execution Plan - 2026-04-26

## Purpose

Move the org from "PR queue is clear" into a controlled preservation and maturity
program. This batch intentionally avoids source mutations in dirty product repos. The
work is to classify, quarantine, and create small clean follow-up lanes.

## Current Verified State

| Signal | Result | Command |
|---|---:|---|
| Open GitHub PRs | 0 | `gh search prs --owner <REDACTED> --state open --limit 200` |
| Merged sunset program | `PhenoKits#36` at `2a294c0` | `gh pr view 36 --repo <REDACTED>/PhenoKits` |
| Closed polluted PR | `PhenoKits#38` closed | `gh pr view 38 --repo <REDACTED>/PhenoKits` |
| Worktree containers | 44 | `find . -maxdepth 2 ... '*-wtrees' '.worktrees' '*-recovered'` |
| Top-level wrapper roots | 33 | subagent inventory cross-check |
| Repo-local nested wrapper roots | 11 | subagent inventory cross-check |
| Immediate child dirs under wrappers | 284 | subagent inventory cross-check |
| Nested `.git` dirs | 142 | `find . -maxdepth 3 -name .git -type d` |
| Priority repo ruleset gaps | `PhenoMCP`, `PhenoProc`, `PhenoKits`, `Dino`, `PhenoSpecs`, `AuthKit` | `gh api repos/<REDACTED>/<repo>/rulesets` |

## P0 Drift Disposition

These repos remain unsafe for direct pushes or archive decisions. Each requires a
manifest-first lane and then one small salvage PR per coherent topic.

| Repo | Live evidence | State | Next action |
|---|---|---|---|
| `agentapi-plusplus` | `chore/infrastructure-push`, ahead 7, large `vendor/` deletion set | `QUARANTINE` | split vendor deletion from infra/docs commits; no rebase until branch intent is proven |
| `phenoSDK` | `main`, ahead 11, broad deletion of governance, CI, docs, package files | `QUARANTINE` | preserve branch tip, recreate any valid deprecation docs from current `main`; do not land bulk deletion |
| `PhenoProc` | `main`, ahead 8 / behind 12, modified Cargo/worklog files plus many untracked roots | `QUARANTINE` | create gitlink/untracked manifest, then isolate crate alignment from docs/governance |
| `Dino` | `main`, ahead 8 / behind 77, docs/ADR plus SDK/test additions | `SALVAGEABLE_SPLIT` | recreate docs ADR lane from current `main`; separate SDK/test seed into product review |
| `PhenoSpecs` | `main`, ahead 4 / behind 16, registry edits plus archive deletions | `SALVAGEABLE_SPLIT` | split registry/spec edits from archive-removal lane |
| `AuthKit/go` | nested repo at `AuthKit/go`, branch `main`, clean locally, no upstream shown | `POLICY_REQUIRED` | leave untouched until submodule, vendored directory, or flattened source policy is decided |
| shelf root `repos` | coordination repo with many untracked child/worktree paths | `GOVERNANCE_ONLY` | never treat root status as product truth; only land curated governance docs |

## Worktree Quarantine Plan

The shelf has 44 worktree/recovery containers:

- 33 top-level wrapper roots.
- 11 repo-local nested wrapper roots.
- 6 `.worktrees` directories.
- 37 legacy `*-wtrees` directories.
- 1 recovered tree: `Tracera-recovered`.
- 284 immediate child directories under all wrappers.
- 142 nested `.git` directories within depth 3.

Required next artifact: `worklogs/WORKTREE_QUARANTINE_LEDGER_2026_04_26.md`.
It should list each container with:

- path
- owning repo
- branch or detached SHA
- dirty/clean state
- open PR, closed PR, or no-PR status
- disposition: `keep-active`, `salvage`, `archive-reference`, `delete-candidate`,
  or `unknown`

Use three first-pass buckets:

- `active-worktree-forest`: non-empty `.worktrees` or `*-wtrees`.
- `recovered-checkout`: `Tracera-recovered`.
- `tombstone-or-marker`: empty wrappers that may still be intentional sentinels.

No delete operation is authorized by this batch.

## Shared Source Convergence

Current accepted local position:

- `phenoShared` is canonical for generic shared Rust crates.
- `pheno`, `PhenoLang`, `HexaKit`, and `PhenoProc` are drift mirrors for shared
  crate audit purposes.
- Kit repos with local copies are vendored extracts, not real consumers.
- `phenotype-errors` is the only broadly consumed crate and is consumed through
  brittle path refs.
- Current manifests are stricter than some older docs: `TestingKit` and
  `ResilienceKit` show local path wiring in this checkout, so docs that mention
  `git = "...phenoShared.git", branch = "main"` should be treated as migration
  intent, not current truth.

Immediate safe next PRs:

| PR | Target repo | Scope |
|---|---|---|
| `shared-crate-tags-adr` | `PhenoKits` docs only | consolidate `shared-crates-canonical-home-adr-2026-04.md` and `shared-crates-distribution-strategy-adr.md` into one accepted ADR |
| `phenotype-errors-release-prep` | `phenoShared` | add release checklist/license/readme/changelog metadata for `phenotype-errors` only |
| `consumer-pin-audit` | `PhenoKits` docs only | list path/git-main consumers to convert to tagged deps after the first `phenoShared` tag |

Blocked migrations:

- deleting duplicate crate copies from drift mirrors
- converting Kit repos from vendored extracts to canonical deps
- publishing to crates.io

Those require a successful `phenoShared` tag/release lane first.

## Governance Ruleset Snapshot

| Repo | GitHub ruleset sample | Local governance files | Maturity action |
|---|---|---|---|
| `AgilePlus` | active `Main Governance Baseline` | CODEOWNERS, PR template, policy workflows | enable required review-thread resolution if baseline still requires it |
| `Tracera` | active `Main` | local path points at `PhenoKits` remote in this shelf | resolve canonical checkout before product edits |
| `phenoShared` | active `Main Governance Baseline`, permissive review settings | CODEOWNERS and reusable workflow set | tighten ruleset before relying on it as baseline source |
| `thegent` | active `Main` | broad workflow set and backups; `AGENTS.md` over 500 lines | split/trim governance doc and add local ruleset source-of-truth |
| `agentapi-plusplus` | active `Main` and `Mainm` | dirty local state blocks edits | audit duplicate ruleset intent after drift quarantine |
| `PhenoMCP` | no rulesets returned | minimal workflow set | candidate for baseline after CI truth is sampled |
| `PhenoProc` | no rulesets returned | workflows exist, dirty local state | ruleset blocked until drift branch is dispositioned |
| `PhenoKits` | no rulesets returned | quality/doc/fr workflows | candidate for docs-only baseline PR after branch cleanup |
| `Dino` | no rulesets returned | dirty local state | ruleset blocked until docs/SDK split |
| `PhenoSpecs` | no rulesets returned | dirty local state | ruleset blocked until registry/archive split |
| `AuthKit` | no rulesets returned | semantic stale PR history and nested `go` policy gap | ruleset after nested repo policy decision |

## Updated WBS

### Batch 2A - Manifests Only

- [ ] Create `WORKTREE_QUARANTINE_LEDGER_2026_04_26.md`.
- [ ] Create per-P0 repo manifests under `worklogs/p0-drift/`.
- [ ] Preserve branch tips and upstream status for each dirty repo.
- [ ] Mark every repo as `QUARANTINE`, `SALVAGEABLE_SPLIT`, or `POLICY_REQUIRED`.

### Batch 2B - Clean Docs PRs

- [ ] Consolidate shared-crate ADRs into a single accepted source.
- [ ] Add consumer-pin audit for `phenotype-errors`.
- [ ] Add governance ruleset gap ledger for priority active repos.

### Batch 2C - First Source PR

- [ ] In `phenoShared`, prepare `phenotype-errors` as the first tagged dependency.
- [ ] Add license/readme/changelog/release checklist.
- [ ] Tag only after CI passes and no consumers still require `branch = "main"`.

### Batch 2D - Repo Mutations

- [ ] Recreate `Dino` docs ADR lane from current `main`.
- [ ] Recreate `PhenoSpecs` registry/spec lane from current `main`.
- [ ] Split `agentapi-plusplus` vendor cleanup from infrastructure changes.
- [ ] Decide and apply `AuthKit/go` nested repo policy.

## Acceptance Criteria For This Batch

- No broad dirty repo is pushed directly.
- Every P0 repo has a written disposition.
- Every worktree container has a ledger row before deletion is considered.
- Shared-crate ADRs do not conflict on canonical home or distribution strategy.
- Ruleset gaps are tracked separately from local drift.
