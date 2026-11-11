# SessionLedger tokens.css adoption (vision-pillar L107 → per-repo)

This file documents how the SessionLedger repo adopts the shared
**Phenotype visual-identity palette library** from
`AgilePlus/.claude/worktrees/vision-pillar/assets/tokens.css`
(vendored here as `assets/tokens.css`).

## Source of truth

- Canonical: `AgilePlus/.claude/worktrees/vision-pillar/assets/tokens.css` (commit `5b95794`).
- Local copy: `assets/tokens.css` (this file's sibling).
- Drift guard: `AgilePlus/.claude/worktrees/vision-pillar/scripts/check-palette-overlap.sh` (10/10 PASS on current shipped state).

## Family selection for SessionLedger

Use the **Lab-Coat** family wrapper class (`.family-lab-coat`):

```css
@import url("./tokens.css"); /* or via Dioxus asset pipeline */

.app-root {
  composes: family-lab-coat;
  /* OR inline equivalents */
  --bg-primary: var(--lc-lab-white);
  --bg-panel: var(--lc-slate);
  --accent-primary: var(--lc-cobalt);
  --accent-secondary: var(--lc-teal);
  --accent-warning: var(
    --lc-orange
  ); /* #f97316 — was #f59e0b, swapped 2026-07-06 */
}
```

## Token quick-reference (Lab-Coat family, canonical as of commit 6afaac0)

| Token            | Hex       | Role                                       |
| ---------------- | --------- | ------------------------------------------ |
| `--lc-lab-white` | `#f6f8fa` | Background / panel base                    |
| `--lc-slate`     | `#1f2937` | Panel/text secondary                       |
| `--lc-cobalt`    | `#2563eb` | Primary accent — slide-stain blue          |
| `--lc-orange`    | `#f97316` | Live-session indicator — lit Bunsen burner |
| `--lc-teal`      | `#14b8a6` | Secondary — growth-medium teal             |

## Status

- **File-copy phase**: vendored `tokens.css` into `assets/`.
- **Wiring phase (Wave-31 C09)**: complete —
  - `crates/sl-viewer/src/tokens.rs` embeds `assets/tokens.css` and exports
    `lab_coat::*` hex constants.
  - `ThemeColors` consumes `tokens::lab_coat` (no ad-hoc accent hex).
  - `app.rs` embeds `TOKENS_CSS` for `--sl-*` / `--lc-*`; chrome CSS uses
    `var(--sl-*)` only.
  - Contract + SelfCheck: `docs/a11y/design-tokens.md`,
    `scripts/design-tokens-check.ps1 -SelfCheck`.

## Cross-repo palette registry

The 5 documented families in `assets/tokens.css`:

1. **Backbone-2** — sharecli + substrate (infra)
2. **Lab-Coat** — SessionLedger (R&D)
3. **Terminal-Forge** — forgecode (terminal)
4. **Tracera** — pre-existing
5. **MelosViz** — pre-existing

All families are pairwise non-overlapping per the overlap verifier.

## Re-syncing from canonical

When `AgilePlus/.../vision-pillar/assets/tokens.css` updates:

```bash
# Re-vendor:
cp /workspace/user/CodeProjects/Phenotype/repos/AgilePlus/.claude/worktrees/vision-pillar/assets/tokens.css \
   /workspace/user/CodeProjects/Phenotype/repos/SessionLedger/assets/tokens.css

# Re-verify overlap:
bash /workspace/user/CodeProjects/Phenotype/repos/AgilePlus/.claude/worktrees/vision-pillar/scripts/check-palette-overlap.sh
```

References:

- Vision-pillar canonical: commit `5b95794` (tokens.css) + commit `5b01e1d` (amber-sync) + commit `04597ce` (overlap verifier)
- SessionLedger: commit `915a408` (initial iconset) + commit `8e68296` (amber swap) + this commit
- Lab-Coat palette decision: 2026-07-06, vision-pillar + melosviz-3d overlap check
