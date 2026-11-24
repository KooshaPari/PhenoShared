# sl-viewer — SessionLedger bundle viewer

A Dioxus 0.7 single-codebase viewer for compiled SessionLedger bundles —
desktop (native) and web (WASM) from one source tree.

## Platform targets

### Desktop (default)

```bash
cargo run -p sl-viewer
```

Opens a native window with the bundle list + detail pane.

### Web (WASM)

The web target requires the `web` feature and the Dioxus CLI (`dx`):

```bash
# Install the Dioxus CLI (one time)
cargo install dioxus-cli

# Terminal 1: start the local daemon with a session watch directory and an output directory.
cd ../sl-daemon
cargo run -- serve --watch ./sessions --out ./okf-out --http-bind 127.0.0.1:8080

# Terminal 2: build and serve the browser viewer against that loopback daemon.
cd ../sl-viewer
SL_DAEMON_URL=http://127.0.0.1:8080 dx serve --platform web --port 8081
```

This compiles `sl-viewer` to WASM and serves it on `http://localhost:8081`.
The **Bundles** screen calls `GET /api/bundles` on `SL_DAEMON_URL` and renders
the daemon's current OKF documents. With the daemon unavailable, it shows a
retryable error instead of embedded demo data. The desktop target remains
local-corpus-first; its native discovery behavior is unchanged.

## Cargo features

| Feature   | Default | Enables                     |
| --------- | ------- | --------------------------- |
| `desktop` | yes     | `dioxus/desktop` — native   |
| `web`     | no      | `dioxus/web` — WASM browser |

The entry point in `src/main.rs` uses `#[cfg]` gates to select the correct
renderer at compile time.
