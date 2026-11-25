# SessionLedger Viewer Help

Short reference for the in-viewer keyboard help overlay, command palette, and related docs.

## Open help in the viewer

| Action             | Result                                                                     |
| ------------------ | -------------------------------------------------------------------------- |
| Press `?`          | Toggle the keyboard help overlay (ignored while focus is in a text field). |
| Click **Help (?)** | Open or close the same overlay from the sidebar.                           |
| Press `Escape`     | Close the overlay and return focus to the Help control.                    |

The overlay is an accessible dialog (`role="dialog"`, `aria-modal="true"`) listing the
current viewer shortcuts. It is implemented in `crates/sl-viewer/src/help_overlay.rs`.

## Command palette

| Action                   | Result                                                 |
| ------------------------ | ------------------------------------------------------ |
| Press `Cmd+K` / `Ctrl+K` | Toggle the command palette (works in text fields too). |
| Press `Escape`           | Close the palette.                                     |

The palette ships six commands — focus search, open keyboard help, next/previous
view tab, clear search, and toggle theme — in
`crates/sl-viewer/src/command_palette.rs`.

## Progressive disclosure (Search)

Beyond the command palette, the Search tab keeps date and model filters visible
and hides **Min Tokens**, **Tags**, and **Limit** behind **Show advanced
filters**. An **N active** badge appears when collapsed advanced criteria still
apply. See [`a11y/progressive-disclosure.md`](a11y/progressive-disclosure.md).

## Related references

- [`docs/ops/sl-viewer-help.md`](ops/sl-viewer-help.md) — `sl-viewer --help` / `--version` and `SL_DAEMON_URL`, `FORGE_DB` env SSOT.
- [`viewer-hotkeys.md`](viewer-hotkeys.md) — canonical shortcut table and test evidence.
- [`a11y/progressive-disclosure.md`](a11y/progressive-disclosure.md) — Search advanced-filter disclosure.
- [`guides/quick-start/QUICKSTART.md`](guides/quick-start/QUICKSTART.md) — first-run stack setup.

## Automated checks

`tests/visual/harness/a11y.spec.js` asserts that `?` opens help, `Ctrl+K` opens the
command palette, `Escape` closes either overlay, and Search advanced filters
expand/collapse with correct `aria-expanded` state against the production Dioxus
web build.
