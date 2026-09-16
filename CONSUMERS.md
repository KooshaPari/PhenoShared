# phenoDesign — Consumer Map & Authority Chain

**Date:** 2026-09-08
**Scope:** Static evidence only — no authority transfer, no consumer migration.
**Provenance:** 2026-09-05 portfolio audit (chat1) breadth readiness slice R2/phenoDesign.

This document records **what currently consumes `@phenotype/design`** and **which document is authoritative** for the package's posture. It is intentionally narrow: it does **not** change authority, **not** retire any export, and **not** migrate any consumer. It exists so that future repair work has a single place to read the consumer graph before touching it.

---

## 1. Authority chain (current, observed 2026-09-08)

| Document | Posture | Notes |
|----------|---------|-------|
| `ARCHIVED.md` | **LIVE** — creativity/design/UX spine, un-archived 2026-06-08, absorption reversed 2026-07-20 | Per `DECLARE_SPINE` registry entry |
| `STATUS.md` | Un-archived 2026-06-08; package name corrected to `@phenotype/design` | Last-updated 2026-06-08 |
| `PLAN.md` | Active; 4-phase token → components → VitePress → quality plan | Phase 1–3 work landed |
| `README.md` (banner) | "ARCHIVED 2026-07-29" | **STALE** — conflicts with the three documents above and with the live consumer base below |
| `package.json` | `"name": "@phenotype/design"`, publishes `css/`, `dist/`, `tokens/`, `docs/guide/glass-recipe.md` | Real `npm publish` target |
| `package.json` (workspace) | `@kooshapari/phenotype-design-tokens` workspace subpackage with its **own** Tailwind palette (`#0ea5e9` sky vs `#7ebab5` teal) | See §3 below — drift, not duplication |

### Open question for the owner (not resolved here)

The `README.md` banner says ARCHIVED while every other authority document (and the live consumer base below) says LIVE. The README banner appears to be **stale**: the audit's `ARCHIVED.md` records the 2026-07-17 archive + 2026-07-20 absorption reversal. **Fixing the README banner is an authority change and is out of scope for this static-evidence fix.** Recommended owner action: update `README.md` to reflect the canonical state per `ARCHIVED.md`, but only after the spine registry is consulted and the change is approved through the AgilePlus feature workflow.

---

## 2. Consumer map (current, observed 2026-09-08)

The following consumers were identified by static search across the Phenotype workspace for `@phenotype/design` in `package.json` files and `keycap-palette.css` / `vitepress-theme.css` / `glass.css` / `components.css` in CSS `@import` statements.

| Consumer | Pin | Use | Evidence |
|----------|-----|-----|----------|
| `phenodocs/phenodocs` (root) | `"@phenotype/design": "github:KooshaPari/phenoDesign"` | VitePress root theme | `phenodocs/phenodocs/package.json:23` + `phenodocs/phenodocs/.vitepress/theme/custom.css` (imports `@phenotype/design/css/vitepress-theme.css`) |
| `phenodocs/phenodocs/packages/docs` | `"@phenotype/design": "github:KooshaPari/phenoDesign"` | `@phenotype/docs` shared theme | `phenodocs/phenodocs/packages/docs/package.json:18` + `phenodocs/phenodocs/packages/docs/src/css/custom.css` (imports `@phenotype/design/css/vitepress-theme.css`) |
| `phenotype-registry/registry/disposition-index.json` | records `absorbed_package_identity: "@phenotype/design"` | Spine registry | Line 1939 |

### What those consumers actually import

`phenodocs/phenodocs` (both root and `packages/docs`) consumes the **CSS asset path only**:

```css
@import '@phenotype/design/css/vitepress-theme.css';
```

That asset path is declared in `package.json` exports as:

```json
"./css/vitepress-theme.css": "./css/vitepress-theme.css",
"./css/keycap-palette.css": "./css/keycap-palette.css",
"./css/components.css":    "./css/components.css",
"./css/glass.css":         "./css/glass.css"
```

