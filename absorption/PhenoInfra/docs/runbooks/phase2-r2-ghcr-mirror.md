# Phase 2 — Cloudflare R2 as GHCR Mirror

**Status:** stub, Phase 2.

## Purpose

Mirror container images from GHCR to Cloudflare R2 for egress-free pulls from mesh runners.

## Outline

- R2 bucket per registry (one for public images, one for private).
- Cloudflare Worker acts as OCI-compatible proxy in front of R2.
- CI pipelines switch pull source via env var.

## TODO

- [ ] Write `iac/terraform/cloudflare/r2-registry.tf`.
- [ ] Deploy Worker (see `iac/terraform/cloudflare/workers.tf` stub).
- [ ] Update runner env files to prefer `registry.phenotype.io`.
