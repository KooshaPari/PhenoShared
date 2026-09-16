# PR420 Kilo review failure audit

**Pull request:** `KooshaPari/phenotype-registry#420`  
**Head:** `2331e82` (`audit: reconcile Grapheon absorption audit`)  
**Check:** `Kilo Code Review`  
**Run:** `6e05d285-f7a7-4338-ac86-1970b8f96b2c`  
**Completed:** `2026-07-27T01:38:07Z`

## Finding

The Kilo check completed with `FAILURE` but emitted no review findings or
actionable annotations. GitHub exposes only the failed conclusion and the
Kilo details URL for this run; the check output contains no source-level
finding. The failure is therefore classified as an unavailable/transient
review result, not as evidence against the Grapheon boundary change.

At the same head, the following gates passed: Summary, SonarCloud, Semgrep,
Socket Security (project and pull request), GitGuardian, and CodeRabbit (the
latter reported rate limiting). Macroscope and Mergify checks were skipped by
their normal policy.

## Exception policy

This artifact records provenance only; it does not authorize an automatic
merge. Merge requires one of:

1. a successful Kilo rerun at the same or a reviewed descendant head; or
2. an explicit sponsor-approved exception after confirming no Kilo findings
   are available and all other substantive security/quality gates remain
   green.

No source files, registry decisions, or boundary claims were changed to work
around the failed check.
