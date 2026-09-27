# herdr-forgecode

A [Herdr](https://github.com/KooshaPari/Herdr) plugin that reports **lifecycle and presence events** from the stock [ForgeCode](https://forgecode.dev) CLI to the Herdr daemon. No fork of ForgeCode is required — the plugin wraps the stock `forge` binary and emits `pane.report_agent` calls.

## What it does

Herdr is a long-lived presence and telemetry daemon for terminal AI agents. When a pane in Herdr runs `forge`, the plugin watches its lifecycle (session start, turn end, error, session end) and emits advisory `pane.report_agent` events. Herdr persists these into a pane registry that survives individual sessions, so even after a ForgeCode run finishes, the pane stays marked `done` and visible in the UI.

The plugin is a **wrapper**: it does **not** recompile or modify ForgeCode. It just runs `forge` as a child process, observes the exit code, and calls Herdr's `pane.report_agent` API at the right lifecycle moments.

## Install

```sh
# Easiest path — let Herdr clone and load the plugin from GitHub
herdr plugin install KooshaPari/herdr-forgecode

# Manual path — clone the repo and run the install companion
git clone https://github.com/KooshaPari/herdr-forgecode ~/wt/herdr-forgecode
cd ~/wt/herdr-forgecode
./install.sh
```

After install, restart Herdr (`herdr plugin reload`) so the detection rules in `agent-detection/forgecode.toml` are picked up.

## Use

Once installed, any pane that Herdr detects as running `forge` auto-emits presence events. The detection rules are in `agent-detection/forgecode.toml` — they match the upstream ForgeCode banner, `forge --help` text, and the `forge` command itself.

You can also invoke the wrapper directly to run a turn:

```sh
# Inside a Herdr-managed pane, the wrapper mode replaces the binary transparently
herdr-forgecode-report forge exec "summarize this repo"

# Or call the lifecycle actions by hand
herdr-forgecode-report session_start
herdr-forgecode-report turn_end ok
herdr-forgecode-report turn_end error "rate limit hit"
herdr-forgecode-report session_end
```

To see what Herdr has recorded for a pane:

```sh
herdr pane list
herdr api call pane.report_history pane_id="$HERDR_PANE_ID"
```

## Why this exists

Herdr and ACP solve different problems. See **[`docs/HERDR_VS_ACP.md`](docs/HERDR_VS_ACP.md)** for the full architectural answer.

Short version: ACP is a request/response wire protocol for active tool calls; Herdr is an always-on observation substrate that outlives any single session. To plug ForgeCode into ACP we would have to fork ForgeCode and own its ACP server. This plugin takes the non-invasive path: wrap the stock binary, watch its lifecycle, emit advisory events. The upstream `leonardoacosta.herdr-jcode` plugin did the same for stock `jcode`.

## Cross-platform

Supported:
- **macOS** (bash 3.2+ via `/bin/bash`)
- **Linux** (bash 4+)
- **Windows** via **git-bash** (e.g. Git for Windows) or **WSL**

NOT supported:
- Native Windows `cmd.exe` or PowerShell. Bash is required for the wrapper.

The `install.sh` and the wrapper both detect MSYS/Cygwin/git-bash and resolve `forge.exe` automatically.

## No fork required

This plugin does not modify ForgeCode in any way. It does not patch the binary, hot-load a shared library, or change the upstream source tree. It runs `forge` as a child process and reports lifecycle events. To upgrade ForgeCode you simply upgrade the binary on PATH; to uninstall this plugin you delete the wrapper and detection rule (see `uninstall.sh`).

## Layout

```
herdr-forgecode/
├── herdr-plugin.toml                  # plugin manifest
├── bin/
│   └── herdr-forgecode-report         # bash wrapper (self-contained, no jq/python deps)
├── agent-detection/
│   └── forgecode.toml                 # pane-detector rules
├── install.sh                         # Herdr plugin install companion
├── uninstall.sh                       # remove plugin artifacts
├── README.md
└── docs/
    └── HERDR_VS_ACP.md                # architectural rationale
```

## Verification

```sh
bash -n bin/herdr-forgecode-report install.sh uninstall.sh          # syntax
shellcheck bin/herdr-forgecode-report install.sh uninstall.sh || true # lint (optional)
python3 -c "import tomllib; tomllib.loads(open('herdr-plugin.toml').read())"
python3 -c "import tomllib; tomllib.loads(open('agent-detection/forgecode.toml').read())"
wc -l bin/herdr-forgecode-report install.sh uninstall.sh            # all ≤350 lines
```

## License

MIT
