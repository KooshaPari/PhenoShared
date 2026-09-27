# herdr-jcode

A [Herdr](https://herdr.dev) plugin that reports **lifecycle and presence events**
from the stock [Jcode](https://github.com/KooshaPari/KCode) CLI to the Herdr
daemon. **No fork of Jcode is required** — the plugin wraps the stock `jcode`
binary and emits `pane.report_agent` calls.

It is the cross-platform, no-fork counterpart to the existing community attempts:
[`leonardoacosta.herdr-jcode`](https://github.com/leonardoacosta/herdr-jcode)
(Linux-only) and
[`capt-marbles.jcode-integration`](https://github.com/capt-marbles/herdr-jcode-integration)
(no Windows). This plugin runs on **macOS, Linux, and Windows (git-bash/WSL)** and
pairs with — rather than replaces — Jcode's built-in `jcode-herdr` reporter.

## What it does

Herdr is a long-lived presence and telemetry daemon for terminal AI agents. When
a pane in Herdr runs `jcode`, the plugin watches its lifecycle (session start,
turn start/end, error, session end) and emits advisory `pane.report_agent`
events. Herdr persists these into a pane registry that survives individual
sessions, so even after a Jcode run finishes the pane stays marked `done` and
visible in the UI.

The plugin is a **wrapper**: it does **not** recompile or modify Jcode. It runs
`jcode` as a child process, observes the exit code, and calls Herdr's
`pane.report_agent` API at the right lifecycle moments.

## Install

```sh
# Easiest path — let Herdr clone and load the plugin from GitHub
herdr plugin install KooshaPari/herdr-jcode

# Manual path — clone the repo and run the install companion
git clone https://github.com/KooshaPari/herdr-jcode ~/wt/herdr-jcode
cd ~/wt/herdr-jcode
./install.sh
```

After install, run `herdr server reload-agent-manifests` (or restart Herdr) so the
detection rules in `agent-detection/jcode.toml` are picked up.

## Use

Once installed, any pane that Herdr detects as running `jcode` auto-emits
presence events. You can also invoke the wrapper directly:

```sh
# Inside a Herdr-managed pane, the wrapper mode replaces the binary transparently
herdr-jcode-report jcode exec "summarize this repo"

# Or call the lifecycle actions by hand
herdr-jcode-report session_start
herdr-jcode-report turn_end ok
herdr-jcode-report turn_end error "rate limit hit"
herdr-jcode-report session session_blossom_1789125438468_65a0cdb3f092c774
herdr-jcode-report session_end
```

To see what Herdr has recorded for a pane:

```sh
herdr agent list
herdr agent explain --json
herdr pane get "$HERDR_PANE_ID"
```

## Two reporters, one truth

- **Jcode's own fork** reports natively through the `jcode-herdr` crate
  (`pane.report_agent` / `pane.report_agent_session`) whenever it runs inside a
  Herdr pane.
- **This plugin** provides the same reports for *stock* Jcode, and a way to drive
  the lifecycle by hand or from a shell hook.

Herdr enforces one status authority per pane, so you never get two competing
sources of truth on the same pane.

## Why this exists

Herdr and ACP solve different problems. See
**[`docs/HERDR_VS_ACP.md`](docs/HERDR_VS_ACP.md)** for the full architectural
answer — including why Jcode's built-in ACP server still doesn't make Herdr an
ACP consumer.

## Cross-platform

Supported:
- **macOS** (bash 3.2+ via `/bin/bash`)
- **Linux** (bash 4+)
- **Windows** via **git-bash** (e.g. Git for Windows) or **WSL**

NOT supported:
- Native Windows `cmd.exe` or PowerShell. Bash is required for the wrapper.

The `install.sh` and the wrapper both detect MSYS/Cygwin/git-bash and resolve
`jcode.exe` automatically.

## No fork required

This plugin does not modify Jcode in any way. It does not patch the binary,
hot-load a shared library, or change the upstream source tree. It runs `jcode` as
a child process and reports lifecycle events. To upgrade Jcode you simply upgrade
the binary on PATH; to uninstall this plugin delete the wrapper and detection rule
(see `uninstall.sh`).

## Layout

```
herdr-jcode/
├── herdr-plugin.toml                  # plugin manifest
├── bin/
│   └── herdr-jcode-report             # bash wrapper (self-contained, no jq/python deps)
├── agent-detection/
│   └── jcode.toml                     # pane-detector rules
├── install.sh                         # Herdr plugin install companion
├── uninstall.sh                       # remove plugin artifacts
├── README.md
└── docs/
    └── HERDR_VS_ACP.md                # architectural rationale
```

## Verification

```sh
bash -n bin/herdr-jcode-report install.sh uninstall.sh                      # syntax
shellcheck bin/herdr-jcode-report install.sh uninstall.sh || true           # lint (optional)
python3 -c "import tomllib; tomllib.loads(open('herdr-plugin.toml').read())"
python3 -c "import tomllib; tomllib.loads(open('agent-detection/jcode.toml').read())"
wc -l bin/herdr-jcode-report install.sh uninstall.sh                        # all ≤350 lines
```

## License

MIT
