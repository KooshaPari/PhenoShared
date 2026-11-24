# phinbox — Product Requirements Document

## Authors

- Owner: `phenotype-tooling/phinbox`
- Status: Draft → ready-for-implementation
- Target version: 0.3.0 (0.1.0 was blocking popup, 0.2.0 added async inbox + install)
- Reviewers: `agent-orchestrator`, `phenotype-cli`, `release-cut`

## Why now

Across the Phenotype ecosystem (Forgecode, Codex, Cursor), every agent that wants a missing decision
today must reach for the chat pane. This breaks the agent's flow and forces the operator to switch
contexts. A native, modal, single-decision prompt — fired from the agent's tool loop — solves it.
The required building blocks already exist in `phenotype-tooling` (rmcp scaffolding, dispatch router,
skill manifest conventions). What's missing is the renderer core and the cross-client plugin glue.

## Product definition

`phinbox` is a Rust crate that ships:

- A library (`phinbox::elicit`) callable from any host agent that imports it.
- A CLI (`phinbox`) usable as a subprocess from any language.
- An MCP server (`phinbox-mcp`) consumable by every MCP-aware client.
- Three first-party plugins (Forgecode, Codex, Cursor) and one universal skill manifest.

It opens a **native popup window** on macOS and Windows. On Linux it opens a GTK4 dialog or, if no
display is available, a TUI prompt. On headless systems it goes straight to TUI. All four rendering
paths consume the same JSON spec and emit the same JSON response.

## User stories

1. **As a Forgecode agent**, I need the operator to confirm before I rename 23 identifiers across 8
   files, so I can `phinbox` a boolean and proceed without chat interruption.

2. **As a Codex agent**, I need an Anthropic API key the operator hasn't set yet, so I can
   `phinbox` a `secret: true` text field, capture the masked input, and continue.

3. **As a Cursor agent**, I need the operator to pick a deployment target (Staging / Canary / Prod),
   so I `elicit` a `choice` and dispatch the deploy.

4. **As an operator**, I want every prompt to feel like a system dialog — small, modal, dismissed
   with the same shortcuts I'm used to — so the agent never feels like a webpage.

5. **As a long-running agent**, I must keep working even when the operator is away from the keyboard.
   I queue my decision request in the inbox, return the open URL to the operator, and `wait` for
   the answer. The operator opens the URL on their phone (via iMessage / email deep link), fills
   in the form, and the agent resumes.

6. **As an operator on a phone**, I want to be notified about pending agent decisions and reply
   without opening a desktop. The system sends me an iMessage / SMS with a link; I tap it; the
   browser opens the form; I submit. The agent's `wait` call returns the answer.

7. **As a CI system**, I want the inbox daemon and binaries available on every runner without a
   manual install. `phinbox install --prefix <path> --no-launch-agent --skip-path` runs as a
   post-install hook and `phinbox uninstall --yes` reverses it.

## Functional requirements

