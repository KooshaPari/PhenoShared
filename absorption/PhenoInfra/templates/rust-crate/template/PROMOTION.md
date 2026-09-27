# Substrate promotion PR template (PROMOTION.md)

Use this template in your PR when promoting a substrate from one tier to
another (lib → SDK → framework → federated service). Required by ADR-042 §6
for every tier transition.

`pheno-framework-lint` will check the resulting repo for tier compliance
after merge.

---

## PROMOTION: `<from-tier>` → `<to-tier>`

**Repo:** <repo-name>
**Date:** YYYY-MM-DD
**Author:** @<handle>
**ADR:** ADR-042

---

## Gate compliance

Each transition has 4-6 specific gates. Mark each ✓ or ✗ and link to evidence.

### `<from-tier>` → `<to-tier>` gates

- [ ] Gate 1: <description> — evidence: <link>
- [ ] Gate 2: <description> — evidence: <link>
- [ ] Gate 3: <description> — evidence: <link>
- [ ] Gate 4: <description> — evidence: <link>
- [ ] Gate 5: <description> — evidence: <link>  *(if applicable)*
- [ ] Gate 6: <description> — evidence: <link>  *(if applicable)*

---

## Tier-skipping declaration (REQUIRED if skipping tiers)

**Are you skipping any tier?** ☐ No  ☐ Yes — `<skipped-tier>` to `<final-tier>`

If yes, justify the skip in 1-2 sentences:

> <justification>

ADR-042 §4: tier-skipping is **forbidden** unless the skipped tier would
have been empty. (Example: a pure-data primitive lib can promote directly
to SDK if it never had business logic; "lib → framework" without an
intermediate SDK is forbidden.)

---

## Breaking-change budget

Per ADR-042 §5, the breaking-change budget for each tier transition is:

| Transition | Max breaking changes | Public API widening? |
|---|---|---|
| lib → SDK | 5 | Allowed (must be additive) |
| SDK → framework | 10 | Forbidden |
| framework → federated service | 20 | Forbidden (semver-major) |

**Estimated breaking changes in this PR:** <N>
**Rationale:** <if ≥ 5, justify>

---

## Reversal plan

If the promotion turns out to be wrong (e.g., new consumer count drops
below the next-tier threshold), how would we reverse?

1. <step>
2. <step>
3. <step>

**Estimated reversal cost:** <hours>

---

## Reviewer checklist

- [ ] All 4 (or 6) tier-transition gates are ✓ with evidence
- [ ] Tier-skipping is declared and justified (if applicable)
- [ ] Breaking-change budget is respected
- [ ] Reversal plan is concrete and ≤ 1 day
- [ ] ADR-042 §7 promotion-decision ADR is filed (or will be in this PR)

---

## Related

- `docs/adr/2026-06-18/ADR-042-substrate-graduation-path.md` — full policy + gate table
- `pheno-framework-lint` — tier-convention enforcer
- `pheno-ci-templates/PREDICTIVE.md` — predictive-DRY template (use for lib extraction)