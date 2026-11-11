# Viewer Hotkeys and Keyboard Navigation

Status: user-facing keyboard contract for the current `sl-viewer` surface.

## Current Shortcuts

| Shortcut            | Scope                   | Behavior                                                                                                                                                |
| ------------------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `?`                 | Whole viewer            | Toggle the in-viewer keyboard help overlay (ignored while focus is in a text field).                                                                    |
| **Help (?)** button | Sidebar                 | Open or close the same keyboard help overlay.                                                                                                           |
| `Cmd+K` / `Ctrl+K`  | Whole viewer            | Toggle the command palette (works even while focus is in a text field).                                                                                 |
| `Tab` / `Shift+Tab` | Whole viewer            | Move through the browser or WebView focus order. The active view tab is the only tab stop in the tablist before focus enters the active panel controls. |
| `ArrowRight`        | Focused view tab        | Select and focus the next view tab, wrapping from Replay to Bundles.                                                                                    |
| `ArrowLeft`         | Focused view tab        | Select and focus the previous view tab, wrapping from Bundles to Replay.                                                                                |
| `Home`              | Focused view tab        | Select and focus Bundles.                                                                                                                               |
| `End`               | Focused view tab        | Select and focus Replay.                                                                                                                                |
| `Enter` / `Space`   | Focused view tab        | Activate the focused view tab.                                                                                                                          |
| `Escape`            | Keyboard help overlay   | Close the overlay and return focus to the Help control.                                                                                                 |
| `Escape`            | Command palette         | Close the palette.                                                                                                                                      |
| `Escape`            | Search view             | Clear search filters, results, and errors without moving focus.                                                                                         |
| `Escape`            | Replay view             | Clear replay output and return the replay panel to idle.                                                                                                |
| `Escape`            | Bundle comparison panel | Close the comparison panel.                                                                                                                             |

### Overlay escape hatch

`Escape` always closes the topmost modal overlay (command palette, then keyboard
help) before view-level recovery runs. Search **Clear** confirmation dismisses on
`Escape` without wiping fields; a second `Escape` (or the live Search path) clears
filters, results, and errors. Full precedence and implementation map:
[`docs/a11y/overlay-escape.md`](a11y/overlay-escape.md).

The current view order is Bundles, History, Unfinished, Memory, Live Feed,
Search, Timeline, and Replay.

## Command palette

`Cmd+K` (macOS) / `Ctrl+K` (Windows/Linux) opens a lightweight command palette
(`role="dialog"` with a `listbox` of options). Current commands:

- **Focus search** — switch to the Search tab and focus the first filter field.
- **Open keyboard help** — open the shortcut reference overlay (`?` equivalent).
- **Next view tab** — select and focus the next tab, wrapping from Replay to Bundles.
- **Previous view tab** — select and focus the previous tab, wrapping from Bundles to Replay.
- **Clear search** — switch to Search and reset filters, results, and errors (same as `Escape` on the Search view).
- **Toggle theme** — switch between light and dark theme.

Arrow keys move the active option; Enter runs it. Escape closes the palette.

## In-app help

Press `?` or choose **Help (?)** in the viewer sidebar to open the keyboard shortcut
overlay. See [`docs/HELP.md`](HELP.md) for a short operator reference.

## Test Evidence

`tests/visual/harness/a11y.spec.js` runs against the built Dioxus web viewer and
covers the ARIA tab keyboard pattern, active-tab tab order, Search
`Escape`-to-clear behavior, Search advanced-filter progressive disclosure
(`aria-expanded` / active badge), keyboard-help open/close via `?` and `Escape`, command
palette open/close via `Ctrl+K` / `Escape`, overlay precedence (help closes while
focus stays in Search), clear-confirm and search-error `Escape` recovery,
fixture-driven status regions
(`skeleton`, `loading-long`, `search-error`, `stream-skeleton`), reduced-motion
spinner flattening, and landmark visibility. The same component source backs the desktop viewer,
with native WebView and OS chrome covered by [`docs/a11y/status-regions-and-native-smoke.md`](a11y/status-regions-and-native-smoke.md).

See also [`docs/a11y/progressive-disclosure.md`](a11y/progressive-disclosure.md).
