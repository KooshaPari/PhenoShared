# SessionLedger — Visual Spec (Lab-Coat)

Status: acceptance reference for C10 / L99–L107.  
Implementation of viewer CSS/components is owned by other lanes (`crates/sl-viewer/src`); this document is the **contract** those surfaces must meet.

## Sources of truth

| Asset                                                         | Role                                                       |
| ------------------------------------------------------------- | ---------------------------------------------------------- |
| [`assets/tokens.css`](../assets/tokens.css)                   | Canonical Lab-Coat hex tokens + `.family-lab-coat` aliases |
| [`assets/README-tokens.md`](../assets/README-tokens.md)       | Adoption / re-sync notes                                   |
| [`docs/a11y/design-tokens.md`](a11y/design-tokens.md)         | Viewer token SSOT wiring (Rust + CSS)                      |
| [`assets/brand/README.md`](../assets/brand/README.md)         | Mark rationale + family differentiation                    |
| [`docs/assets/identity/README.md`](assets/identity/README.md) | Identity demo motion (SVG/MP4)                             |
| [`tests/visual/README.md`](../tests/visual/README.md)         | Manual golden checklist                                    |

Forbidden drift: MelosViz warn `#f59e0b`, Backbone-2 graphite/panel/violet/green, Tracera midnight/teal/indigo, and purple accent `#7c3aed` (legacy dark theme) must not appear as Lab-Coat brand colors.

---

## 1. Lab-Coat palette

Family: **Lab-Coat** (R&D). Light lab-bench base; cool cobalt primary; orange live pulse; teal secondary.

### Core tokens

| Token                 | Hex       | Semantic role                                             |
| --------------------- | --------- | --------------------------------------------------------- |
| `--lc-lab-white`      | `#f6f8fa` | App / page background (lab coat)                          |
| `--lc-slate`          | `#1f2937` | Primary text, dark panels, bench grid                     |
| `--lc-cobalt`         | `#2563eb` | Primary accent (light) — focus, links, selected, fills    |
| `--lc-cobalt-on-dark` | `#93c5fd` | Dark-mode text/chrome accent — AA on slate + accent mixes |
| `--lc-orange`         | `#f97316` | Live / in-progress — Bunsen burner                        |
| `--lc-teal`           | `#14b8a6` | Secondary accent — success-adjacent, growth medium        |

### Semantic aliases (required mapping)

| Alias                     | Maps to                   | Use                                                          |
| ------------------------- | ------------------------- | ------------------------------------------------------------ |
| `--bg-primary`            | `--lc-lab-white`          | Shell background                                             |
| `--bg-panel`              | `--lc-slate`              | Inset panels (or slate-tinted surfaces)                      |
| `--accent-primary`        | `--lc-cobalt`             | CTAs, selection, focus ring                                  |
| `--accent-secondary`      | `--lc-teal`               | Secondary actions, positive secondary                        |
| `--accent-warning` / live | `--lc-orange`             | Live session, warning-adjacent live state                    |
| `--text-muted`            | slate @ ~60% or `#5c5f6e` | Empty-state / helper copy (must remain ≥ 4.5:1 on lab-white) |
| `--status-error`          | see §4                    | Failure text/surfaces — **not** cobalt                       |

### Light vs dark

- **Brand default:** light Lab-Coat (`lab-white` canvas).
- **Dark panel mode** (viewer chrome): inverted slate canvas; use `--lc-cobalt-on-dark` for accent _text/chrome_ so WCAG AA holds on slate. Brand cobalt `#2563eb` remains for light mode and solid fills. Do not invent a non–Lab-Coat brand palette.
- Theme API (`Theme::{Dark,Light}`) and web `data-theme="light|dark"` must resolve to these tokens — no purple primary.
- Web preference persistence uses `localStorage["sl-viewer-theme"]` with values `light` or `dark`; absence falls back to OS preference.

### Theme contract tokens

| Token                                 | Light role                | Dark role                         |
| ------------------------------------- | ------------------------- | --------------------------------- |
| `--sl-bg`                             | Lab-white app canvas      | Inverted slate canvas             |
| `--sl-surface`                        | White panel surface       | Slate panel surface               |
| `--sl-surface-muted`                  | Muted lab bench tint      | Muted slate tint                  |
| `--sl-border`                         | Subtle neutral divider    | Slate divider                     |
| `--sl-text`                           | Slate primary text        | Near-white primary text           |
| `--sl-text-muted`                     | Muted helper text         | Muted helper text                 |
| `--sl-accent`                         | Lab-Coat cobalt `#2563eb` | Lab-Coat on-dark cobalt `#93c5fd` |
| `--sl-accent-secondary`               | Lab-Coat teal `#14b8a6`   | Lab-Coat on-dark teal `#2dd4bf`   |
| `--sl-accent-warning`                 | Lab-Coat orange           | Lab-Coat orange                   |
| `--sl-danger` / `--sl-danger-surface` | Error foreground/surface  | Error foreground/surface          |

