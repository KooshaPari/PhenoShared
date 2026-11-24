# Phase 2 — Hetzner Spillover (paid burst)

**Status:** stub, Phase 2.

## Purpose

Provision a Hetzner CAX11 Arm VM on demand when the heavy-home queue depth exceeds a threshold (e.g., 3 jobs waiting > 10 minutes).

## Outline

- Terraform module `iac/terraform/hetzner/` (to be added).
- Queue-warden shim (Rust) polls Woodpecker, rewrites labels when SLA breached.
- Cost target: < €10/mo averaged over a month.

## TODO

- [ ] Write `iac/terraform/hetzner/cax11.tf`.
- [ ] Write `iac/scripts/queue-warden` (Rust).
- [ ] Add Hetzner token handling to `docs/specs/credential-inventory.md`.
- [ ] Add cost alarms via Cloudflare Workers cron.
