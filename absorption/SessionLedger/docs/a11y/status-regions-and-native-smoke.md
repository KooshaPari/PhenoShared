# Status regions, cognitive copy, and native WebView smoke

Machine-claimable accessibility evidence for SessionLedger viewer **status visibility**
(L81.7), **inclusive help copy** (L81.10), and **keyboard efficiency** (L81.14).

## Automated contract (CI)

| Check                        | Location                                                                      | What it proves                                                                                                                                    |
| ---------------------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Status region ARIA           | `tests/visual/harness/a11y.spec.js`                                           | `role=status` / `role=alert`, `aria-live`, `aria-busy` on fixture-driven loading, skeleton, and error surfaces                                    |
| Error-field association      | `/?fixture=search-error` + Playwright                                         | Search fields set `aria-invalid` / `aria-errormessage` to the alert id; Retry is `aria-describedby` the error detail                              |
| Destructive clear confirm    | Search tab Clear                                                              | Lightweight `alertdialog` before wiping filters/results/errors (Escape dismisses confirm; second Escape clears immediately for keyboard recovery) |
| Overlay escape precedence    | `a11y.spec.js` + [`overlay-escape.md`](overlay-escape.md)                     | Palette/help close on Escape even with focus in a text field; search-error fixture dismisses on Escape                                            |
| Long-operation patience hint | `/?fixture=loading-long` + Playwright                                         | Plain-language ETA-style copy for operations that may exceed ~10s                                                                                 |
| Stream skeleton status       | `/?fixture=stream-skeleton` + Playwright                                      | Live Feed connecting state exposes content-shaped skeleton + labelled status badge                                                                |
| Reduced motion               | `a11y.spec.js`                                                                | Spinner animation flattened under `prefers-reduced-motion: reduce` (global guard in `app.rs`)                                                     |
| Landmarks                    | `a11y.spec.js`                                                                | `navigation` + `main` landmarks on every production tab                                                                                           |
| Help golden snapshot         | `tests/fixtures/a11y/help_shortcuts.golden.tsv` + `help_overlay.rs` unit test | Keyboard-help table stays in sync with shipped overlay copy                                                                                       |
| Inclusive language seed      | `scripts/inclusive-language-check.ps1` in `.github/workflows/a11y.yml`        | Docs + viewer user-facing strings avoid deny-list terms                                                                                           |

Build the web viewer before local runs:

```powershell
cd crates/sl-viewer
dx build --platform web --release --no-default-features --features web
cd ../../tests/visual/harness
npm ci
npx playwright test a11y.spec.js
```

## Visual fixtures

| Query                       | Tab       | Surface exercised                                                                                                 |
| --------------------------- | --------- | ----------------------------------------------------------------------------------------------------------------- |
| `/?fixture=skeleton`        | Bundles   | `ContentSkeleton` (`aria-busy`, `aria-label`)                                                                     |
| `/?fixture=loading-long`    | Bundles   | `LoadingState` + patience hint for long loads                                                                     |
| `/?fixture=search-error`    | Search    | `ErrorState` (`role=alert`, Retry); fields expose `aria-invalid` + `aria-errormessage` pointing at the alert `id` |
| `/?fixture=stream-skeleton` | Live Feed | Stream skeleton + `aria-label` status badge                                                                       |

## Native WebView smoke checklist (manual, ~5 min)

Run the desktop viewer (`cargo run -p sl-viewer` with the desktop feature) and tick each item.
OS window chrome is outside the browser harness; this checklist captures what auditors should verify on the shipped shell.

