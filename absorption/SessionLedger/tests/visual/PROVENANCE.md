# Visual Golden Provenance

These PNG baselines are approved browser-rendered captures for the Playwright
visual contract in `tests/visual/harness/visual.spec.js`.

| Golden                              | Screen                                        | Route / state                                           | Viewport          | Motion                           | Notes                                                                                                      |
| ----------------------------------- | --------------------------------------------- | ------------------------------------------------------- | ----------------- | -------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `golden/e1-bundle-empty.png`        | Bundles tab, detail pane empty state          | `/` with the default mock corpus and no bundle selected | 1280x720 Chromium | `prefers-reduced-motion: reduce` | Locks VISUAL_SPEC E1: the muted "Select a bundle..." empty detail state is distinct from error styling.    |
| `golden/e2-history-empty.png`       | History tab, detail pane empty state          | `/?fixture=history-empty`                               | 1280x720 Chromium | `prefers-reduced-motion: reduce` | Locks VISUAL_SPEC E2: muted "Select a session..." empty detail state.                                      |
| `golden/e4-search-empty.png`        | Search tab, zero-match empty state            | `/?fixture=search-empty`                                | 1280x720 Chromium | `prefers-reduced-motion: reduce` | Locks VISUAL_SPEC E4: zero-match copy without `.search-error` styling.                                     |
| `golden/e5-first-run-empty.png`     | Bundles tab, first-run activation empty state | `/?fixture=first-run`                                   | 1280x720 Chromium | `prefers-reduced-motion: reduce` | Locks VISUAL_SPEC first-run variant: instructional copy + cobalt CTA, not error styling.                   |
| `golden/r1-search-error.png`        | Search tab, fetch failure                     | `/?fixture=search-error`                                | 1280x720 Chromium | `prefers-reduced-motion: reduce` | Locks VISUAL_SPEC R1: error region with retry affordance.                                                  |
| `golden/r2-replay-error.png`        | Replay tab, SSE stream failure                | `/?fixture=replay-error`                                | 1280x720 Chromium | `prefers-reduced-motion: reduce` | Locks VISUAL_SPEC R2: `.status-error` copy + Retry on replay surface.                                      |
| `golden/r3-error-color.png`         | Bundles tab, error color contract             | `/?fixture=error-color`                                 | 1280x720 Chromium | `prefers-reduced-motion: reduce` | Locks VISUAL_SPEC R3: warm red error foreground on slate panel, distinct from live orange.                 |
| `golden/l1-content-skeleton.png`    | Bundles tab, content-shaped loading skeleton  | `/?fixture=skeleton` on the Bundles tab                 | 1280x720 Chromium | `prefers-reduced-motion: reduce` | Locks VISUAL_SPEC L99: list + detail shimmer blocks preserve layout without CLS.                           |
| `golden/s1-launch-splash.png`       | Viewer launch splash (dark theme)             | `/?fixture=launch-splash`                               | 1280x720 Chromium | `prefers-reduced-motion: reduce` | Locks L103: branded SessionLedger mark + Viewer caption held via `.launch-splash-hold` (no dismiss timer). |
| `golden/s1-launch-splash-light.png` | Viewer launch splash (light theme)            | `/?fixture=launch-splash-light`                         | 1280x720 Chromium | `prefers-reduced-motion: reduce` | Locks L103 theme variant: same splash chrome on lab-white / cobalt light tokens.                           |

Refresh with:

```powershell
cd tests/visual/harness
npm run test:visual -- --update-snapshots
```

## Tolerance

maxDiffPixelRatio is 0.03 to absorb Linux vs Windows Chromium font AA while still failing layout regressions.