### Contrast floor

- Body text on `--lc-lab-white`: use `--lc-slate` (or darker).
- Cobalt / orange / teal on lab-white: large UI / icons OK; small body text prefers slate with accent for chrome only.
- Dark: accent text/chrome must use `--lc-cobalt-on-dark` (or equivalent ≥4.5:1 on `--lc-slate`); do not paint brand `#2563eb` as small text on slate.
- Error text must meet WCAG AA against its background (§4).

### Typography roles

`assets/tokens.css` defines named type-role tokens so viewer CSS and docs demos can share intent without repeating raw stacks:

| Token              | Role                                                    |
| ------------------ | ------------------------------------------------------- |
| `--font-display`   | Product/hero display headings; use sparingly            |
| `--font-body`      | Reading text and prose content                          |
| `--font-mono`      | Code, paths, timestamps, replay terminal output         |
| `--font-ui`        | Buttons, tabs, labels, controls, dense app chrome       |
| `--font-caption`   | Captions, badges, metadata, helper copy below 14px body |
| `--sl-measure-max` | Maximum line length for prose blocks (65ch)             |

---

## 2. Empty states

Empty ≠ error. Empty is calm, instructional, and non-alarming.

### Variants

| Variant            | When                        | Copy pattern                                                  | Visual                                                     |
| ------------------ | --------------------------- | ------------------------------------------------------------- | ---------------------------------------------------------- |
| **Unselected**     | Pane open, no row chosen    | “Select a … to …”                                             | Centered muted text; no icon required                      |
| **Zero data**      | List/query returned nothing | “No bundles to display” / equivalent                          | Optional low-contrast flask/eyepiece mark at ≤ 64px, muted |
| **First-run**      | No corpus / never ingested  | Short why + one primary CTA (“Open corpus…” / “Start daemon”) | Cobalt CTA; no orange (not “live”)                         |
| **Filtered empty** | Filters hide all rows       | “No matches” + clear-filters control                          | Teal or cobalt text link; never error red                  |

### Rules

- Class / region: `empty-state` (or equivalent) with `role="status"` when content updates asynchronously.
- No card chrome, no badge clusters, no multi-stat strips in empty panes.
- Do not reuse `.search-error` / `.status-error` styling for empty.

### Surfaces (viewer)

| Surface                   | Expected empty                |
| ------------------------- | ----------------------------- |
| Bundle detail             | Unselected: select from list  |
| History / timeline detail | Unselected session            |
| Timeline / list           | Zero data or filtered empty   |
| Search results            | Zero matches (filtered empty) |

---

## 3. Loading & skeleton states

Loading is temporary; it must not shift layout when content arrives (minimize CLS).

### Levels

| Level                | Use                                 | Spec                                                                                           |
| -------------------- | ----------------------------------- | ---------------------------------------------------------------------------------------------- |
| **Inline copy**      | Short fetches (&lt; ~300ms typical) | “Loading…” / “Searching…” adjacent to control; muted text                                      |
| **Busy control**     | Button during request               | Disable + label swap; keep width stable                                                        |
| **Content skeleton** | List / detail panes                 | Shimmer blocks matching final content shape (rows ≈ list row height; detail ≈ title + 3 lines) |

### Skeleton tokens (target)

| Token                     | Value                               | Notes                               |
| ------------------------- | ----------------------------------- | ----------------------------------- |
| `--lc-skeleton-base`      | slate @ 8–12% on lab-white          | Or `#e5e7eb`-class neutral on brand |
| `--lc-skeleton-highlight` | lab-white → translucent cobalt wash | Shimmer peak                        |
| Duration                  | `--lc-motion-slow` (see §5)         | Looping gradient or opacity pulse   |
| Shape                     | 4–6px radius                        | Match list/detail radii; no pills   |

### Rules

- Prefer content-shaped skeletons over spinners for primary panes.
- Spinners, if used, are cobalt stroke on transparent; 1.2s linear rotate; hidden under `prefers-reduced-motion` (static cobalt arc or copy only).
- Never paint skeletons in error red or live orange.

---

## 4. Error & failure states

Errors are recoverable by default; show message + path forward.

### Anatomy