| ID    | Requirement                                                                                            |
| ----- | ------------------------------------------------------------------------------------------------------ |
| F-01  | The library accepts a `PromptSpec` JSON and returns an `ElicitResponse`.                               |
| F-02  | The CLI accepts the same spec via flags or stdin and emits the same response on stdout.                |
| F-03  | The MCP server exposes a single tool `phinbox_mcp` with the spec as input schema.                    |
| F-04  | The macOS renderer uses AppKit (`NSPanel` / `NSWindow` + standard `NSControls`) and is modal to the active app. |
| F-05  | The Windows renderer uses Win32 (`CreateWindowExW` + standard controls) and is modal to the owner window. |
| F-06  | The Linux renderer uses GTK4 (`rfd`) when a display is available, otherwise TUI.                       |
| F-07  | A TUI fallback exists using `inquire`, always accepting the same input shape and emitting the same JSON. |
| F-08  | All renderers honor `timeout_secs`. On timeout, the prompt is dismissed and the response is `timed_out`. |
| F-09  | Secret fields are masked in the GUI and never logged.                                                   |
| F-10  | The schema is published as JSON Schema (`phinbox schema` and `phinbox::schema_json()`).            |
| F-11  | Plugins for Forgecode, Codex, and Cursor install the binary and register the MCP server / skill.       |
| F-12  | A universal skill manifest lives at `.phinbox/skills/phinbox/SKILL.md` and is consumable by all clients. |
| F-13  | **Async inbox.** `phinbox ask --async` returns immediately with `{status: "deferred", request_id, open_url}`. The spec is persisted to `<inbox_dir>/inbox/<id>.json`. |
| F-14  | `phinbox wait --request-id <id> [--timeout <sec>]` blocks until the operator's reply is persisted at `<inbox_dir>/answered/<id>.json`. |
| F-15  | **Inbox daemon.** `phinbox daemon` runs an HTTP server on `127.0.0.1:7117` (loopback only). `GET /?id=<request_id>` renders the form as HTML; `POST /answer/<id>` accepts the reply. |
| F-16  | **Tray.** On macOS and Windows the daemon registers a tray icon whose menu shows the pending count and links to the inbox. |
| F-17  | **iMessage / SMS / email notify.** When configured (env vars: `PHINBOX_IMESSAGE_TO`, `PHINBOX_SMS_TWILIO_*`, `PHINBOX_SMTP_*`) the daemon sends a one-way outbound message with the deep link on every new pending request. |
| F-18  | **Install / uninstall.** `phinbox install` copies both binaries, optionally registers a launch agent / systemd user unit / Run-key, and runs a smoke test. `phinbox uninstall` reverses it. Both support `--prefix`, `--inbox-dir`, `--dry-run`. |
| F-19  | **Answer directory.** Answered responses land in `<inbox_dir>/answered/<id>.json` with the full `ElicitResponse` (so the agent's `wait` returns identical JSON to the blocking path). |

## Non-functional requirements

| ID    | Requirement                                                                                            |
| ----- | ------------------------------------------------------------------------------------------------------ |
| N-01  | First-paint latency: ≤ 500 ms on warm start (binary already launched once).                            |
| N-02  | Cold start: ≤ 1.5 s on M-series Mac, ≤ 2.0 s on Windows 11.                                            |
| N-03  | Binary size: ≤ 25 MB stripped (the Windows release; macOS is smaller).                                 |
| N-04  | Zero outbound network dependencies.                                                                    |
| N-05  | All public types implement `Serialize + Deserialize` and roundtrip through `serde_json`.                |
| N-06  | No panics on user input. Invalid spec → `ElicitError::InvalidSpec(String)`.                            |
| N-07  | Cross-platform test suite runs on `cargo test -p phinbox` without a display server.                  |

## Risks

| Risk                                                                                  | Mitigation                                                  |
| ------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| AppKit requires main thread; mixing with `tokio` runtime is brittle.                  | Run the GUI on a dedicated blocking thread; tokio runtime stays clean. |
| `windows-sys` is large and slow to compile.                                            | Gate behind a feature flag (`gui-windows`); TUI-only build is fast. |
| Operators on locked-down macOS may not have Accessibility / Automation entitlements. | The macOS renderer is a passive prompt — no entitlements required (modal sheet attached to the active app via `setSheetParent`). |
| Cursor's MCP transport changes between versions.                                      | Plugin's `install.sh` detects Cursor version and writes the right key (`mcp` for v0.40+, `mcpServers` for older). |
| An agent can spin up unbounded popups.                                                | The MCP server enforces `max_concurrent_prompts = 1`. A second call blocks until the first resolves or times out. |

## Out of scope (v0.1 / v0.2)

- Multi-page wizards.
- Drag-and-drop file pickers (we provide `FieldSpec::Path` but no DnD UI yet).
- Localized button labels (UI strings are English-only; i18n is a follow-up).
- Server-rendered prompts (HTTP transport) — stdio only for v0.1.
- Inbound message parsing (iMessage / SMS replies must come back via the browser form or CLI;
  no inbound webhook).
- Bidirectional push notifications (we deliver the link; the user opens it on whatever device they
  prefer).

## Success metrics

- A reviewer can `phinbox install --prefix ~/.local --skip-path` and have a working `phinbox`
  and `phinbox-mcp` in under five minutes.
- Forgecode + Codex + Cursor all list `phinbox_mcp` after running their respective `install.sh`.
- CI passes: `cargo test -p phinbox` (108 / 108 green) and `phinbox-mcp` round-trips a
  `tools/list` request.
- A long-running Forgecode agent can `phinbox ask --async --request-id …` and the daemon's tray
  icon shows the pending count; clicking it opens the form in the default browser; the agent's
  `wait` call returns within 200 ms of the operator clicking Submit.
- The macOS renderer ships a notarizable `.app` bundle (handled in a separate `release-cut` plan).