1. **Landmarks** — Tab to the sidebar: VoiceOver/NVDA announces “Primary viewer navigation”. Tab into the main panel: “main” region is reachable.
2. **Status while loading** — With daemon stopped, open **Live Feed**: hear or see “Connecting…” status; skeleton blocks appear without layout jump.
3. **Error recovery** — Trigger a Search failure (daemon down): alert copy is plain language (“Something went wrong” + detail), Retry is keyboard-focusable.
4. **Reduced motion** — Enable OS “reduce motion”, relaunch viewer: tab transitions and loading spinner do not animate distractingly.
5. **Keyboard efficiency** — Press `?` (outside a text field): help overlay opens with shortcut table; `Escape` closes and focus returns to **Help (?)**.
6. **Search escape hatch** — On Search tab, type in a filter, press `Escape`: fields clear, focus stays in the filter.

Record pass/fail and build ID in your audit worksheet, or write machine-readable
evidence with `scripts/record-native-webview-smoke.ps1` (schema sample:
[`docs/ops/fixtures/native-webview-smoke.sample.json`](../ops/fixtures/native-webview-smoke.sample.json)).
Do not claim Authenticode or platform signing here — see packaging ADR 0003 for
the portable trust model.

## Live-daemon native WebView parity

The web Playwright harness exercises **fixture** surfaces only. Native parity
against a **live** `sl-daemon` needs both a short manual pass and optional probe
evidence from the recorder.

### Prerequisites

1. Start the daemon (`cargo run -p sl-daemon -- serve` or `make dev`) so
   `GET /readyz` returns `200` on the bind you will use (default
   `http://127.0.0.1:8080`).
2. Launch the desktop viewer with the same base URL the viewer modules expect
   (`127.0.0.1:8080` for Search/Bundles; Live Feed currently targets
   `localhost:9001/api/stream` — point or proxy the stream bind accordingly, or
   treat stream as skip until the shell is aligned).

### Manual checklist (daemon up, ~5 min)

1. **Bundles load** — Bundles tab shows real OKF rows (or an empty list) without
   a stuck skeleton; status region settles to idle.
2. **Search recovery** — With daemon **up**, submit Search; results or empty
   state appear. Then stop the daemon and Retry: assertive alert + named Retry
   still work (same contract as `/?fixture=search-error`).
3. **Live Feed status** — Open Live Feed: Connecting → Live (or Disconnected)
   status badge remains a labelled live region without announcement floods.
4. **Layout parity** — At a narrow window (~360 CSS px), tabs and primary
   controls stay usable; no horizontal page scroll from live payloads.

### Recorder attach mode

After the manual ticks, record machine-readable evidence that also probes the
daemon HTTP surface (does not replace the SR/viewer checklist):

```powershell
pwsh -NoProfile -File scripts/record-native-webview-smoke.ps1 `
  -Outcome pass `
  -AttachDaemon `
  -DaemonUrl http://127.0.0.1:8080 `
  -ScreenReader NVDA `
  -OutPath docs/ops/fixtures/native-webview-smoke.local.json
```

`-AttachDaemon` sets `mode=live-daemon` and fills `daemon.probes` for
`/healthz`, `/readyz`, `/api/bundles`, `/api/search`, and `/api/stream`. Probe
failures refuse `outcome=pass` (use `-Outcome fail|partial` when filing a known
gap). `-SelfCheck` validates the sample fixture + attach arg contract without
talking to a daemon.

Keep `native-webview-smoke.local.json` untracked unless an audit package asks
for it.

For NVDA/VoiceOver announcement checks and what axe/ARIA already cover in CI,
see [`docs/a11y/screen-reader-smoke.md`](screen-reader-smoke.md).

## Related references

- [`docs/a11y/screen-reader-smoke.md`](screen-reader-smoke.md) — L81.4 SR procedure
- [`docs/viewer-hotkeys.md`](../viewer-hotkeys.md) — keyboard contract
- [`docs/a11y/overlay-escape.md`](overlay-escape.md) — Escape precedence for overlays and recovery
- [`docs/HELP.md`](../HELP.md) — operator help
- [`docs/VISUAL_SPEC.md`](../VISUAL_SPEC.md) §3–5 — loading, skeleton, and error anatomy