No current consumer imports the TypeScript token bundle (`./tokens` or `.` exports). The TS contract is enforced by `tests/exports.test.ts` and `tests/tokens.test.ts`; the **CSS contract is what is exercised in production today**.

### Consumers found but NOT yet wired to `@phenotype/design`

The following workspaces ship `keycap-palette.css` / `vitepress-theme.css` references in template/asset paths but do **not** declare `@phenotype/design` in `package.json` — they appear to be **historical or template-only** consumers and are NOT listed as live consumers until their `package.json` is wired:

- `thegent/templates/vitepress*/theme/custom.css` (template content, not consumed at runtime unless a downstream uses the template)
- `thegent-mergify/templates/vitepress*/theme/custom.css` (same)
- `phenotype-tooling{, -wtrees, -mergify}/packages/design/ARCHIVED.md` (references in archived material only)
- `phenodocs/phenodocs/{PRD,SOTA,SPEC,FUNCTIONAL_REQUIREMENTS}.md` (prose mentions, not runtime imports)

**No action taken on these.** Listed for owner awareness only.

---

## 3. Drift between `@phenotype/design` and `@kooshapari/phenotype-design-tokens`

The workspace subpackage `packages/design-tokens/` ships a Tailwind config that uses **a different palette** than the canonical keycap:

| Token | `@phenotype/design` (canonical) | `@kooshapari/phenotype-design-tokens` (workspace) |
|-------|---------------------------------|--------------------------------------------------|
| Primary | `#7ebab5` (teal, keycap.accent) | `#0ea5e9` (sky-500) |
| Dark | `#090a0c` (keycap.dark.bg) | `#0f172a` (slate-900) |
| Surface | `#f8f9fa` (keycap.light.bg) | `#f8fafc` (slate-50) |

The workspace package's `package.json` description says: "Shared CSS and Tailwind tokens for Phenotype landing pages (canonical home: phenoDesign)". That claim is **partially true**: the package re-exports `tokens.css` and a `tailwind.config.mjs`, but the Tailwind config defines **its own** palette that does not derive from the canonical keycap. It is currently not wired into any consumer's `package.json` (no direct `@kooshapari/phenotype-design-tokens` dependency was found).

**This is documented drift, not a regression.** A future cleanup task may unify the two palettes or formally retire the workspace subpackage; both are out of scope for this fix.

---

## 4. Verification commands

Re-running this audit at any later date:

```bash
# 1. Find direct consumers (package.json declarations)
grep -rn '"@phenotype/design"\|"@kooshapari/phenotype-design-tokens"' \
  --include="*.json" /Users/kooshapari/CodeProjects/Phenotype/repos \
  | grep -v node_modules | grep -v "phenoDesign/source-checkouts"

# 2. Find CSS asset consumers
grep -rln "keycap-palette.css\|vitepress-theme.css\|glass.css\|components.css" \
  --include="*.css" --include="*.ts" --include="*.tsx" --include="*.vue" \
  /Users/kooshapari/CodeProjects/Phenotype/repos \
  | grep -v node_modules | grep -v "phenoDesign/source-checkouts"

# 3. Verify the package builds and exports are intact
cd /Users/kooshapari/Downloads/chat1-portfolio-audit-2026-09-05/source-checkouts/20260908T082020Z/phenoDesign
bun run build && bun run test
```

---

## 5. What this document does NOT do

- Does not retire the `README.md` "ARCHIVED" banner (authority change — out of scope).
- Does not unify the workspace subpackage palette with the canonical keycap (cleanup — out of scope).
- Does not migrate any consumer to a different package (no authority transfer per audit mandate).
- Does not assert that the spine is the right spine — only that the spine is the **currently observed** spine.

Refs: audit/2026-09-05 (R2/phenoDesign), ARCHIVED.md, STATUS.md, PLAN.md, package.json exports.
