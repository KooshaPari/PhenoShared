# ResearchLedger — Audits

This directory holds the canonical audit-trail artifacts for
ResearchLedger. Any research-finding claim, dataset-citation record,
or postmortem MUST land here before it is referenced in docs/ or
external pages.

## Sub-directories

| Sub-directory | Purpose | Notes |
|---|---|---|
| `org-audit-snapshots/` | Point-in-time captures of ResearchLedger + fleet inventory used in audits | append-only; never overwrite |
| `postmortems/` | Blameless retrospectives of failed research reconciliations, schema drift, or infra incidents | one file per event, dated |
| `ci-exceptions/` | One-off CI waivers (e.g. a research-validation test skipped due to known environment drift) | each waiver expires; link to owner + ticket |
| `boundary-reconciliation/` | Reconciliations with phenoregistry `BOUNDARY_OWNERS.md` (which repo owns research findings?) | match by YYYY-MM-DD |
| `absorption-justifications/` | When a research schema, dataset, or contract is absorbed from another repo, this directory records why | one file per absorbed artifact |

## Conventions

- File names: `YYYY-MM-DD-<slug>.md` (UTC, slug = kebab-case).
- Each artifact opens with a one-paragraph summary, then a table of
  contents, then the full report. Keep tone neutral; this is
  audit-grade prose.
- Append only. If a report is superseded, write a new dated file that
  links to its predecessor and adds a `Supersedes: <path>` header.
- Sensitive secrets must be redacted; see phenotype-registry
  `audits/secret-handling-policy.md` (if present) before committing.

## Cross-references

- Backlog: `BACKLOG-CROSSREPO-001` (cluster member; see
  `audits/org-audit-snapshots/2026-08-11-backlog-cross-repo-researchledger-init.md`)
- Sister repos in the same cluster: `KooshaPari/Benchora` (commit
  `bd8b717`), `KooshaPari/PhenoPlugins` (commit `0fc70fb`),
  `KooshaPari/Eidolon` (commit `cc20a5e`), `KooshaPari/RepoLedger`
  (commit `11fde57`).
- Cluster: Benchora, PhenoPlugins, Eidolon, RepoLedger, ResearchLedger.
- Parent context: `/path/to/phenotype/repos/_cockpit/audit-ResearchLedger.json`
