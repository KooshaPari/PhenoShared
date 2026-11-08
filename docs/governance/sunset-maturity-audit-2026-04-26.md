# Phenotype Sunset Maturity Audit - 2026-04-26

## Executive Status

The GitHub PR queue is clear, but the organization is not yet in a mature sunset-ready state.
The remaining work is operational: local drift preservation, canonical source collapse,
governance/ruleset normalization, stale branch hygiene, and documentation consolidation.

Current verified state:

- Open PRs: **0** via `gh search prs --owner <REDACTED> --state open --limit 200`.
- GitHub repos: **164 total**: 101 active, 63 archived.
- Local git repos under the shelf: **112** top-level/local checkouts.
- Local drift backlog: previously audited 218 git repos with 186 drifted, 126 dirty, 108 ahead/behind, and 49 local-only branch cases.
- Archived Dependabot noise: cleared for the audited archived repos by closing PRs and removing stale `.github/dependabot.yml` from six archived repos.
- Known cross-repo technical debt: shared crate sprawl, drift mirrors, stale no-PR branches, and governance docs that do not always match live GitHub rulesets.

## Sunset State Model

Every repo should end in exactly one state:

| State | Definition | Required evidence |
|---|---|---|
| `ACTIVE` | Live product/library with ongoing changes | Open roadmap, passing CI, ruleset baseline, clean default branch |
| `MAINTENANCE` | Used but low-change | Owner, dependency policy, security policy, no stale PRs, minimal CI |
| `SUNSET_READY` | No planned feature work; kept for references/releases | No open PRs, no active Dependabot config, no local unmerged work, README states replacement/canonical home |
| `ARCHIVED` | GitHub archived/read-only | No open PRs, no Dependabot config, archive reason in ledger, successor link if applicable |
| `QUARANTINE` | State unknown or unsafe to mutate | Drift manifest, no pushes/deletes until disposition approved |

Default rule: if a repo has large local drift or unclear canonical-home status, mark it `QUARANTINE`, not `SUNSET_READY`.

## Repo Cohorts

### Cohort A - P0 Quarantine / Preservation

These repos must not be pushed, reset, or archived until their local work is split and dispositioned:

| Repo | Current evidence | Required disposition |
|---|---|---|
| `agentapi-plusplus` | 4,681 tracked changes; vendor deletion mixed with docs/import/test commits | split vendor cleanup from governance/test/import lane |
| `phenoSDK` | 2,189 tracked changes; deprecation/governance mixed with generated-doc cleanup and module removal | split deprecation docs from generated artifact cleanup |
| `PhenoProc` | ahead 8 / behind 12; 38 tracked changes; 68 untracked; 24 dirty gitlinks | freeze, gitlink manifest, split docs/CI from crate alignment |
| `Dino` | ahead 8 / behind 62; docs/spec scaffold plus SDK/test seed | fresh branch from current main; split docs from SDK/test |
| `PhenoSpecs` | archive consolidation and registry/spec edits in one dirty tree | split archive deletions from registry/spec updates |
| shelf root `repos` | coordination repo; child repos/worktrees create status spillover | treat as governance-only surface; never use root status as product truth |
| `AuthKit/go` | clean nested repo in this checkout, but no clear `.gitmodules` policy | choose managed submodule, vendored nested repo, or flattened directory |

### Cohort B - Shared Source Collapse

Goal: collapse "shared crate" sprawl into durable canonical homes before any further forced adoption.

| Area | Current evidence | Sunset target |
|---|---|---|
| `phenoShared` | canonical for many generic crates but missing Phase 1 crates | single published/source home for shared generic Rust crates |
| `pheno`, `PhenoLang`, `HexaKit`, `PhenoProc` | drift mirrors that re-host `phenoShared` crates | stop counting as consumers; remove duplicate workspace members after canonical imports |
| `AuthKit`, `DataKit`, `ResilienceKit`, `ObservabilityKit`, `TestingKit` | vendored extracts of shared crates | either own domain-specific forks explicitly or consume canonical shared crate |
| `phenotype-errors` | only broadly consumed crate, but via brittle relative paths | versioned git/tag or registry-published dependency |

Required first move: import Phase 1 crates from `pheno` into `phenoShared`, then re-target adoption specs to `phenoShared`.

### Cohort C - Governance Enforcement

Minimum mature state for active repos:

- Default branch protected by ruleset.
- PR required for default branch.
- No force push and no branch deletion.
- Repository-role bypass only for admin cleanup actors.
- Required checks are real workflow names, not stale docs.
- `CODEOWNERS`, PR template, and governance docs match live rulesets.

Priority repos:

| Repo | Current state | Action |
|---|---|---|
| `AgilePlus` | has active governance ruleset | verify required checks match local docs |
| `heliosApp` | active governance ruleset | reconcile local branch-protection docs with live ruleset |
| `thegent` | active `Main` ruleset | verify rule coverage after stale PR cluster closure |
| `agentapi-plusplus` | active `Main` and `Mainm` rulesets | inspect all-ref bypass shape after local drift quarantine |
| `Tracera` | active `Main` ruleset; local recovered/live split remains | resolve canonical checkout before more governance edits |
| `phenoShared` | active governance baseline | use as ruleset template where appropriate |
| `PhenoKits`, `HexaKit`, `PhenoMCP`, `PhenoProc`, `AuthKit`, `Dino`, `PhenoSpecs` | no rulesets in latest sampled audit | apply baseline only after repo-local drift and CI truth are known |

### Cohort D - Archived Repo Hygiene

Archived repos should stay closed/read-only and should not emit new dependency PRs.

Already handled:

- Closed stale PRs for the audited archived repos.
- Removed `.github/dependabot.yml` from `Quillr`, `phenoForge`, `phenotype-dep-guard`, `Authvault`, `worktree-manager`, `Settly`.
- Re-archived those repos after cleanup.

Next archived audit:

- Re-run `gh repo list` quarterly for `isArchived=true`.
- For any archived repo with open PRs or active Dependabot config, temporarily unarchive, close/remove, re-archive.
- Do not delete archived repos unless there is a separate evidence-backed deletion ADR.

## End-to-End WBS

### P0 - Preserve Unknown Work

1. Produce a branch/diff manifest for each Cohort A repo.
2. Create one salvage branch per coherent lane: docs/governance, generated cleanup, vendor cleanup, source feature work.
3. Push nothing until each branch has a written keep/split/discard decision.
4. Acceptance: no P0 repo has mixed unclassified drift.

### P1 - Canonical Source and Dependency Strategy

1. Import Phase 1 crates (`phenotype-error-core`, `phenotype-config-core`, `phenotype-health`) from `pheno` to `phenoShared`.
2. Decide per duplicated crate whether `phenoShared` or a Kit repo is canonical.
3. Replace sibling-path consumers with versioned git/tag or registry dependencies.
4. Acceptance: shared-crate audits subtract drift mirrors and show canonical home per crate.

### P1 - Governance Enforcement

1. Build live ruleset inventory for all 101 active repos.
2. Apply or repair rulesets only when the repo has a known CI truth surface.
3. Update local governance docs after live rulesets change.
4. Acceptance: each active repo is `ACTIVE`, `MAINTENANCE`, `SUNSET_READY`, or `QUARANTINE` with matching GitHub rules.

### P2 - Branch Hygiene

1. Inventory remote branches with no open PR.
2. Delete only branches proven merged or superseded.
3. For unmerged branches, record tip SHA and decision before deletion.
4. Acceptance: no stale no-PR branch older than 30 days without ledger entry.

### P2 - Docs and Worklog Consolidation

1. Promote this audit, the PR cleanup ledger, and local drift manifest into canonical worklog index entries.
2. Move unique content from dated/root cleanup docs into category worklogs.
3. Add pointers from legacy locations only when needed; otherwise remove redundant temporal docs in a dedicated docs cleanup PR.
4. Acceptance: each governance claim links to one durable source.

### P3 - Sunset Closeout

1. For each repo marked `SUNSET_READY`, add README successor/canonical-home note.
2. Disable Dependabot configs before archive.
3. Close PRs, clear branches, archive.
4. Acceptance: archived repos have no open PRs, no Dependabot config, and a recorded successor/disposition.

## Acceptance Criteria for "Truly Full" Closeout

- Org open PR count remains zero after two consecutive sweeps.
- Every active repo has one maturity state and one owner/canonical-home decision.
- Every archived repo has no open PRs and no active Dependabot config.
- Every P0 local drift repo has a split/discard/publish decision.
- Shared source crates have a canonical home and no unlabelled drift mirrors.
- Live GitHub rulesets match local governance docs for priority active repos.
- Worklogs and AgilePlus specs contain enough detail for a new agent to resume without chat history.

## Evidence Sources

- `gh search prs --owner <REDACTED> --state open --limit 200`
- `gh repo list <REDACTED> --limit 1000 --json name,isArchived,isPrivate,defaultBranchRef,pushedAt,updatedAt,primaryLanguage`
- `docs/governance/sunset-maturity-batch-2-execution-plan-2026-04-26.md`
- `docs/governance/ruleset-gap-ledger-2026-04-26.md`
- `docs/governance/actual-shared-crates-audit-2026-04-25.md`
- `docs/governance/org-pr-cleanup-ledger-2026-04-25.md`
- `worklogs/P0_DRIFT_DISPOSITION_2026_04_26.md`
- `worklogs/WORKTREE_QUARANTINE_LEDGER_2026_04_26.md`
- `worklogs/PHENOTYPE_POST_PR_CLEANUP_AUDIT_WBS_2026_04_25.md`