1. **Icon or label** — “Error” / alert affordance (a11y lane owns ARIA details).
2. **Message** — one sentence, human-readable; no raw stack in default UI.
3. **Action** — Retry and/or dismiss; cobalt for Retry, muted for dismiss.

### Color

| Role                     | Spec                                                                                            |
| ------------------------ | ----------------------------------------------------------------------------------------------- |
| Error foreground         | Warm red that contrasts on panel, e.g. `#b91c1c` on lab-white or `#f87171` on dark slate panels |
| Error surface (optional) | Tinted wash (`#fef2f2` light / `#2a1a1a` dark) — not full-bleed alarm                           |
| Border                   | Subtle related red, 1px                                                                         |

Do **not** use `--lc-orange` as the sole error signal (orange = live). Do **not** use cobalt for failure text.

**Non-color cues (L81.15):** every recoverable error panel (`ErrorState`) must pair color with at least one of: a warning glyph (`aria-hidden`), a distinct left border, `role="alert"`, and/or `aria-invalid="true"`. Color alone is never sufficient.

### Surfaces

| Surface              | Behavior                                                                |
| -------------------- | ----------------------------------------------------------------------- |
| Search fetch failure | Inline `.search-error` region; clear on next successful search          |
| Replay / SSE failure | `.status-error` + Retry                                                 |
| Corpus open failure  | Blocking message + fallback to mock only in dev; production shows Retry |

---

## 5. Motion & reduced motion

### Motion tokens (target; may live in `tokens.css` later)

| Token                | Duration  | Easing        | Use                                     |
| -------------------- | --------- | ------------- | --------------------------------------- |
| `--lc-motion-fast`   | 120–150ms | `ease-out`    | Hover, tab underline, focus ring        |
| `--lc-motion-medium` | 200–250ms | `ease-in-out` | Panel fade, skeleton pulse half-cycle   |
| `--lc-motion-slow`   | 1.5–2s    | `ease-in-out` | Brand breathing (bundle bars, meniscus) |
| `--lc-motion-rise`   | ~3.2s     | `ease-in`     | Identity bubble rise (demo / mark only) |

### Brand motion (reference)

Documented in identity demo / animated mark:

- Bubbles: ~3.2s rise, stagger ~0.4s
- Bunsen / meniscus: ~1.8–4s opacity/scale breathe
- Bundle bars: ~2s opacity breathe

App chrome should stay at `--lc-motion-fast` / `--lc-motion-medium`; reserve slow loops for brand/live indicators.

### `prefers-reduced-motion: reduce`

When the user (or OS) requests reduced motion:

| Element                    | Behavior                                |
| -------------------------- | --------------------------------------- |
| CSS transitions            | Duration → `0.01ms` or `none`           |
| Skeleton shimmer           | Static base fill; no gradient animation |
| Spinners                   | Static or replace with “Loading…” text  |
| Live orange pulse          | Solid `--lc-orange`; no opacity loop    |
| Identity SMIL / demo loops | Pause on first frame or show static SVG |
| Scroll / route             | No parallax; no entrance choreography   |

Implement with a global guard:

```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

(Viewer may scope this under `.app-root` instead of `*`.)

---

## 6. Composition & chrome (viewer)

- One job per pane: list **or** detail **or** search results — avoid dashboard card grids.
- Focus ring: 2px `--lc-cobalt` outline, offset 2px; visible on keyboard only if focus-visible is available.
- Live session badge: `--lc-orange` dot or label; must not animate under reduced motion.
- Selected row: cobalt left border or background wash (~8% cobalt), not purple.

---

## 7. Keyboard map (viewer)

The primary view selector follows the ARIA tabs keyboard pattern:

| Key                          | Action                                                                             |
| ---------------------------- | ---------------------------------------------------------------------------------- |
| `Tab` / `Shift+Tab`          | Move focus into or out of the active tab and through controls in the current panel |
| `Left Arrow` / `Right Arrow` | Select the previous / next primary view, wrapping at either end                    |
| `Home` / `End`               | Select the first / last primary view                                               |
| `Enter` / `Space`            | Activate the focused tab or focused button                                         |

---

## 8. Acceptance (L107)

A change is visually accepted when:

1. Hex usage matches §1 (spot-check against `assets/tokens.css`).
2. Empty / loading / error match §§2–4 on the surfaces listed.
3. Reduced-motion behavior in §5 verified in OS or DevTools emulation.
4. Manual golden checklist in [`tests/visual/README.md`](../tests/visual/README.md) is checked (or automated harness, when present, is green).

Out of scope for this doc: packaging installers, a11y ARIA implementation details (a11y lane), and Rust theme module wiring (owned-repos / viewer lanes).
