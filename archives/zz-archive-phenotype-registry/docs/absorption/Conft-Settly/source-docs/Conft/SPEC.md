# Conft — Specification

**Version:** 0.1.0
**Status:** ARCHIVED
**Last Updated:** 2026-06-19

## Purpose

Conft was the canonical TypeScript configuration edge layer for the Phenotype
organization, providing Zod-validated config bindings. All content has been
absorbed into Configra.

## History

- **Created:** 2026-06-15 (as part of ADR-022 Rust/TS edge split)
- **Absorbed:** 2026-06-18 (ADR-031 / L5-111)
- **Contents:** TypeScript `@phenotype/config-ts` package, Zod schemas,
  Taskfile, E2E suite, SLSA attestation

## Migration

All content migrated to `KooshaPari/Configra`:
- `typescript/packages/conft/` → Configra `typescript/packages/conft/`
- Zod schemas → Configra `crates/config-schema/` (adapted to Rust)
- E2E suite → Configra test infrastructure
- ADR governance → Configra `docs/`

## Related ADRs

- ADR-022 — config consolidation (Rust/TS edge split)
- ADR-031 — Configra absorb decision
- ADR-035 — Configra migration gates
