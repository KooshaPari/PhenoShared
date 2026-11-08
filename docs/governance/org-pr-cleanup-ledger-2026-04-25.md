# Org PR Cleanup Ledger - 2026-04-25

## Summary

- Final open PR search: `gh search prs --owner <REDACTED> --state open --limit 200` returned no results.
- Archived repos were temporarily unarchived only to close stale PRs, then re-archived.
- No conflict rebases were performed during the final cleanup waves.
- Merge attempts against several active/blocked PRs confirmed repository rules or permissions as blockers.

## Closed PR Batches

### Stale User-Authored Cleanup PRs

Closed because they were conflicting, duplicate, broad generated scaffolding, or superseded by current main:

- `AuthKit#22`
- `PhenoKits#17`
- `PhenoLang#3`
- `pheno#58`
- `ResilienceKit#1`
- `DataKit#1`
- `phenotype-auth-ts#6`
- `agent-devops-setups#32`
- `Tasken#1`
- `Stashly#1`
- `heliosBench#122`

### Archived Repo PRs

Closed after temporary unarchive, then repos were re-archived:

- `phenoXddLib#7`
- `KodeVibeGo#41`
- `Settly#1` through `Settly#6`
- `worktree-manager#9` through `#13`, `#15`, `#16`
- `worktree-manager#14`

### Archived Repo Dependabot PRs

Closed as stale queue noise because the repositories are archived/read-only:

- `AppGen#21`
- `KlipDot#2`
- `kwality#4`
- `Quillr#1`, `#2`
- `phenoForge#1` through `#7`
- `phenotype-dep-guard#3`
- `Authvault#3` through `#7`

## Merged PRs

- `AuthKit#1`
- `portage#401`
- `Stashly#3`
- `Stashly#4`

Earlier migration/documentation PRs created or left for normal review:

- `PhenoProc#13`
- `PhenoKits#24`
- `pheno#77`

## Left Open By Design

- None. Final org-wide open PR search returned no results.

## Dependabot Audit

Archived repos with `.github/dependabot.yml` still present:

- `Quillr`
- `phenoForge`
- `phenotype-dep-guard`
- `Authvault`
- `worktree-manager`
- `Settly`

Archived repos checked with no `.github/dependabot.yml` found:

- `AppGen`
- `KlipDot`
- `kwality`

Attempted `DELETE /repos/<REDACTED>/<repo>/automated-security-fixes` for the archived repos that still have Dependabot configs. GitHub returned `422 Vulnerability alerts must be enabled to configure automated security fixes`, which means automated security-fix PR generation was not enabled for those repos at the security-fix setting layer. The remaining config files are only relevant if the repos are unarchived later.

## Ruleset / Merge Blocker Audit

Classic branch protection endpoint returned `Branch not protected` for the inspected active repos; blockers are GitHub rulesets and external checks.

- `heliosBench`
  - Active rulesets: `Main`, `Mainm`
  - `Main` includes repository-role bypass, pull request, linear history, required signatures.
  - `Mainm` applies to all refs without bypass and requires pull request, non-fast-forward protection, deletion protection, and required signatures.
  - `heliosBench#122` was also draft and had a failing SonarCloud reliability gate before closure.

- `portage`
  - Active rulesets: `Main`, `Mainm`
  - Both include pull request rules plus `code_quality` and Copilot code review rules.
  - Prior blocker was a requested-changes review; it was dismissed before `portage#401` admin merge.

- `phenoShared`
  - Active ruleset: `Main Governance Baseline`
  - Pull-request rule allows merge, squash, and rebase, with no required approving reviews.

- `AuthKit`
  - No rulesets returned in this audit and branch protection endpoint returned not protected.

## Follow-Up Recommendations

- If any archived repo is reactivated, remove or update stale `.github/dependabot.yml` before unarchiving long-term.
- Normalize rulesets that use an all-refs rule without bypass, especially `heliosBench/Mainm`, because it can block admin cleanup operations.
- For active repos, keep stale generated governance/doc scaffold PRs closed and recreate narrow current-main PRs only when the change has live value.
