# 20-Cohort Cloud Contradiction Audit

Evidence window: 2026-08-01 08:32:46Z-08:35:27Z
Base: `phenotype-registry` `main` at `052c5eff4856cf800db0776c286bd53e18f84318`
Branch: `docs/cloud-cohort-contradiction-20260801`

## Purpose

Reconcile the first-20 consolidation packet with current GitHub repository metadata. This is a
documentation-only evidence packet. It does not edit registry rows, change repository settings,
archive or unarchive repositories, delete refs, rewrite history, or force-push.

## Current cloud result

The twenty intake names resolve into four observable classes:

```text
11 archive-named target/archived rows +-- source API path resolves to zz-archive-*
 2 in-place archived repositories   +-- name retained; archived=true
 3 HTTP 404 repositories             +-- owner API path unavailable under current credentials
 4 active repositories               +-- PriceyApp fork, Quillr, Stashly, phenotype-teamcomm
                                  = 20 intake names
```

This contradicts the committed consolidation-20 outcome, which says only docket #1 was archived
and the remaining nineteen stayed HOLD or VERIFY-ONLY. The API result proves current state, not
who performed a rename/archive/delete operation or whether a sponsor authorized it. No
authorization or actor attribution is inferred here.

## Preserve-first disposition

Treat every mismatch as a provenance reconciliation queue:

1. freeze destructive follow-up;
2. preserve current cloud refs and local evidence already available;
3. establish a per-repository event/actor/authorization receipt from GitHub audit or sponsor records;
4. reconcile the session packet and registry only after the receipt is independently verified;
5. leave 404 rows unresolved until a durable bundle, redirect, or sponsor-confirmed disposition is
   found.

The existing `archive=false`, `delete=false`, `rename=false`, and `force_push=false` policy in
`docs/sessions/20260722-repository-preservation-wave/preservation-manifest.json` remains the
governing default for this packet.
