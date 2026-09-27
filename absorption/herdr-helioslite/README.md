# herdr-helioslite

Herdr plugin for [HeliosLite](https://github.com/KooshaPari/HeliosLite) — the
AI pair-programmer CLI for Claude, GPT, Gemini, Grok, Deepseek, and 300+ models.

## What it does

Wraps the **stock** HeliosLite CLI in a thin observer: every pane lifecycle
transition (`session_start`, `turn_start`, `turn_end`, `error`, `blocked`,
`session_end`) is forwarded to your local Herdr daemon via
`pane.report_agent`, so multiple HeliosLite panes (and other agents) are
visible in one place without taking over the TUI. **No fork of HeliosLite
required** — this plugin only needs the `helioslite` binary on `PATH`.

## Install

```bash
# 1. Install HeliosLite first (optional — plugin no-ops gracefully if absent):
#    https://github.com/KooshaPari/HeliosLite
#    (the plugin will idle until `helioslite` is on PATH)

# 2. Install this plugin via Herdr:
herdr plugin install KooshaPari/herdr-helioslite
```

Or, from a local clone:

```bash
./install.sh
herdr plugin install herdr-helioslite
```

## Use

Once installed, open a HeliosLite TUI in any pane Herdr watches. The plugin's
detection rule (`agent-detection/helioslite.toml`) matches HeliosLite's banner
and prompt, so the pane is automatically labelled `helioslite`. You can
verify this from another shell:

```bash
herdr-helioslite-report ping         # → pong if daemon reachable
herdr-helioslite-report status       # → emits idle with install location
herdr-helioslite-report detect       # → reads stdin, prints helioslite|unknown
herdr-helioslite-report report session_start "starting helioslite work"
herdr-helioslite-report report turn_end   "model returned"
herdr-helioslite-report report error      "model timed out"
```

## Why this exists

See [`docs/HERDR_VS_ACP.md`](docs/HERDR_VS_ACP.md) for the architectural
answer to "why doesn't Herdr just consume ACP?". TL;DR: Herdr is an always-on
observation substrate; ACP is a wire protocol for the active tool call. They
answer different questions, and for off-the-shelf HeliosLite we don't own
the ACP server — so we wrap the binary instead of forking it.

## Cross-platform

| Platform | Status | Notes |
|---|---|---|
| macOS   | yes | bash 3.2+ |
| Linux   | yes | bash 4+ |
| Windows | yes | git-bash, msys, WSL — `helioslite.exe` is auto-detected |
| Native cmd.exe / PowerShell | no | not supported (would need a separate .ps1 installer; PRs welcome) |

The bash entrypoint detects `uname -s` and appends `.exe` to `helioslite` on
Windows shells. On Linux/macOS the script works with the bare `helioslite`
binary or `$HELIOSLITE_BIN` env override.

## No fork required

This plugin does **not** ship a fork of HeliosLite. It wraps the stock binary
and observes its lifecycle from the outside. The upstream
[`leonardoacosta.herdr-jcode`](https://github.com/leonardoacosta/herdr-jcode)
plugin took the same approach for stock jcode — and this plugin follows that
precedent for HeliosLite.

## Layout

```
herdr-helioslite/
├── herdr-plugin.toml                  # manifest
├── bin/
│   └── herdr-helioslite-report        # bash entrypoint (set -euo pipefail)
├── agent-detection/
│   └── helioslite.toml                # screen-rule detection
├── install.sh                         # cross-platform installer
├── uninstall.sh                       # cross-platform uninstaller
├── README.md                          # this file
└── docs/
    └── HERDR_VS_ACP.md                # architectural answer
```

## License

MIT.
