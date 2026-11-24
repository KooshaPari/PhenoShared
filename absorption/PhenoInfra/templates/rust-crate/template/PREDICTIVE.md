# Predictive DRY PR template (PREDICTIVE.md)

Use this template in your PR description when your PR touches a substrate
tier (`pheno-*-lib`, `phenotype-*-sdk`, `phenotype-*-framework`) or extracts
a capability from an app-level repo into a substrate crate.

The CI lint (`pheno-ci-templates/predictive-dry-check.yml`) requires the 4
ADR-041 criteria to be addressed in the PR body. Copy this template, fill
in the four lines, and your PR will pass.

---

## Predictive DRY (ADR-041)

- **criterion-1 (current consumer):** <repo/path> with working code stable for ≥ 30 days
- **criterion-2 (predicted consumer):** <repo-or-app-name>, target quarter Q-YYYY, scope: <specific capability>
- **criterion-3 (abstraction):** Port trait in `<path/to/trait.rs>`, MockAdapter in `<path/to/mock.rs>`, ≤ 5 methods
- **criterion-4 (reversal cost):** ≤ 1 day — delete crate + revert consumer to local copy (estimated < 4 h)

---

## PROMOTION.md (for tier promotions only)

If your PR also promotes a substrate to a higher tier (lib → SDK → framework
→ federated service), add a PROMOTION.md to the repo root documenting how
each ADR-042 gate was met. See `pheno-ci-templates/PROMOTION.md` template.

---

## Why these 4 criteria?

Per ADR-041, the goal is to prevent two failure modes:

1. **Speculative DRY** — extracting "just in case" with no real consumer.
2. **Premature abstraction** — extracting before the abstraction is clean.

Criterion 1 ensures there is real code to extract. Criterion 2 prevents
speculation. Criterion 3 forces a clean `Port` trait boundary (per ADR-014)
rather than a free-function copy. Criterion 4 bounds the reversal cost so
that a bad predictive extract is cheap to undo.

## Related

- `docs/adr/2026-06-18/ADR-041-predictive-dry.md` — full policy
- `docs/adr/2026-06-18/ADR-042-substrate-graduation-path.md` — tier promotion policy
- `pheno-predict` — fleet-wide similar-code scanner
- `pheno-drift-detector` — app-substrate drift scanner
- `pheno-framework-lint` — tier-convention enforcer