# SessionLedger — Quick Start

Get the full stack running in five steps.

## Prerequisites

- Rust toolchain (`rustup` recommended, stable >= 1.85)
- [`process-compose`](https://github.com/F1bonacc1/process-compose) installed and on `PATH`
  (`brew install f1bonacc1/tap/process-compose` on macOS)
- Optional task runners (preferred): [`just`](https://github.com/casey/just) and/or
  [`task`](https://taskfile.dev) (`brew install just go-task` / `scoop install just go-task`)

## Steps

### 1. Clone the repository

```sh
git clone https://github.com/KooshaPari/SessionLedger.git
cd SessionLedger
```

### 2. Build the binaries

```sh
just build
# or: task build
# or: make build
```

This compiles `sl-daemon` and `sl-viewer` (debug profile).
Both binaries land in `./target/debug/`.

### 3. (Optional) Set watch/output directories

```sh
export SL_WATCH_DIR=~/.forge/sessions   # directory of *.jsonl session transcripts
export SL_OUT_DIR=~/sl-okf-output       # where compiled OKF documents are written
```

Defaults are `./sessions` and `./okf-out` if these are not set.

### 4. Start the stack

```sh
just dev
# or: task dev
# or: make dev
```

This builds then brings up the local stack (`scripts/runtime-up.*` if present, otherwise
`process-compose up`). You should see three services appear in the process-compose TUI:

| Service        | Role                                                                  |
| -------------- | --------------------------------------------------------------------- |
| `sl-daemon`    | Watches `$SL_WATCH_DIR`, compiles each JSONL session, writes OKF docs |
| `sl-viewer`    | Dioxus desktop window — opens automatically once the daemon starts    |
| `sl-cli-check` | One-shot probe that logs the daemon binary version then exits         |

### 5. Verify

Drop a `.jsonl` session transcript into `$SL_WATCH_DIR`. Within a few seconds
`sl-daemon` emits a `<session-id>.okf.json` file in `$SL_OUT_DIR` and
`sl-viewer` refreshes to show the compiled knowledge-graph document.

## Stopping

```sh
just dev-down
# or: task dev-down
# or: make dev-down
```

Or press `q` in the process-compose TUI.
