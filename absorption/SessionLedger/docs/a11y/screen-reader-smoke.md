# Screen-reader smoke (L81.4)

Manual NVDA / VoiceOver procedure for SessionLedger viewer **screen-reader
compatibility**, plus what CI already proves via axe and ARIA contracts.

Companion: [`status-regions-and-native-smoke.md`](status-regions-and-native-smoke.md)
(status regions, cognitive copy, native WebView shell checklist).

## What CI already proves (axe / ARIA)

| Check                                     | Location                               | Screen-reader relevance                                                     |
| ----------------------------------------- | -------------------------------------- | --------------------------------------------------------------------------- |
| WCAG 2.A/2.AA axe scan per tab × 3 widths | `tests/visual/harness/a11y.spec.js`    | No critical name/role/value or landmark regressions in the built web viewer |
| Tablist keyboard pattern                  | same                                   | Arrow/Home/End move selection; `aria-selected` tracks focus                 |
| Primary control accessible names          | same                                   | Theme toggle, Help, search filter fields, Retry reachable by role + name    |
| Status / alert live regions               | same + fixtures                        | `role=status` / `role=alert` with `aria-live` on loading, skeleton, error   |
| Landmarks                                 | same                                   | `navigation` (“Primary viewer navigation”) + `main` on every production tab |
| Help dialog labelling                     | same                                   | Dialog `aria-labelledby`, shortcut table columnheaders                      |
| Inclusive language seed                   | `scripts/inclusive-language-check.ps1` | User-facing docs/strings avoid deny-list terms                              |

CI does **not** run a real screen reader. Treat axe/ARIA as a regression net; use
the checklist below for announcement quality, verbosity, and OS chrome.

## Prerequisites

1. Build the web viewer (or desktop with WebView) from a clean worktree. Prefer a
   worktree-local target dir so parallel lanes do not collide:

   ```powershell
   $env:CARGO_TARGET_DIR = "$PWD/target-w23-c09"
   cd crates/sl-viewer
   dx build --platform web --release --no-default-features --features web
   ```

2. For web smoke: serve `tests/visual/harness` (`npm ci` then
   `npx playwright test a11y.spec.js`) or open the built assets in a browser with
   the SR attached.
3. For native shell: `cargo run -p sl-viewer` with the desktop feature (see native
   checklist in the companion doc), then attach NVDA (Windows) or VoiceOver (macOS).

## NVDA checklist (Windows, ~8 min)

Use browse mode (NVDA+Space toggles) for landmarks; focus mode for forms.

1. **Landmarks** — NVDA+F7 → Landmarks: hear **Primary viewer navigation** and
   **main**. Tab into the sidebar; confirm “SessionLedger views” tablist.
2. **Tabs** — Focus Bundles; ArrowRight: History is selected and announced;
   Home/End reach Bundles / Replay.
3. **Theme toggle** — Tab to **Toggle light and dark theme**; Activate: theme
   change is announced or visible without losing focus context.
4. **Help** — Activate **Help (?)**; dialog “Keyboard shortcuts” is announced;
   Escape closes and focus returns to Help.
5. **Search filters** — Open Search; Tab through **Since (YYYY-MM-DD)** and
   **Model (substring)**; labels are spoken with the fields.
6. **Bundles filter** — On Bundles (after load): find **Filter sessions** by
   name; typing filters the list without unexplained focus jumps.
7. **Error + Retry** — `/?fixture=search-error` (web) or fail Search with daemon
   down: assertive alert “Something went wrong”; **Retry** is a named button and
   activatable with Enter/Space.
8. **Live status** — Live Feed connecting: polite status / “Connecting…” without
   flooding (no endless identical announcements every frame).

## VoiceOver checklist (macOS, ~8 min)

Use VO+U for the rotor; VO+Left/Right to move.

1. **Rotor → Landmarks** — Primary viewer navigation + main present.
2. **Rotor → Form Controls** — Theme toggle, Help (?), Search fields, Retry (on
   error fixture) appear with the names above.
3. **Tabs** — Interact with the tablist; VO+Right across tabs updates selection
   announcement.
4. **Help dialog** — Open Help; VO announces dialog title; Escape dismisses and
   restores Help button focus.
5. **Status / alert** — Loading/skeleton fixtures announce busy status; search
   error announces assertively; Retry remains in the form-controls rotor.

## Recording a pass

Write machine-readable native WebView smoke evidence (schema sample + recorder):

- Fixture: [`docs/ops/fixtures/native-webview-smoke.sample.json`](../ops/fixtures/native-webview-smoke.sample.json)
- Recorder: `pwsh -NoProfile -File scripts/record-native-webview-smoke.ps1`
- Live daemon (optional): add `-AttachDaemon -DaemonUrl http://127.0.0.1:8080`
  after the [live-daemon native parity](status-regions-and-native-smoke.md#live-daemon-native-webview-parity)
  checklist so evidence includes HTTP probes beyond the fixture sample.

See [CONTRIBUTING.md](../../CONTRIBUTING.md#native-webview-accessibility-smoke)
for maintainer steps. Do not claim platform code-signing here — ADR 0003.

## Related references

- [`docs/viewer-hotkeys.md`](../viewer-hotkeys.md) — keyboard contract
- [`docs/a11y/status-regions-and-native-smoke.md`](status-regions-and-native-smoke.md) — status/cognitive + OS shell
- [`docs/VISUAL_SPEC.md`](../VISUAL_SPEC.md) §3–5 — loading, skeleton, and error anatomy
