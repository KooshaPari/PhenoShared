# macOS packaging (unsigned)

Scripts here produce an unsigned `.app` and a `productbuild` `.pkg`.
Apple Developer ID signing and notarization remain deferred
([ADR 0003](../../docs/adr/0003-platform-code-signing.md)).

## Prerequisites

- Xcode command line tools (`productbuild`, `pkgutil`)
- A release `sl-viewer` binary (`cargo build -p sl-viewer --release`)

## Usage

```sh
# From repo root, after building for the host (or a cross target):
export VERSION=0.1.0
export BINARY=target/aarch64-apple-darwin/release/sl-viewer
export ARCH_LABEL=aarch64
./packaging/macos/package-app.sh
./packaging/macos/package-pkg.sh
```

Outputs land under `packaging/dist/`:

- `SessionLedger.app`
- `SessionLedger-<version>-<arch>.pkg` when `ARCH_LABEL` is set

## Local install

After building an app bundle, install it into the current Mac's Applications
folder without elevating privileges:

```sh
./packaging/macos/install-local.sh
```

The script validates the bundle executable, preserves an existing install as
`SessionLedger.app.previous`, and never creates a background service with an
implicit service. To install a locally-built daemon as well, opt in:

```sh
INSTALL_DAEMON=1 ./packaging/macos/install-local.sh
```

The installer prints `sl-daemon serve --out ...`, which enables native
discovery of supported local session stores. Add `--watch <path>` only when a
custom transcript root is required.

For unattended local ingestion, explicitly opt in to a per-user LaunchAgent.
It uses the daemon's native auto-discovery (no `--watch` path is stored),
writes bundles/logs below `~/.local/share/sessionledger`, and rejects
non-loopback HTTP binds:

```sh
START=1 ./packaging/macos/install-launch-agent.sh
sl-daemon status
launchctl print "gui/$UID/com.sessionledger.daemon"
```

Stop/remove it with `launchctl bootout "gui/$UID/com.sessionledger.daemon"`
and remove `~/Library/LaunchAgents/com.sessionledger.daemon.plist`. This is a
separate explicit action so installing the app never starts a process or
begins reading local transcripts unexpectedly.

Release CI builds at least the `aarch64-apple-darwin` PKG (and `x86_64` when
the matrix target runs) and attaches them as Release assets.
