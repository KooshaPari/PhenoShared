# Testing Strategy

## Evidence gates

- GitHub metadata: owner, fork, archive, visibility, default branch, size.
- Git evidence: every head and tag, commit SHA, tree SHA, and content size.
- Local evidence: exact-name path search plus Airlock registry, database, bare, and WIP records.
- Boundary evidence: named canonical owner or explicit infrastructure-artifact classification.
- Security evidence: gitleaks before publishing recovered commit history.

## Required validation before archive

1. Re-run live metadata immediately before mutation.
2. Confirm zero heads, zero tags, zero releases, and no default branch.
3. Confirm no local payload or unresolved Airlock state.
4. Archive, never delete.
5. Re-read post-action name, archived flag, and redirect behavior.

## Current results

- `git diff --check`: pass.
- Evidence ledger: 20 records; 13 archive actions complete, 7 blocked and untouched.
- AgilePlus: feature ID 2 is `specified` on the Wave 1 target branch.
- Gitleaks: repository config reproducibly panics on pre-existing allowlist path `*.lock`; rerunning
  with `/dev/null` configuration scanned 15.88 MB and found no leaks.
- `scripts/validate-ecosystem.sh`: repository-wide pre-existing drift remains, including unreachable
  `KooshaPari/dispatch-mcp`; this packet introduces no ecosystem metadata changes.
