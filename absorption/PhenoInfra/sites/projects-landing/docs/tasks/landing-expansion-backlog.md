# Landing Expansion Backlog

## Status

Open.

## Purpose

Track the next shippable landing, docs, and branding surfaces after the Tier 1
`projects-landing` hub and `/koosha` personal layer.

## Tier 1 Router

- `projects-landing`: canonical Phenotype and KooshaPari project hub.
- `/koosha`: personal KooshaPari layer for the public project graph.
- `/brand`: public landing and microfrontend rollout map for shipped, next, and
  infrastructure surfaces.
- Next router work: federated docs source selection, org-wide QA aggregation, real
  preview routing, and PhenoObservability embed hardening.

## Clean Tier 2 Landing Repos

These are closest to production-ready project branding work:

- `byteport-landing`: run and record build proof, then add SEO/social metadata.
- `hwledger-landing`: sharpen the above-fold product proof around the HWLedger demo flow.
- `phenokits-landing`: add a clear kit catalog and CTA path.
- `thegent-landing`: add a current-state section and verify preview/docs routes.

## Next Landing Builds

These are now surfaced publicly at `/brand` so the next scaffold has a durable
control-plane queue:

- `phenoData`: data-layer landing and docs shell.
- `heliosBench`: benchmark docs, install/run guide, report gallery, and Pages workflow.
- `phenotype-registry`: registry landing docs and reference index.
- `Observably`: observability brand page and public UI integration notes.
- `PhenoContracts`: contract and schema docs shell.
- `PhenoKit`: single-kit docs and brand bridge into the PhenoKits catalog.

## Missing Docs/Landing Surfaces

Highest-leverage repos with README surfaces but no proper docs or site shell:

- `phenoData`: add a VitePress docs shell and Pages workflow.
- `heliosBench`: add benchmark docs, install/run guide, and Pages workflow.
- `phenotype-registry`: add registry landing docs and reference index.
- `phenotype-org-audits`: add a redaction-safe audit docs shell.

## Existing Docs To Promote

Repos with useful docs that need a surfaced site:

- `AuthKit`
- `PhenoRuntime`
- `PhenoMCP`
- `PhenoDevOps`
- `Tracely`
- `phenotype-tooling`

## Guardrails

- Keep project-specific landing work in the project landing repo when one exists.
- Keep `projects-landing` as the Tier 1 router, not a replacement for project docs.
- Do not use the dirty `pheno` workspace as a landing host.
- Preserve repo boundaries and commit each repo independently.
