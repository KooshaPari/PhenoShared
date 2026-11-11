# Viewer design-token consistency (C09 L81.8)

SessionLedger viewer chrome uses one Lab-Coat token source:

| Layer       | Path                                                                     | Role                                                       |
| ----------- | ------------------------------------------------------------------------ | ---------------------------------------------------------- |
| CSS SSOT    | [`assets/tokens.css`](../../assets/tokens.css)                           | `--lc-*` brand + `--sl-*` viewer aliases                   |
| Rust mirror | [`crates/sl-viewer/src/tokens.rs`](../../crates/sl-viewer/src/tokens.rs) | Typed hex constants + embedded `TOKENS_CSS`                |
| Theme API   | [`crates/sl-viewer/src/theme.rs`](../../crates/sl-viewer/src/theme.rs)   | `ThemeColors` reads `tokens::lab_coat::*`                  |
| App chrome  | [`crates/sl-viewer/src/app.rs`](../../crates/sl-viewer/src/app.rs)       | Embeds `TOKENS_CSS`; component CSS uses `var(--sl-*)` only |

Do **not** re-declare `--sl-accent` / Lab-Coat brand hexes inside `app.rs`. Prefer `var(--sl-*)` or `ThemeColors` / `tokens::lab_coat`.

## SelfCheck

```powershell
pwsh ./scripts/design-tokens-check.ps1 -SelfCheck
```

Also covered by `cargo test -p sl-viewer tokens::`.
