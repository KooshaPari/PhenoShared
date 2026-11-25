# Progressive disclosure (C09 L81.12)

SessionLedger keeps recognition over recall by revealing complexity only when
operators ask for it. Beyond the `Cmd+K` / `Ctrl+K` command palette, the Search
view uses progressive disclosure for advanced query parameters.

## Search advanced filters

| Layer   | Path                                                                               | Role                                                                                 |
| ------- | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| UI      | [`crates/sl-viewer/src/search_view.rs`](../../crates/sl-viewer/src/search_view.rs) | Primary fields always visible; Min Tokens / Tags / Limit behind a disclosure control |
| Chrome  | [`crates/sl-viewer/src/app.rs`](../../crates/sl-viewer/src/app.rs)                 | Lab-Coat `--sl-*` styles for toggle, badge, and panel                                |
| Harness | [`tests/visual/harness/a11y.spec.js`](../../tests/visual/harness/a11y.spec.js)     | Expand/collapse, `aria-expanded`, badge recognition                                  |

### Default surface

Always visible:

- **Since** / **Until** date filters
- **Model** substring filter
- Contextual hint that advanced filters are optional

Collapsed by default (toggle **Show advanced filters**):

- **Min Tokens**
- **Tags** (comma-separated)
- **Limit** (default `50`)

### Recognition cues

- The disclosure button exposes `aria-expanded` and `aria-controls="search-advanced-filters"`.
- When any advanced field differs from its default, a teal **N active** badge
  appears on the toggle so operators see that hidden criteria still apply
  without memorizing which fields were set.
- Clear / Escape resets advanced values and collapses the panel.

### Lab-Coat tokens

Toggle, badge, and panel chrome use `var(--sl-*)` only (accent, accent-secondary,
border, surface-muted, text-muted, radius, motion). See
[`design-tokens.md`](design-tokens.md).
