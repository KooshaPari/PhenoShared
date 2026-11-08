# Alert-Sync Issue Filing Policy

**Status:** Active
**Owner:** Phenotype org governance
**Last updated:** 2026-04-25

## Background

The reusable workflow `<REDACTED>/phenotype-ops/.github/workflows/manifest-gate.yml` files GitHub Issues for Dependabot, code-scanning, and secret-scanning alerts on a weekly cadence. It is consumed by ~36 repos org-wide via thin caller workflows at `.github/workflows/alert-sync-issues.yml`.

The workflow is high-leverage in repos that ship code and surface real CVEs (e.g. `heliosCLI`, `cliproxyapi-plusplus`), but in docs-only repos it is pure noise — it re-files the same low-severity transitive-dep advisories every week, drowning the issue tracker.

## Policy

Alert-sync should run **only** in repos that meet **both** criteria:

1. The repo ships executable artifacts (binaries, libraries, services, CLIs, web apps) — i.e. dependency advisories are actionable.
2. The repo's issue tracker is the canonical place to triage security findings (not a downstream board, not a sibling repo).

### Repos where alert-sync MUST be disabled

- Docs-only repos (`phenodocs`, `phenotype-design`, sidebar-only sites)
- Audit/manifest repos that don't ship code (`phenotype-tooling` callers that only run scheduled audits)
- Archived repos (issue filing is moot)

### Repos where alert-sync MUST run, with severity gating

For active code repos, the workflow stays enabled but should file issues **only for `severity >= HIGH`** Dependabot/code-scanning findings, plus all verified secret-scanning hits. Lower severities flow into Dependabot's native PR stream and are triaged there.

This requires a follow-up change to the reusable workflow at `<REDACTED>/phenotype-ops/.github/workflows/manifest-gate.yml` to accept a `min_severity` input (default `high`).

## Disable procedure

Disable via the Actions API rather than deleting the caller workflow file, so the change is reversible without a code commit:

```bash
WORKFLOW_ID=$(gh api repos/<owner>/<repo>/actions/workflows \
  --jq '.workflows[] | select(.path==".github/workflows/alert-sync-issues.yml") | .id')
gh api -X PUT repos/<owner>/<repo>/actions/workflows/$WORKFLOW_ID/disable
```

Re-enable with `/enable` when the repo starts shipping code or when severity gating lands upstream.

## Current state (2026-04-25)

| Repo | State | Reason |
|------|-------|--------|
| `phenodocs` | **disabled** (workflow id 256491322) | Docs-only; was the heaviest noise source |
| `heliosCLI` | enabled | Ships binary; real CVEs |
| `cliproxyapi-plusplus` | enabled | Ships binary; real CVEs |
| `AgilePlus`, `Tracera`, `Civis`, `QuadSGM`, `Parpoura`, `pheno`, `HexaKit`, `PhenoLang`, `Tokn`, `Configra`, `Conft`, `heliosApp`, others | enabled | Active code repos; pending severity gating |

## Follow-ups

- [ ] Land `min_severity` input on the reusable workflow in `phenoShared`.
- [ ] Audit each consumer caller to pass `min_severity: high` once available.
- [ ] Re-evaluate `phenodocs` if it ever starts shipping a published package with a runtime dep graph (currently `@phenotype/docs` is content-only).

## References

- Current active workflow owner: `<REDACTED>/phenotype-ops/.github/workflows/manifest-gate.yml`
- Caller pattern: `.github/workflows/alert-sync-issues.yml` in each consumer repo
- Session memory: task #184 (alert-sync-issues.yml dedup)
