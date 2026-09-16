# Consolidation Wave 3

## Goal

Preserve local-ahead Git history and dirty payloads discovered after Wave 2, then publish verified
history under namespaced recovery refs before any boundary consolidation.

## Current outcome

- Wave 1 and Wave 2 registry packets are merged into `main` at `29f12fc`.
- Civis local `main` was gitleaks-clean and published as `recovery/civis-local/main-20260723`.
- OmniRoute local heads were gitleaks-clean and 65 heads were published under
  `recovery/omniroute-wtrees/*`.
- AgilePlus dirty/untracked payload was preserved with Airlock but remains blocked from cloud
  publication until its working tree is reconciled.
- SessionLedger, PhenoObservability, phenotype-tooling, portage, and thegent were published under
  verified recovery namespaces; forgecode was preserved to the KooshaPari fork after its origin
  remote rejected the Airlock push.
- Seven Wave 2 protected repositories remain mutation-blocked.

## Links

- Parent: `phenotype-registry` main
- Wave 2: `docs/sessions/20260723-consolidation-wave-2/`
- Boundary SSOT: `BOUNDARY_OWNERS.md`
