# `.github/workflows/` — STATUS

**Last updated:** 2026-08-19 (O28, Forge)

This directory contains 49 real GitHub Actions workflows. **5 obsolete placeholder stubs were removed in commit `<this>` / PR `<next>`**:

| Removed workflow | Deprecation reason |
|---|---|
| `alert-sync-issues.yml` | Was a placeholder for `<REDACTED>/phenoShared/.github/workflows/alert-sync-issues.yml@72b9c6cb` (deleted repo). Replaced in O27 with this stub; now removed since the original PhenoShared feature was an artefact of an earlier consolidation wave. |
| `release-drafter.yml` | Same history. The release-drafter pattern is already provided by `release-plz.yml` (active) and `release.yml` (active). |
| `security-guard-hook-audit.yml` | Same history. The hook-audit pattern is subsumed by `security-scan.yml` and `trunk-check.yml` (active). |
| `self-merge-gate.yml` | Same history. Merge policy is enforced by `policy-gate.yml` (active, `stack/layer/release/*` prefix enforcement). |
| `tag-automation.yml` | Same history. Tag automation is handled by `release-plz.yml` and `release.yml`. |

## What to do if these features are wanted again

1. Check git history: `git log --diff-filter=D --summary | grep -E "alert-sync|release-drafter|self-merge|tag-automation"`
2. The cherry-pick source for the stubs was upstream commit `b10d1b3b3` (2026-06-30) — git-blame that to see the original logic
3. Reimplement the feature *inline* in this repo (do NOT point at `phenoShared` — it is 404)
4. If a real automated issue-alert or tag-automation system is needed, prefer using GitHub's built-in repo settings (Security tab → Dependabot alerts, Settings → Tags → auto-tag protected branches) over a custom workflow

## Why `codeql.yml` was KEPT

Despite being part of the O27 cherry-pick, `codeql.yml` is a **fully functional** CodeQL analysis workflow (real `github/codeql-action/init@v3` + analyze steps) scanning Rust + Python + JS-TS on weekly cron + push/PR. It is the only one of the 6 inlined from `b10d1b3b3` that has working implementation logic, so it was preserved.

## Honest accounting

PR #301 (O27) fixed the immediate `phenoShared@*` CI noise by replacing the broken refs with placeholder echo-only stubs. That was a correct first step (made the 404 errors stop confusing the CI signal), but the stubs themselves were a transitional artifact and now (O28) are being removed so the operator isn't paged on phantom failures every cron tick.
