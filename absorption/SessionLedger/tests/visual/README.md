# Visual golden checklist (SessionLedger)

Manual acceptance for [`docs/VISUAL_SPEC.md`](../../docs/VISUAL_SPEC.md) (Lab-Coat / L99–L107).  
The contract validator is CI-safe and the Playwright screenshot comparison asserts committed PNG baselines under `tests/visual/golden/`. Run this checklist before merging viewer visual changes.

## Prerequisites

- Viewer running against a known fixture corpus (or mock data).
- Display scale 100%; window ≥ 1280×720 for desktop shots.
- Tokens reference: `assets/tokens.css` Lab-Coat block.

## Palette lock-in

- [ ] Canvas / page background reads as lab-white `#f6f8fa` (or documented dark slate panel mode — accents still Lab-Coat).
- [ ] Primary accent / selection / focus uses cobalt `#2563eb`.
- [ ] Live / in-progress indicator uses orange `#f97316` (not `#f59e0b`).
- [ ] Secondary accent uses teal `#14b8a6` where applicable.
- [ ] No purple `#7c3aed`, Backbone-2, Tracera, or MelosViz brand hexes in chrome.

## Empty states

Capture or eyeball each surface (store approved PNGs under `tests/visual/golden/`):

| ID  | Surface                          | Expect                                                   |
| --- | -------------------------------- | -------------------------------------------------------- |
| E1  | Bundle detail, nothing selected  | Muted “Select a bundle…” empty-state; not error styling  |
| E2  | History detail, nothing selected | Muted “Select a session…” empty-state                    |
| E3  | Timeline / list with zero rows   | “No bundles…” (or equivalent); calm, not red             |
| E4  | Search with no matches           | Zero-match copy + clear path; not `.search-error`        |
| E5  | First-run, no corpus ingested    | Short why + cobalt CTA; not error styling or live orange |

- [ ] E1–E5 pass copy + color rules in VISUAL_SPEC §2.

## Loading states

| ID  | Surface                                 | Expect                                                              |
| --- | --------------------------------------- | ------------------------------------------------------------------- |
| L1  | Search in flight                        | “Searching…” / “Loading…”; control not layout-shifting wildly       |
| L2  | List/detail skeleton (when implemented) | Content-shaped placeholders; cobalt-neutral shimmer, not orange/red |

- [ ] L1 pass; L2 pass or N/A if skeletons not yet shipped.

## Error states

| ID  | Surface                 | Expect                                                     |
| --- | ----------------------- | ---------------------------------------------------------- |
| R1  | Search fetch failure    | Error region + readable message; Retry or recoverable path |
| R2  | Replay / stream failure | `.status-error` (or equivalent) + Retry                    |
| R3  | Error color             | Warm red on panel — **not** live orange alone              |

- [ ] R1–R3 pass VISUAL_SPEC §4.

## Motion / reduced motion

- [ ] Default: hover/tab transitions ≤ ~150ms; no gratuitous loops on chrome.
- [ ] Live indicator may breathe; under **prefers-reduced-motion: reduce**, pulse stops (solid orange / static).
- [ ] Skeletons / spinners do not animate under reduced motion (static or text-only).
- [ ] Identity demo / animated mark: static first frame or paused when reduced motion is on (docs/demo surfaces).
- [ ] Launch splash (`golden/s1-launch-splash.png`, `golden/s1-launch-splash-light.png`): branded mark + caption; hold fixtures pin visibility under reduced motion for capture.

Emulate in Chromium DevTools → Rendering → Emulate CSS media feature `prefers-reduced-motion: reduce`.

## Harness

Run the headless contract check from the repository root (no GUI or Node install required):

```powershell
pwsh -NoProfile -File tests/visual/harness/validate.ps1
```

The accessibility suite builds the production `sl-viewer` Dioxus web target,
serves the generated WASM application over HTTP, and runs axe-core WCAG AA
(including contrast) on every viewer tab at 375, 768, and 1280 CSS pixels. It
also exercises the production ARIA tab state, focus order, and Escape-to-clear
behavior documented in [`docs/viewer-hotkeys.md`](../../docs/viewer-hotkeys.md).
The responsive overflow suite visits the same built viewer tabs at
360, 768, and 1280 CSS pixels and asserts the document and body scroll widths
do not exceed their client widths. Install the `wasm32-unknown-unknown` target
and Dioxus CLI 0.7.9, then run:

```powershell
rustup target add wasm32-unknown-unknown
cargo install dioxus-cli --version 0.7.9 --locked
cd crates/sl-viewer
dx build --platform web --release --debug-symbols false --no-default-features --features web
cd ../../tests/visual/harness
npm ci
npx playwright install chromium
npm run test:a11y
npm run test:responsive
```

The harness starts its small static server automatically and expects the build
at `target/dx/sl-viewer/release/web/public` (override with
`A11Y_VIEWER_DIR` when using a custom Cargo target directory). The check
therefore covers the real Dioxus components, styles, generated DOM, and browser
event handlers—not a parallel HTML mirror.

Residual platform gap: CI runs the viewer's production **web** renderer with
mock corpus data. It does not cover native WebView/OS chrome, SQLite-backed
data, or a live daemon response. Those inputs can change content and native
integration, but the audited component markup and CSS are the same source used
by the desktop viewer.

For an already-built viewer, the short form is:

```powershell
cd tests/visual/harness
npm ci
npx playwright install chromium
npm run test:a11y
npm run test:responsive
```

`.github/workflows/a11y.yml` runs both `validate.ps1` and this Playwright suite
on Ubuntu as a blocking pull-request check.

The Playwright visual spec compares the default Bundles empty state with
`golden/e1-bundle-empty.png`. Build the web viewer, then:

```powershell
cd tests/visual/harness
npm ci
npx playwright install chromium
npm run test:visual
```

The harness starts its static server automatically unless `VISUAL_BASE_URL` points at an already-running viewer. To intentionally create or refresh an approved baseline, run `npm run test:visual -- --update-snapshots`, inspect the image, record it in [`PROVENANCE.md`](PROVENANCE.md), and commit it.

Harness layout:

```text
tests/visual/
  README.md          ← this file
  PROVENANCE.md      ← golden filename to screen mapping
  golden/            ← approved baseline PNGs
    e1-bundle-empty.png
    e2-history-empty.png
    e3-timeline-zero.png
    e4-search-empty.png
    e5-first-run-empty.png
    l1-search-loading.png
    l1-content-skeleton.png
    r1-search-error.png
    r2-replay-error.png
    r3-error-color.png
    s1-launch-splash.png
    s1-launch-splash-light.png
  harness/
    a11y.spec.js       ← axe across every built viewer tab + keyboard evidence
    responsive.spec.js ← document-level no-horizontal-overflow evidence
    serve-viewer.mjs   ← static server for the Dioxus web build
    validate.ps1      ← headless VISUAL_SPEC contract check
    visual.spec.js   ← Playwright golden comparison
```

Suggested compare tolerance: ≤ 0.1% pixel diff on non-AA regions; ignore OS window chrome.

Directory `golden/` stores approved baselines; commit PNGs only after intentional refresh and review.

## Related checklists

- Icon / mark palette: [`assets/icons/CHECKLIST.md`](../../assets/icons/CHECKLIST.md)
- Identity demo media: [`docs/assets/identity/README.md`](../../docs/assets/identity/README.md)
