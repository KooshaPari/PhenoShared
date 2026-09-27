# Phase 2 — Vaultwarden Canonical Migration

**Status:** stub, Phase 2.

## Purpose

Complete the credential migration from ad-hoc `.env` files and 1Password to Vaultwarden as the single source of truth. Establish formal rotation policy.

## Outline

- Inventory audit against `docs/specs/credential-inventory.md`.
- Bulk import script (Rust) from 1Password export.
- Rotation calendar (90/180 day cadence).
- Agent service-account scoping review.

## TODO

- [ ] Complete credential inventory audit.
- [ ] Write `iac/scripts/vw-import` (Rust, wraps `bw` CLI).
- [ ] Schedule first full rotation cycle.
