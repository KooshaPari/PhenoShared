# Overlay escape hatch (Escape key)

Emergency-exit contract for modal overlays and recoverable error surfaces in
`sl-viewer` (L81.8 consistency, L81.9 user control).

## Precedence (top wins)

When the user presses `Escape`, the viewer resolves the key in this order:

1. **Command palette** — closes the palette (`command_palette.rs` + global bridge in `app.rs`).
2. **Keyboard help overlay** — closes help and returns focus to **Help (?)** (`help_overlay.rs` + global bridge).
3. **Search clear confirm** — dismisses the `alertdialog` via the Cancel control (`search_view.rs` + global bridge when focus left the panel).
4. **View recovery** — clears Search filters/results/errors, Replay idle state, or closes the bundle comparison panel.

Palette and help are checked **before** the global “typing in a text field” guard so
`Escape` always dismisses modal chrome even when focus remains in an input behind
the backdrop.

## Implementation map

| Surface              | Handler                                                               | Test                                                            |
| -------------------- | --------------------------------------------------------------------- | --------------------------------------------------------------- |
| Command palette      | `command_palette.rs` `onkeydown` + `app.rs` capture bridge            | `a11y.spec.js` Ctrl+K / Escape                                  |
| Keyboard help        | `help_overlay.rs` `onkeydown` + `app.rs` capture bridge               | `a11y.spec.js` Help / Escape; Escape with focus in Search field |
| Search clear confirm | `search_view.rs` `onkeydown` + `app.rs` capture bridge (Cancel click) | `a11y.spec.js` Clear confirm Escape                             |
| Search error         | `search_view.rs` `onkeydown` (live + `/?fixture=search-error`)        | `a11y.spec.js` search-error Escape                              |
| Replay idle reset    | `replay_view.rs` `onkeydown`                                          | documented in `viewer-hotkeys.md`                               |
| Bundle compare       | `app.rs` Bundles tab `onkeydown`                                      | documented in `viewer-hotkeys.md`                               |

The global bridge clicks existing close buttons so Dioxus `onclick` handlers own
state — see the comment above `use_effect` in `app.rs`.

## Related references

- [`docs/viewer-hotkeys.md`](../viewer-hotkeys.md) — shortcut table
- [`docs/a11y/status-regions-and-native-smoke.md`](status-regions-and-native-smoke.md) — CI harness index
- [`docs/HELP.md`](../HELP.md) — operator help
