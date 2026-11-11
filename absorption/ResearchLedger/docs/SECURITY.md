# Security and privacy

ResearchLedger is local-first. Vault Markdown, SQLite databases, imported source content,
tokens, and browser state are local artifacts and must not be committed or uploaded.

- GitHub credentials are read only by the Rust backend from the authenticated local GitHub CLI;
  no credential crosses the frontend IPC boundary.
- The GitHub adapter is read-only: it lists stars and reads repository READMEs.
- Reddit and X support use a user-directed local browser capture for
  read-only collection of activity / saved posts / bookmarks. None of them automate
  posting, messaging, reactions, follows, votes, or other account actions.
- The Reddit and X browser connectors each use a user-selected persistent
  local profile only for reading the appropriate saved-posts page, apply bounded
  scrolling and deduplication, and store only extracted post text/URLs in the
  capture file; browser cookies remain in the dedicated profile.
- Tauri filesystem commands must validate user-selected roots before reading or writing.
- The production renderer CSP permits bundled Tauri assets and renderer-to-Rust IPC only.
  Provider requests run in Rust or the packaged local browser helpers, so their URLs are
  deliberately not renderer CSP sources. The development-only CSP additionally permits the
  Vite server and its local HMR WebSocket at `127.0.0.1:5173`.
- Logs and error messages must redact tokens and authentication artifacts.
- CI uses synthetic fixtures and never requires real credentials or personal data.
- Users can delete imported Markdown and rebuild SQLite indexes from the vault.

Before release, review Tauri capabilities, macOS signing/notarization settings, dependency
licenses, and the exact external service terms for every enabled connector.

## Known accepted risks

### `glib` 0.18.x — RUSTSEC-2024-0429 (GHSA-wrw7-89jp-8q8g, CVSS 6.9)

The `glib` crate (via `glib::VariantStrIter::impl_get`) has an unsound `&*mut c_char`
out-argument pass that crashes on iteration in optimised builds. **ResearchLedger
does not reach this code path.**

- `glib` is transitive: `webkit2gtk 2.0.2` → `gtk 0.18.2` → `glib 0.18.5`.
- Linux only. macOS builds use `WKWebView` via `objc`; `cargo tree -i glib`
  reports "nothing to print" on the macOS target.
- App source contains zero references to `glib::Variant`, `VariantStrIter`,
  or `use glib` (verified by `grep -rn`).
- The patched release is `glib 0.20.0`, which requires a breaking upgrade
  of the entire `gtk-rs` stack. The current stack is pinned by the
  Tauri 1.x line.

**Mitigation:** none required at the application layer. Track for
remediation when Tauri/webkit2gtk bumps to the `gtk-rs` 0.20+ series.

GitHub Dependabot alert #1 (medium) is dismissed with the `tolerable_risk`
reason and the comment recorded in the alert audit trail.

### Playwright browser binary download (one-time, on first permitted capture)

The Reddit and X capture scripts use Playwright's persistent
Chromium context. Chromium is **not** bundled with the .app to keep the
installer size small; instead, on first launch of any capture script, the
helper runs `npx playwright install chromium` to fetch the browser binary
into `~/Library/Caches/ms-playwright/`. This is a single ~150 MB download
from Playwright's CDN (microsoft.com via `playwright.azureedge.net`).

- The download happens automatically the first time the user clicks a permitted
  browser-capture action.
- The cache lives in the user's home Library; it is shared across all
  Playwright projects on the machine.
- No data leaves the user's machine beyond the Playwright CDN request for
  the browser binary itself.
- No Playwright telemetry is enabled — Playwright is invoked in
  `headless: false` mode with no `PW_TEST_CONNECT_WS` or remote-debug
  endpoints configured.
