# phinbox — Research Document
> **Date:** 2026-07-22 (updated for v0.5.0 — terminal inbox viewer)
> **Owner:** @KooshaPari
> **Status:** SHIPPED (v0.5.0 — 129 / 129 tests green)
> **Crate path:** `phenotype-tooling/crates/phinbox/`
> **Binary name:** `phinbox` (long-form `phinbox-mcp` for the MCP server mode)
> **Tier:** 2 (extension; UX/AX-facing)
> **Maturity target:** stable

---

## 1. Executive summary

`phinbox` is a Rust-native elicitation tool that lets an autonomous agent
(Forge / Codex / Cursor / Claude Code / anything MCP-compatible) pause mid-task,
present the human user with a **native OS popup** containing a form field (the
"agent-devised" prompt) plus an optional notes/free-text box, and synchronously
receive the human's answer back as a typed JSON response.

It ships **four** coordinated surfaces:

| Surface | Path | Format | Purpose |
|---|---|---|---|
| **Rust library** | `src/lib.rs` | Rust crate | Reusable core (schema, dialog, transports) |
| **CLI binary** | `src/main.rs` | clap subcommand | `phinbox ask`, `phinbox schema`, `phinbox serve` |
| **MCP server** | `src/mcp.rs` | stdio JSON-RPC | `phinbox_mcp` tool exposed to forgecode/codex/cursor |
| **Skill + Plugins** | `.phinbox/skills/phinbox/SKILL.md` + `plugins/{forgecode,codex,cursor}/*` | Markdown manifest | Pre-wired tool registration for each host agent |
| **Skill** | `.phinbox/skills/phinbox/` | SKILL.md frontmatter | Agent-readable description of the tool |

The crucial design choice: **the popup is rendered by the OS, not by a
webview**. On macOS the dialog uses `osascript` driving `display dialog`
(native NSAlert under the hood). On Windows it uses PowerShell driving
`Add-Type -AssemblyName System.Windows.Forms` (true Win32 form). Both run
**out-of-process** so the MCP server is never blocked on UI thread, and both
are **modal at the OS layer** (the human cannot ignore them) but **non-blocking
for the agent's other tool calls** thanks to a request-id correlation layer
that multiplexes multiple in-flight elicitation requests.

## 2. Problem statement

Autonomous agents routinely hit decision points where guessing is worse than
asking. Examples that came up repeatedly in fleet telemetry (per
`worklogs/RESEARCH.md` §3):

- "I have two valid approaches — proceed with A or B?"
- "Should I commit with this message or amend?"
- "Enter the secret value the next tool needs"
- "Approve this PR description?"
- "Pick the deployment target (staging|prod|canary)?"

Today the agent either (a) guesses, (b) dumps a wall-of-text question into
the terminal and hopes the human sees it, or (c) requires the human to
hand-type JSON into a chat reply. All three are bad AX. None are blocking
modal UI that **demands** a response.

We need a primitive that:

1. Is **modal** (the human cannot miss it; the agent cannot proceed without
   an answer or explicit cancel).
2. Runs on **native OS chrome** (no electron, no webview) so the popup feels
   like every other system dialog and survives terminal multiplexer state.
3. Has a **typed schema** the agent authors (field label, input type,
   validation, optional notes/free-text box) — not free-form "ask a question
   in plain English and pray the parser interprets it".
4. Works **identically** from Forge, Codex, Cursor, Claude Code, or any
   stdio MCP client — same UX surface regardless of host.
5. Is **non-blocking for concurrent tool calls** so a long-running agent
   session doesn't deadlock when two prompts are queued.
6. Returns a **structured JSON answer** the agent can `match` on
   (`Cancelled` | `Declined` | `Answered { value, notes }`).
7. Defaults to a **TTY fallback** (`inquire` crate) when no GUI is available
   (SSH session, headless CI, Linux without X).

## 3. Why a native popup (vs. TUI / webview / Slack / etc.)

| Approach | Pros | Cons | Verdict |
|---|---|---|---|
| Native NSAlert (macOS) / Win32 Form (Windows) | Modal, OS-styled, always-on-top, accessible, screenshot-friendly, screen-reader-friendly | OS-specific code paths | ✅ **chosen** |
| TUI dialog (`inquire`/`dialoguer`) | Cross-platform, zero deps | Not modal at OS layer; invisible if terminal is backgrounded; no accessibility | ❌ fallback only |
| Electron webview | Cross-platform, full styling | 50MB+ binary, slow startup, NOT modal at OS layer, security surface | ❌ overkill, wrong tool |
| Slack/Discord notification | Async, persists | Not blocking; human may not see; requires bot setup | ❌ wrong primitive |
| HTTP form in browser tab | Familiar UX | Backgrounded, not modal, requires browser; clutters tabs | ❌ |
| AppleScript only (`osascript -e 'display dialog'`) | Tiny, zero deps, modal | macOS only | ✅ on macOS |
| PowerShell `System.Windows.Forms` | Modal, accessible, Win32-native | Windows only | ✅ on Windows |

We use **OS-native APIs via the most-available scripting shell** on each
platform (AppleScript on macOS, PowerShell on Windows, `zenity`/`kdialog` on
Linux). The agent never sees the platform split — the `phinbox` library
detects platform at runtime and picks the right renderer. The agent always
sees the same `ElicitResponse` enum.

## 4. Platform-native popup mechanics

### 4.1 macOS — `osascript` + `display dialog`

AppleScript's `display dialog` command is a thin wrapper over `NSAlert`
(AppKit). Key properties:

- **Modal at the OS layer**: the dialog window owns input focus; the
  spawning process can be backgrounded without losing the dialog.
- **Blocks until user responds**: `osascript` does not return until the user
  clicks a button. This is the blocking property we exploit — the spawned
  subprocess (an `phinbox-popup-mac` shim) writes the user's response to
  stdout and exits with code 0 (accepted) or 1 (cancelled).
- **Supports a default text field** and **optional text** (multi-line
  hidden behind "Show details" disclosure triangle — perfect for the
  "notes" box).
- **Supports `as critical`**: makes the dialog appear on top of all
  windows and play an alert sound.
- **Supports `with title` and `with icon`** for branding.

The Rust side:

```rust
// crates/phinbox/src/platform/macos.rs
use std::process::Command;

pub fn render(prompt: &PromptSpec) -> Result<ElicitResponse> {
    let script = build_applescript(prompt);
    let out = Command::new("osascript")
        .arg("-e").arg(script)
        .output()?;
    parse_applescript_output(&out.stdout, &out.stderr)
}
```

Where `build_applescript` produces something like:

```applescript
set theResponse to display dialog "
    Title: Approve deployment plan?
    Question: The diff touches 14 files. Continue with rollout?

    Field: confirmation_token
    Default: yes
    Secret: false
" with title "phinbox · approval requested" default answer "yes" \
  with icon caution \
  buttons {"Cancel", "OK"} default button "OK" \
  giving up after 600

set theField to text returned of theResponse
set theNotes to (if button returned of theResponse is "OK") then "" else ""
return theField & "|" & theNotes
```

Notes on the macOS design:

- We **escape all string interpolation** through `shell_escape`-style quoting
  to prevent AppleScript injection from the agent's authored prompt.
- The default timeout is **10 minutes** (`giving up after 600`). Agents
  should never wait longer than that — if they do, they get a `TimedOut`
  response. The timeout is configurable via `--timeout-secs`.
- The dialog is spawned in a **separate process tree** via `setsid` so a
  SIGTERM to the MCP server doesn't kill the dialog.

### 4.2 Windows — PowerShell + Win32 Form

PowerShell on Windows can instantiate `System.Windows.Forms.Form` (a
managed wrapper over `USER32.dll`'s `CreateWindowEx`). The popup:

- Is **modal at the Win32 layer** (`Form.ShowDialog()` blocks the calling
  thread; we spawn a PowerShell child process so the MCP server is not
  blocked).
- Has a **textbox** for the field (single-line `TextBox` or multi-line
  `RichTextBox` depending on `notes_required`).
- Supports a **default value**, **placeholder text**, **max length**, and
  **input mask** (`PasswordChar = '*'` for secrets).
- Returns the entered value via `Write-Output` so the Rust parent can
  read it from stdout.
- Honors the **Cancel button** (the form's `DialogResult = DialogResult.Cancel`).

The Rust side:

```rust
// crates/phinbox/src/platform/windows.rs
use std::process::Command;

pub fn render(prompt: &PromptSpec) -> Result<ElicitResponse> {
    let script = build_powershell(prompt);
    let out = Command::new("powershell.exe")
        .arg("-NoProfile")
        .arg("-NonInteractive")
        .arg("-Command").arg(script)
        .output()?;
    parse_powershell_output(&out.stdout, &out.stderr)
}
```

Where `build_powershell` produces a 30-line script that:

1. Loads `System.Windows.Forms` and `System.Drawing` assemblies.
2. Constructs a `Form` with title, icon, and `TopMost = $true`.
3. Adds a `Label` for the question, a `TextBox` for the field (with
   `PasswordChar` if secret), and a `RichTextBox` for notes (if enabled).
4. Adds `OK` / `Cancel` buttons wired to set `$script:dialogResult`.
5. Calls `$form.ShowDialog()` (blocks the PowerShell process).
6. Prints `$dialogResult` + field value + notes to stdout as
   `STATUS|VALUE|NOTES` for easy parsing.

### 4.3 Linux — `zenity` / `kdialog` / TUI fallback

Linux GUI dialogs are non-portable across distros. We use a priority chain:

1. `zenity --entry --text=...` (GNOME; widely packaged)
2. `kdialog --inputbox ...` (KDE)
3. `python3 -c "import tkinter; ..."` (Tk; almost always present)
4. **`inquire` crate TUI** (last resort; what runs in CI/headless)

The TUI fallback is the only renderer we ship a Rust dependency for
(`inquire = "0.7"`). All other platforms shell out to the OS tool.

### 4.4 SSH / headless detection

Before rendering, we check:

- `$DISPLAY` (X11) and `$WAYLAND_DISPLAY` (Wayland) — both unset → headless
- `$SSH_CLIENT` or `$SSH_TTY` set → SSH session (default to TUI unless
  `--allow-gui-over-ssh` is set; some users forward X11 over SSH)
- `cargo test` / `CI=true` env → TUI only
- `--renderer=force-tty` / `--renderer=force-gui` → override

The detection lives in `src/platform/select.rs` and is unit-testable.

## 5. The schema: `PromptSpec`

The agent authors the dialog. The schema is the contract.

```rust
#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema)]
pub struct PromptSpec {
    /// One-line title shown in the popup title bar / window header.
    /// Examples: "Approve deployment?", "Provide API key", "Pick a target"
    /// Max 80 chars.
    pub title: String,

    /// Multi-line body explaining context. Rendered as the question label
    /// above the input field. Markdown is NOT rendered — plain text only
    /// (popup native chrome has no markdown renderer; we deliberately
    /// don't ship a webview). Max 2000 chars.
    pub question: String,

    /// The input field configuration.
    pub field: FieldSpec,

    /// Whether to show the notes/free-text box.
    /// Default: false (single-field dialog).
    #[serde(default)]
    pub notes: Option<NotesSpec>,

    /// Button labels. Default: ["Cancel", "OK"].
    #[serde(default)]
    pub buttons: Option<ButtonSpec>,

    /// Urgency hint — affects icon + sound.
    /// - "info"    : NSAlertStyleInformational / MB_ICONINFORMATION
    /// - "warning" : NSAlertStyleWarning        / MB_ICONWARNING
    /// - "error"   : NSAlertStyleCritical       / MB_ICONERROR
    /// - "secret"  : same as warning + mask input
    #[serde(default = "default_urgency")]
    pub urgency: Urgency,

    /// Timeout in seconds. After this, response is `TimedOut`.
    /// Default: 600 (10 min). Set to 0 for no timeout (CI/automation only).
    #[serde(default = "default_timeout_secs")]
    pub timeout_secs: u32,

    /// Request ID for correlation when multiple prompts are queued.
    /// If omitted, the library auto-generates a UUIDv4.
    #[serde(default)]
    pub request_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum FieldSpec {
    /// Single-line text input.
    Text {
        label: String,
        default: Option<String>,
        placeholder: Option<String>,
        max_length: Option<u32>,
        /// If true, render as password field (••• mask).
        secret: bool,
        /// Regex the value must match before OK is enabled.
        /// Stored as string; compiled at runtime with the `regex` crate.
        pattern: Option<String>,
    },
    /// Long-form multi-line text.
    LongText {
        label: String,
        default: Option<String>,
        max_length: Option<u32>,
    },
    /// Integer in [min, max].
    Integer {
        label: String,
        min: Option<i64>,
        max: Option<i64>,
        default: Option<i64>,
    },
    /// Choice from a fixed list (rendered as radio buttons on GUI,
    /// as a select prompt on TUI).
    Choice {
        label: String,
        options: Vec<ChoiceOption>,
        default_index: Option<usize>,
    },
    /// Boolean yes/no. Renders as 2 buttons.
    Boolean {
        label: String,
        default: Option<bool>,
    },
    /// Date / time picker.
    DateTime {
        label: String,
        default: Option<String>, // RFC3339
        kind: DateTimeKind,      // Date | Time | DateTime
    },
}

#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema)]
pub struct ChoiceOption {
    pub value: String,
    pub label: String,
    #[serde(default)]
    pub description: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema)]
pub struct NotesSpec {
    pub label: String,                  // "Why did you choose this?"
    pub default: Option<String>,
    pub max_length: Option<u32>,
    pub required: bool,                 // blocks OK until notes non-empty
}

#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema)]
pub struct ButtonSpec {
    pub cancel: String,                 // default: "Cancel"
    pub confirm: String,                // default: "OK"
    /// If true, swap which button is the default (Enter-key target).
    #[serde(default)]
    pub default_is_cancel: bool,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, JsonSchema, Default)]
#[serde(rename_all = "lowercase")]
pub enum Urgency { #[default] Info, Warning, Error, Secret }

#[derive(Debug, Clone, Copy, Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "lowercase")]
pub enum DateTimeKind { Date, Time, DateTime }
```

The `ElicitResponse`:

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "status", rename_all = "snake_case")]
pub enum ElicitResponse {
    /// User clicked OK and entered a value.
    Answered { value: FieldValue, notes: Option<String> },
    /// User clicked Cancel. Notes may be populated if they typed some.
    Cancelled { notes: Option<String> },
    /// Popup timed out (--timeout-secs reached with no response).
    TimedOut { elapsed_secs: f64 },
    /// Popup failed to render (e.g., no display, osascript missing).
    /// The agent should fall back to a different strategy.
    Failed { reason: String },
}

#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema)]
#[serde(tag = "kind", content = "value", rename_all = "snake_case")]
pub enum FieldValue {
    Text(String),
    LongText(String),
    Integer(i64),
    Choice { value: String, index: usize },
    Boolean(bool),
    DateTime(String), // RFC3339
}
```

## 6. The four surfaces

### 6.1 Library (`crates/phinbox/src/lib.rs`)

Public API:

```rust
pub fn elicit(spec: &PromptSpec) -> Result<ElicitResponse, ElicitError>;
pub async fn elicit_async(spec: &PromptSpec) -> Result<ElicitResponse, ElicitError>;
pub fn elicit_with(spec: &PromptSpec, opts: &ElicitOptions) -> Result<ElicitResponse, ElicitError>;
pub fn schema_json() -> serde_json::Value;       // returns PromptSpec JSON Schema
pub fn platform() -> Platform;                    // for diagnostics
pub fn detect_renderer() -> RendererKind;         // for --renderer override
```

The library is sync-first (popup UI is fundamentally synchronous from the
caller's POV — the agent is waiting), with an async wrapper that uses
`tokio::task::spawn_blocking` so the async runtime isn't blocked.

`ElicitOptions` lets the caller override defaults:

```rust
pub struct ElicitOptions {
    pub renderer: RendererPreference,  // AutoGui | ForceGui | ForceTty
    pub timeout: Option<Duration>,
    pub working_dir: Option<PathBuf>,  // for resolving icons
    pub parent_pid: Option<u32>,       // for focus stealing
}
```

### 6.2 CLI binary (`phinbox ask ...`)

```
phinbox ask --title "Approve deployment?" \
              --question "The diff touches 14 files..." \
              --field-text label="Are you sure?" default=yes \
              --notes label="Why?" \
              --urgency warning \
              --timeout-secs 60

phinbox schema               # print PromptSpec JSON Schema
phinbox schema --field       # print just FieldSpec schema
phinbox detect               # print detected platform + renderer
phinbox serve                # run MCP server on stdio
phinbox render --from-json '{"title":"..."}'   # for shell scripting
phinbox render --from-file ./prompt.json
phinbox smoke                # render a test popup and exit
phinbox version
```

The CLI is what `phinbox-mcp` (the MCP server binary) shells out to
under the hood. This separation lets the popup renderer be tested
independently and lets shell scripts use the same primitive.

### 6.3 MCP server (`src/mcp.rs`)

Single tool: `phinbox_mcp`.

```json
{
  "name": "phinbox_mcp",
  "description": "Pause and ask the human user a structured question via a native OS popup. ...",
  "inputSchema": { "$ref": "#/schemas/PromptSpec" },
  "outputSchema": { "$ref": "#/schemas/ElicitResponse" }
}
```

Wire format: standard MCP stdio JSON-RPC 2.0. Server uses `rmcp` crate
(v0.2 — the rust-sdk for MCP).

The MCP server is a **single tool by design**: every question the agent
wants to ask goes through `phinbox_mcp`. The agent composes the
`PromptSpec` to express exactly what UI it wants. This keeps the MCP
surface tiny (one tool, one schema) while supporting infinite UX variation
through schema composition.

Concurrent requests: the server maintains a `HashMap<RequestId,
oneshot::Sender<ElicitResponse>>`. When two prompts are queued, both
popups are displayed (the user sees them stacked); each popup's response
is routed back to its corresponding request. The MCP server never blocks
on a single request — `tokio::spawn` per request, `await` on the oneshot.

### 6.4 Skills + Plugins

#### Skill: `.phinbox/skills/phinbox/SKILL.md`

The skill follows the SKILL.md frontmatter convention used by Forge
and Claude Code:

```markdown
---
name: phinbox
description: Pause and ask the human user a structured question via a native OS popup. Use whenever you need user input to disambiguate, confirm, collect a secret, or pick among options.
version: 0.1.0
license: MIT
---

# phinbox

Renders a modal native OS dialog (NSAlert on macOS, Win32 Form on
Windows, zenity/Tk/inquire on Linux) and returns the user's answer as
typed JSON.

## When to invoke

- You face 2+ equally valid next steps and guessing is worse than asking.
- The next tool requires a secret or token you don't have.
- The user must approve a destructive / external action (push, deploy,
  publish, send).
- You need to confirm a generated artifact (commit message, PR body,
  release notes).

## Schema

[Full PromptSpec embedded as YAML, then prose walk-through]

## Response shape

[Full ElicitResponse enum documented]

## Examples

### Ask yes/no

[example]

### Ask for a secret

[example with urgency=secret, field.kind=text secret=true]

### Ask for a multi-choice with required notes

[example with field.kind=choice + notes.required=true]

## Anti-patterns

- Don't ask questions you can answer yourself by reading the codebase.
- Don't ask questions whose answers are deterministic from context.
- Don't ask "shall I proceed?" after a non-destructive read.
```

The skill file is **identical across all three host agents** (Forge,
Codex, Cursor) — they all consume the same SKILL.md format. Host-specific
configuration lives in the `plugins/<host>/` directories.

#### Plugins

```
crates/phinbox/plugins/
├── forgecode/
│   ├── plugin.toml          # Forge plugin manifest
│   ├── install.sh           # one-line installer
│   └── README.md
├── codex/
│   ├── codex.toml           # Codex MCP config snippet
│   ├── install.sh
│   └── README.md
└── cursor/
    ├── cursor-mcp.json      # Cursor MCP config snippet
    ├── install.sh
    └── README.md
```

**Forge** (`plugins/forgecode/plugin.toml`):

```toml
[plugin]
name = "phinbox"
version = "0.1.0"
description = "Native OS popup elicitation tool"
author = "Phenotype Contributors"
license = "MIT"

[skill]
path = "../../.phinbox/skills/phinbox/SKILL.md"
auto_load = true

[[mcp_servers]]
name = "phinbox_mcp"
command = "phinbox-mcp"
args = ["serve"]
transport = "stdio"
```

**Codex** (`plugins/codex/codex.toml`):

```toml
[mcp_servers.phinbox_mcp]
command = "phinbox-mcp"
args = ["serve"]
disabled = false

[skills.phinbox]
path = ".phinbox/skills/phinbox/SKILL.md"
auto_activate = true
```

**Cursor** (`plugins/cursor/cursor-mcp.json`):

```json
{
  "mcpServers": {
    "phinbox_mcp": {
      "command": "phinbox-mcp",
      "args": ["serve"],
      "transport": "stdio"
    }
  }
}
```

The skill activation is handled by Cursor's "Project Rules" feature via
a generated `.cursorrules` snippet:

```
# phinbox
When the user or the agent needs structured input, prefer the
phinbox_mcp tool with a PromptSpec over inline questions.
```

## 7. Why these technologies

| Choice | Rationale | Alternatives considered |
|---|---|---|
| **Rust** | Phenotype scripting policy is Rust-first. Single binary per host. Zero runtime deps on macOS/Windows. | Python (slower startup, harder single-binary); Go (cross-compile pain for Win32 forms) |
| **`rmcp` 0.2** | Official Rust MCP SDK. Schema export built-in. Async-first. | `mcp-rs` (less maintained); hand-rolled JSON-RPC (regression risk) |
| **`clap` 4 derive** | Workspace convention. Used by 26+ existing crates. | `argh` (less discoverable), hand-rolled (regression risk) |
| **`serde` + `schemars`** | Workspace convention. JSON Schema derive is the cheapest path to MCP `inputSchema`. | `serde_json` alone (manual schema), `ts-rs` (no MCP benefit) |
| **`tokio`** | Workspace async runtime. | `async-std` (not used in workspace) |
| **AppleScript via `osascript`** | Already on every macOS install (system component since OS 8). No dep. | `objc`/`cocoa` crate (heavier, requires Xcode SDK linking, AppKit authorship friction) |
| **PowerShell `Add-Type System.Windows.Forms`** | On every Windows 10/11 / Server 2016+. No dep. | `winit`/`winapi` direct (Rust ABI fragility against Win32 patches), C# shim binary (extra build step) |
| **`inquire` for TUI fallback** | Workspace-aligned (used by `release-cut` ad-hoc). Clean terminal fallback. | `dialoguer` (less actively maintained) |
| **`regex` for pattern validation** | Workspace dep. | `fancy-regex` (overkill) |
| **`uuid` for request IDs** | Workspace dep. | `nanoid` (not in workspace) |
| **`chrono` for DateTime** | Workspace dep. | `time` (not in workspace) |
| **`thiserror` for error enums** | Workspace convention. | `anyhow` (less typed at API boundary) |
| **`tracing` for structured logs** | Workspace convention. | `log` (no spans) |

## 8. Concurrency model

The MCP server multiplexes multiple in-flight elicitation requests:

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP server (tokio)                        │
│                                                              │
│   JSON-RPC in  ──►  Router  ──►  HashMap<ReqId, oneshot>    │
│                                  │                           │
│                                  ▼                           │
│                            tokio::spawn                      │
│                                  │                           │
│                                  ▼                           │
│                          render_blocking                     │
│                          (osascript / powershell)            │
│                                  │                           │
│                                  ▼                           │
│                          response ──► oneshot.send()         │
│                                                              │
│   JSON-RPC out ◄── await oneshot                            │
└─────────────────────────────────────────────────────────────┘
```

Key invariants:

- One popup process per request. Two simultaneous requests = two popup
  processes. The OS handles window stacking (NSAlert queues modally on
  macOS; Win32 forms are top-most only by virtue of `TopMost = true`).
- Each popup process is detached (`setsid` on POSIX,
  `CREATE_NEW_PROCESS_GROUP` on Windows) so a SIGTERM to the server
  doesn't kill in-flight popups.
- The server exposes `/metrics` (when `observability` feature is enabled
  via the workspace's `phenotype-tooling-observability` crate) for
  monitoring: `phinbox_in_flight`, `phinbox_total`,
  `phinbox_timeouts_total`, `phinbox_failures_total`.
- All popups emit a structured `tracing` event on close with
  `{request_id, status, elapsed_ms, renderer, platform}`.

## 9. Security & privacy

- **Secrets are masked in the field** when `field.secret = true` (PowerShell
  `PasswordChar`, macOS NSSecureTextField via `display dialog` with the
  `default answer ""` + manual echo suppression).
- **Notes field is NOT masked** even when the field is secret — the
  popup explicitly warns in the body that notes are visible.
- **No popup content is logged at INFO level**. The library uses
  `tracing` with explicit field redaction:
  `tracing::info!(request_id, status, elapsed_ms, "popup closed")` —
  never includes the entered value.
- **The `secret` urgency** auto-applies `field.secret = true` if the agent
  forgets to set it. Defense-in-depth.
- **No telemetry leaves the host**. No HTTP. No analytics. The crate is
  100% local; the binary never makes an outbound network call.
- **Input is shell-escaped** before being interpolated into AppleScript
  or PowerShell to prevent injection from agent-authored prompts.

## 10. Failure modes (and how each is handled)

| Failure | Detection | Response | UX consequence |
|---|---|---|---|
| macOS, no `osascript` | `which osascript` fails | Fallback to TUI | User sees terminal prompt instead of popup |
| Windows, no PowerShell | `which powershell.exe` fails | Fallback to TUI | Same |
| Linux, no `zenity`/`kdialog`/`tkinter` | Probe each | Fallback to `inquire` TUI | Same |
| Headless (no `$DISPLAY`, no `$WAYLAND_DISPLAY`, no SSH X-forward) | Env probe | Force TUI | Same |
| User dismisses with X / Cmd+W / Escape | Button returned = Cancel | `Cancelled` | Agent gets a typed cancel |
| Timeout | `giving up after N` / `Form.Timer` | `TimedOut` | Agent gets typed timeout |
| AppleScript injection attempt in prompt | Shell-escape | `Failed { reason: "invalid prompt" }` | Agent retries with sanitized spec |
| Process spawn fails | `Command::status()` Err | `Failed { reason }` | Agent retries with `--renderer=force-tty` |
| MCP server gets SIGTERM mid-popup | Signal handler | Detach popup from process group; popup persists | Popup survives server restart |
| Two popups simultaneously | Request ID correlation | Both render; each response routed to correct request | User sees both, answers both |
| User types invalid value (fails regex) | Validation hook | OK button disabled until valid | Forced retry |

## 11. Test matrix

```
crates/phinbox/tests/
├── lib.rs                    # integration tests for the library
├── schema.rs                 # JSON Schema round-trip
├── platform_macos.rs         # macOS-specific (cfg-gated)
├── platform_windows.rs       # Windows-specific (cfg-gated)
├── platform_linux.rs         # Linux-specific (cfg-gated)
├── mcp_stdio.rs              # spawn MCP server, send tool call, assert response
├── cli.rs                    # spawn binary, assert exit codes + stdout JSON
└── fixtures/
    ├── simple_text.json      # PromptSpec fixtures for snapshot tests
    ├── choice_with_notes.json
    ├── secret.json
    └── timeout.json
```

`cargo test` runs everything that doesn't require a GUI. GUI tests are
`#[ignore]` by default and run via `cargo test -- --ignored` on CI hosts
with a display attached.

Snapshot tests lock the JSON Schema output — if we accidentally change
the schema, CI fails. This is the contract with every plugin/host.

## 12. FR (functional requirements) sketch

To be tracked in AgilePlus once approved. Sketch:

- **FR-ELIC-001**: Library exposes `elicit(spec) -> Result<ElicitResponse>`.
- **FR-ELIC-002**: CLI exposes `phinbox ask` with `--from-json`,
  `--from-file`, and flag equivalents.
- **FR-ELIC-003**: MCP server exposes exactly one tool, `phinbox_mcp`.
- **FR-ELIC-004**: macOS renderer uses `osascript` `display dialog`.
- **FR-ELIC-005**: Windows renderer uses PowerShell `System.Windows.Forms`.
- **FR-ELIC-006**: Linux renderer prefers `zenity`, then `kdialog`,
  then `tkinter`, then `inquire`.
- **FR-ELIC-007**: Headless / SSH detection forces TUI.
- **FR-ELIC-008**: Concurrent requests are routed by `request_id`.
- **FR-ELIC-009**: Timeout defaults to 600s, configurable.
- **FR-ELIC-010**: Secrets are masked when `field.secret = true` or
  `urgency = "secret"`.
- **FR-ELIC-011**: Prompt content is shell-escaped before
  AppleScript/PowerShell interpolation.
- **FR-ELIC-012**: No outbound network calls.
- **FR-ELIC-013**: Tracing events never include entered values.
- **FR-ELIC-014**: Skill manifest is identical across Forge/Codex/Cursor.
- **FR-ELIC-015**: Plugins install via a single shell command per host.

## 13. Absorbed-tool lineage

Nothing to absorb — `phinbox` is a brand-new primitive. It draws
inspiration from:

- **MCP spec's `elicitation` capability** (2025-06-18 spec revision)
- **`inquire` crate** (terminal UX patterns)
- **`rfd` crate** (Rust File Dialogs — considered but rejected: needs GTK/Qt
  runtime, heavier than `osascript`)
- **`native-dialog`** crate (considered; unmaintained since 2023)
- **Apple's `display dialog` AppleScript command** (the inspiration for the
  macOS path)

## 14. Risks & mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| AppleScript injection from agent-authored prompt | high | Shell-escape layer; rejected prompts return `Failed` |
| Popup hangs forever if OS bug | medium | Default 600s timeout; configurable |
| Modal dialog not visible on multi-monitor / virtual desktops | medium | `--parent-pid` focus-stealing hook |
| MCP server gets SIGTERM mid-popup | medium | `setsid` / `CREATE_NEW_PROCESS_GROUP` |
| Plugin install path varies across host versions | medium | Each plugin ships an OS-aware `install.sh` |
| Cursor `mcpServers` schema changes | low | Pin to known-good version; document upgrade path |
| PowerShell execution policy blocks script | medium | Spawn with `-ExecutionPolicy Bypass -NoProfile` |
| macOS sandbox restrictions on `osascript` (some MDM profiles) | medium | Detect and fall back to TUI with clear error |
| User never sees popup because session is locked | low | Document; recommend `--renderer=force-tty` for headless workflows |
## 15. Linkage:

- Charter: `phenotype-tooling/charter.md` (will be updated; see plan §6)
- SPEC: `phenotype-tooling/SPEC.md` (will be updated; see plan §6)
- Intent: `phenotype-tooling/intent.md` (will be updated; see plan §6)
- SOTA: `phenotype-tooling/SOTA.md` (will add DX dimension entry)
- Workspace: `phenotype-tooling/Cargo.toml` (add `crates/phinbox` member)
- CLI facade: `phenotype-tooling/crates/phenotype-cli/src/lib.rs` (add
  `Phinbox` variant or use the existing delegated pattern)
- Plans: `repos/plans/2026-07-21-phinbox-EXECUTION-PLAN-v1.md`
- Skill: `phenotype-tooling/crates/phinbox/.phinbox/skills/phinbox/SKILL.md`
- Plugins: `phenotype-tooling/crates/phinbox/plugins/{forgecode,codex,cursor}/`

## 16. What ships in v0.1.0 (this work)

1. Rust crate `phinbox` with library, CLI, and MCP-server binaries.
2. macOS renderer (AppleScript).
3. Windows renderer (PowerShell + Win32 forms).
4. Linux renderer (zenity/kdialog/tkinter/inquire chain).
5. JSON Schema export for `PromptSpec` and `ElicitResponse`.
6. SKILL.md.
7. Plugins for Forge, Codex, Cursor.
8. CLI smoke-test.
9. Unit + integration tests (GUI tests `#[ignore]`d by default).
10. `phinbox serve` MCP server (stdio transport).
11. `phenotype-cli` subcommand delegation (`pt phinbox`).
12. README, CHANGELOG, PRD, SPEC, PLAN, ABSORPTION notes.

What does **not** ship in v0.1.0 (deferred to v0.2):

- HTTP transport for the MCP server (stdio only for v0.1).
- Webview fallback (intentional non-goal).
- Slack/Discord notification fallback.
- Persistent popup history.
- Custom icons beyond the built-in 4 (info/warning/error/secret).
- Linux Wayland native protocol (X11/XWayland/`zenity` covers it).

## 17. Async inbox + install (v0.2.0 addendum)

The v0.1.0 design is purely **blocking**: an agent calls `elicit()`, a popup
appears, the user replies, the call returns. That breaks down the moment the
agent runs unattended — the operator may be away from the keyboard, on
another device, or simply not watching the screen. v0.2.0 adds a non-blocking
inbox path so the agent can keep working and the operator can reply at their
own pace.

### 17.1 Design goals

1. **Agent never blocks waiting on the user.** `phinbox ask --async` must
   return in single-digit milliseconds with a `request_id` and an `open_url`.
2. **Single artifact path.** The answer that comes back from the inbox must be
   **byte-for-byte identical** to what the blocking path would have returned.
3. **Cross-device.** The operator must be able to reply from a phone, a tablet,
   or another laptop — not just the host running the agent.
4. **Zero inbound attack surface.** The agent is usually on a corporate
   laptop with a public IP. We must not open a listener that accepts
   unauthenticated input from the internet.
5. **Reuse, don't replace.** v0.1.0's blocking path stays the default.
   `--async` is the opt-in.

### 17.2 The three coordinated surfaces

| Surface | Runs where | Lifetime | Role |
|---|---|---|---|
| `phinbox ask --async` | On the agent's host | One-shot subprocess | Enqueues spec, returns `request_id` + `open_url` |
| `phinbox daemon` | On the agent's host | Long-running background | Serves the HTML form, watches the inbox dir, emits tray notifications |
| `phinbox wait --request-id <id>` | On the agent's host | One-shot subprocess (blocking) | Polls `<inbox>/answered/<id>.json`, returns the response |

The agent's loop is:

```rust
let request_id = elicit_async_deferred(spec)?;  // non-blocking
// ... agent continues doing other work ...
let response = elicit_wait(&request_id, Duration::from_secs(3600))?;  // blocks
match response {
    Answered { values, notes } => proceed(),
    Cancelled => fallback(),
    TimedOut => escalate(),
    _ => error(),
}
```

### 17.3 Why an HTTP listener on loopback

The phone must reach the form. Options considered:

| Option | Verdict | Reason |
|---|---|---|
| Cloud relay (server we host) | Reject | Inbound network exposure; vendor lock-in; outages |
| WebRTC P2P | Reject | NAT traversal complexity; needs signaling server anyway |
| Cloudflare Tunnel | Defer | Good ergonomics but adds dependency for v0.2 |
| **Loopback HTTP + LAN-broadcast deep link** | **Accept** | Zero inbound exposure; phone reaches via QR or LAN IP |
| Email-only (no live form) | Reject | Reply latency 30+ seconds; user has to type JSON by hand |

The chosen design: the daemon binds to `127.0.0.1:7117` (rejects any non-loopback
bind). The `open_url` returned to the agent is `http://127.0.0.1:7117/?id=<id>`
for the host itself, or `http://<lan-ip>:7117/?id=<id>` if `--bind-lan` is set.
For v0.2 we ship loopback only; LAN mode is gated behind `--bind-lan` and a
warning banner.

The iMessage / SMS / email notification carries the deep link. The phone's
browser hits the LAN URL (or the loopback URL via SSH tunnel / Tailscale /
ngrok). The form posts to the daemon's `POST /answer/<id>` endpoint, which
writes the `ElicitResponse` to `<inbox>/answered/<id>.json`. The agent's
`wait` subprocess notices the file and returns.

### 17.4 File-system as the IPC substrate

We deliberately avoid a database. Every state transition is a file move:

```
<inbox_dir>/inbox/<id>.json     # created by `ask --async` (the spec)
<inbox_dir>/answered/<id>.json  # created by the daemon when user replies
```

**Why no DB?** Two reasons: (1) the agent's `wait` subprocess is a tiny
~250 KB static binary that may run in a sandbox with no DB drivers; (2) the
filesystem is inspectable with `cat` and `ls`, which is invaluable when
debugging "why didn't my agent resume?".

Atomicity is achieved with `write-to-temp-then-rename`. The daemon fsync's
the parent directory. The `wait` subprocess polls every 250 ms (configurable
via `--poll-ms`).

### 17.5 The HTML form is the cross-device UX

The form is rendered by `phinbox::views::render_full_html`, a single
self-contained HTML file (~6 KB) with embedded CSS and a tiny vanilla-JS
submit handler. No frameworks, no external assets, no CDN. The form posts
to `/answer/<id>` via `fetch()` and redirects to a `/done` confirmation
page. The page is `<meta name="viewport">`-aware so it lays out correctly on
iOS / Android browsers.

This is the *only* HTML we ever render. We deliberately do not webview-wrap
the agent's host application.

### 17.6 Tray integration — out-of-process, not FFI

We considered linking `objc2` + `cocoa` for `NSStatusItem` and
`windows-sys` for `Shell_NotifyIcon`. Decision: **don't link**. The daemon
spawns `osascript -e 'tell application "System Events" to ...'` on macOS or
`powershell -Command '... BurntToast ...'` on Windows for each notification.
The tray *icon* itself is opt-in via the `--tray` flag, and on macOS it
launches a tiny helper process that uses the dock icon as a proxy (we
avoid `LSUIElement` Info.plist requirements for the dev binary).

This is the same trade-off we made in §6 for the popup itself: **shell out,
don't FFI**. It keeps the daemon pure Rust, cross-compiles cleanly, and
isolates the GUI code so a buggy tray implementation can't crash the
daemon's notification loop.

### 17.7 Why iMessage first (not Slack, not email)

iMessage is the lowest-friction channel for the developer persona: it's
already on their phone, already authenticated, already set to receive
notifications. We deliver via two complementary paths:

1. **Local Messages.app deep link** (zero-config on macOS):
   `messages://open?message-text=<url>` opens a pre-filled new message
   window. The user picks the recipient, hits send.
2. **Twilio SMS bridge** (cross-platform):
   `PHINBOX_SMS_TWILIO_ACCOUNT_SID=...` + `_TOKEN` + `_FROM=+15551234567`
   env vars; daemon POSTs to Twilio's REST API. Outbound only.

Email (SMTP via `lettre`-style config or `sendmail`) is the fallback for
when neither iMessage nor Twilio is configured.

**Inbound: zero.** The user always replies via the form, not by replying
to the SMS / email. This eliminates an entire class of prompt-injection
attacks (no one can trick the agent by sending it a fake "approved" SMS).

### 17.8 Install / uninstall flow

`phinbox install --prefix ~/.local --inbox-dir ~/.phinbox --no-launch-agent`
copies both binaries, generates the launch agent (macOS plist, Linux systemd
unit, Windows Run-key), and runs `phinbox ask --from-file <fixture> --renderer
json` as a smoke test.

`phinbox uninstall --prefix ~/.local --yes` reverses it. Both write a
`phinbox-install.log` to `<prefix>/logs/` so a CI failure can be
triaged.

The install path is **user-local** by design. No `/usr/local/bin`, no sudo.
The launch agent runs as the current user, binds loopback only, and exits
cleanly on SIGTERM.

### 17.9 Trade-offs accepted

- **Polling vs inotify.** v0.2 uses 250 ms polling for the `wait`
  subprocess. Inotify/FSEvents would be cleaner but adds a dependency and
  makes the binary larger. We can revisit when the daemon itself uses
  inotify (planned for v0.3).
- **No end-to-end encryption.** The form is HTTP, not HTTPS, because it's
  loopback. If a future `--bind-lan` flag is enabled, we'll add an
  auto-generated self-signed cert + cert-pin in the QR code. For v0.2 LAN
  is documented as "trusted network only".
- **One popup at a time per inbox dir.** Two parallel `--async` requests
  queue; the operator answers them in order. v0.3 may add per-request tray
  icons.
- **Tray icon is a stub.** The `phinbox daemon --tray` flag registers a
  tray entry that opens the inbox URL on click. The full NSStatusItem
  binding (right-click menu, count badge, animations) is on the M2 roadmap.

### 17.10 Alternatives considered

| Alternative | Why we rejected it |
|---|---|
| Use `tokio::sync::mpsc` + an in-process broker instead of files | Breaks the "agent spawns subprocess" model; harder to inspect |
| Use SQLite for the inbox | Adds a native dep; harder to debug from the shell |
| Use `notify` crate for inotify | Defer to v0.3 — polling is good enough at 4 Hz |
| Use a cloud-hosted message broker | Vendor lock-in + inbound exposure |
| Use webview for the popup (Tauri / wry) | Defeats the whole point — we want OS-native controls |
| Have the daemon stay alive permanently via launchctl | What we ship; documented in ABSORPTION.md |
| Use `tokio::task` for everything instead of subprocesses | Subprocesses are inspectable + killable from outside |

---

## 18. v0.3.0 addendum — non-blocking operator inbox (2026-07-22)

### 18.1 Motivation

The v0.2.0 inbox was technically async (write a spec to a file, return a request
ID), but it was **only** useful when the agent had a human in the seat and the
human was actively watching the inbox page. For a long-running fleet of agents
where the operator is on a phone, on a laptop with Notifications silenced, or
simply AFK, v0.2 left too much friction:

1. The agent had to fire-and-forget, then the operator had to **remember**
   to open the inbox tab and **manually keep it open** in the browser.
2. There was no surface notification — no badge, no icon, no message.
3. The only delivery channel was the local HTTP page. No iMessage. No email.
4. The bin had no first-class install step; running it required `cargo
   install` or hand-copying the binary.

The v0.3.0 work adds the **non-blocking inbox UX** the user requested:
agents can `ask --async` and continue; the operator gets a tray icon, an
iMessage-style notification, and a one-click deep link to a native form.

### 18.2 What v0.3 adds

| Capability | Module / binary | Why |
|---|---|---|
| Local HTTP server (`127.0.0.1:7117`, loopback only by default) | `inbox::daemon` | Serves the form from anywhere on the host; bound loopback to avoid LAN risk |
| `/healthz`, `/form/:id`, `/answer/:id`, `/list` routes | `inbox::daemon::router` | REST-ish interface; identical protocol used by both the tray click handler and the iMessage bridge |
| macOS tray (`NSStatusItem`) stub | `inbox::tray` (`#[cfg(target_os = "macos")]`) | Click → open `/form/<id>` in default browser; badge shows pending count |
| Windows tray (`Shell_NotifyIcon`) stub | `inbox::tray` (`#[cfg(target_os = "windows")]`) | Same UX as macOS tray |
| iMessage / SMS / email fanout | `inbox::notify` | Multi-channel delivery, off by default |
| `phinbox install [--prefix DIR]` | `installer::install` | One-shot setup: copy binary, emit PATH export, register LaunchAgent / schtasks |
| `phinbox uninstall [--yes]` | `installer::uninstall` | Reverses the install atomically |
| `phinbox daemon [--port N] [--bind ADDR]` | new subcommand | Background the inbox server (used by the launch agent) |
| `phinbox ask --async` | `bin_phinbox` | Non-blocking enqueue; prints `{status:"deferred", request_id:"…", open_url:"http://127.0.0.1:7117/form/…"}` |
| `phinbox wait --request-id ID [--timeout S]` | `bin_phinbox` | Block (with timeout) until the answered file appears |
| `phinbox answer --request-id ID [--values …]` | `bin_phinbox` | Scripted reply (CLI form) |
| `phinbox inbox {--list,--show ID,--purge}` | `bin_phinbox` | Inspect / clean the inbox directory |

### 18.3 iMessage / email / SMS delivery — security model

The user's request was *"open imessage/emails like view that lets me open the forms and answer/deal with"* — i.e., the inbox must look and feel like an inbox
that can be **answered from the phone**. We honor that surface, but we apply a
**zero-inbound** rule on the agent side:

- **Outbound only.** The daemon **never** opens an SMS / iMessage / email
  *inbound* surface. There is no SMTP server, no IMAP connection, no Twilio
  inbound webhook, no Messages.app automation that replies to a chat.
- **Deep link, not auto-reply.** The user must *choose* to open the form
  by clicking the iMessage link. The popup or click action targets the
  local HTTP form, never the original message thread.
- **No prompt injection via channel.** Because the response file is created
  by the local browser (or by a `phinbox answer` CLI call), and never by
  the iMessage / email recipient, a malicious message cannot smuggle an
  "approved" payload to the agent by spoofing a sender. The protocol end
  point is local-only.

The implementation:

```rust
// src/inbox/notify.rs (sketch)
pub enum NotifyChannel { IMessage, Sms { via: SmsProvider }, Email { via: EmailProvider } }

pub struct NotifyChannels {
    pub imessage: bool,   // PHINBOX_NOTIFY_IMESSAGE=1
    pub sms: Option<SmsProvider>,
    pub email: Option<EmailProvider>,
}

pub async fn fanout(request: &PendingRequest, ch: &NotifyChannels) -> Vec<NotifyAttempt> {
    // Each channel is best-effort; failures are logged, not propagated.
}
```

The iMessage path on macOS shells out to `open "messages://open?message-text=<url>"`
which opens a pre-filled new message window in Messages.app; the user picks
the recipient and hits send. No automation of the actual send (Apple does
not permit it without private entitlements).

### 18.4 Tray integration — decision: stub now, native later

We considered two routes for the tray icon:

1. **Full FFI** — link `objc2` + `cocoa` for `NSStatusItem`, link
   `windows-sys` for `Shell_NotifyIcon`. Pros: real icon, badge, menu,
   right-click actions. Cons: adds two heavy native deps; cross-compile
   pain; breaks the "pure Rust crate" guarantee.
2. **Shell-out stub** — register a *placeholder* system event via
   `osascript` on macOS, or PowerShell `BurntToast`-style on Windows, and
   open the inbox URL in the default browser. Pros: zero native deps,
   cross-compiles cleanly. Cons: no permanent tray icon; only fires per
   notification.

For v0.3 we ship **(2)** for the default build and gate **(1)** behind a
`tray-native` cargo feature so a follow-up PR can land the real binding
without rewriting the daemon.

### 18.5 Install / uninstall idempotency

`phinbox install` is **idempotent**:

- Detects an existing install at the same prefix and either overwrites
  (with `--yes`) or refuses (without).
- Writes an `phinbox-install.log` to `<prefix>/logs/` so CI failures are
  inspectable.
- The `--no-launch-agent` flag skips LaunchAgent / schtasks registration
  (for sandboxed environments and CI).
- The `--skip-path` flag skips `PATH=` shimming (for when the user already
  has the prefix on PATH).

`phinbox uninstall` is the reverse:

- Removes every file the install wrote (binary, logs, schtasks plist, …).
- Removes the PATH-export line it added (matched by checksum).
- Refuses to run without `--yes` if the directory looks like a system path
  (contains `bin` or `sbin` and is not user-owned).

### 18.6 CLI decision — why `clap` `derive` + subcommands

v0.2 shipped with hand-rolled arg parsing (30 lines of `if let Some(...)`).
v0.3 adds nine subcommands; that's the inflection point where hand-rolling
becomes a footgun. We migrated to `clap = { version = "4", features =
["derive", "env"] }` and pinned `clap_derive` so the macro generation is
reproducible. The `env` feature lets us pick up `PHINBOX_INBOX_DIR` and
`PHINBOX_PORT` so a daemon started by the launch agent doesn't need
explicit flags.

### 18.7 Verification matrix

| Scenario | Expected | Verified by |
|---|---|---|
| `phinbox ask --async` writes file, prints request ID | Envelope JSON, exit 0 | `tests/cli.rs::ask_async_enqueue` |
| `phinbox inbox --list` returns JSON summary | `[{request_id, title, …}]` | `tests/cli.rs::inbox_list_*` |
| Daemon `GET /healthz` returns 200 | Plaintext `ok` | `tests/inbox_daemon.rs::healthz_returns_ok` |
| Daemon `GET /form/<id>` returns HTML | `view-source:`-renderable | `tests/inbox_daemon.rs::form_renders_for_pending` |
| iMessage channel off by default | No outbound when env unset | `tests/inbox_notify.rs::default_no_outbound` |
| `phinbox install --dry-run` does not write | Diff-only mode | `tests/installer.rs::install_dry_run` |

### 18.8 Open follow-ups (M2)

1. **Real native tray bindings** (`tray-native` feature).
   → **Addressed in v0.4.0 — see §19.**
2. **`WinToast` / `BurntToast` shim** for Windows without PowerShell modules.
3. **iOS push relay** so the iMessage URL surfaces as a true
   tap-to-open notification instead of a deep link.
4. **HTTPS auto-cert** for `--bind-lan` (mentioned in §17.9 Q1 follow-up).
5. **In-process inotify** to drop the 4 Hz polling.

---

## 19. v0.4.0 addendum — persistent tray icon (`tray-native` feature)

> **Date:** 2026-07-22
> **Status:** SHIPPED (115 / 115 tests green in both default-features and `tray-native` builds)

### 19.1 Why this came before the remaining popup FFI work

The v0.3 plan deferred "real native tray bindings" to M2. v0.4 makes that the
**M2 deliverable** — and bumps the original "wire the FFI popups" work to M3.

The reasoning is empirical:

1. We already ship native *popups* (Cocoa `NSAlert` via `osascript`,
   Win32 `MessageBox` via PowerShell `Add-Type`). They're good enough for
   the blocking case.
2. What we **don't** ship is a persistent operator-facing presence. A daemon
   that lives in the background has no way to show "I have 3 prompts waiting"
   without the user opening a browser.
3. The FFI popup work is a much larger lift (Cocoa runloop, Win32 message
   pump, GTK4) and risks destabilizing v0.3's working shell-out path.
4. The tray is a smaller surface (~600 LOC) and unblocks the operator UX.

### 19.2 Options considered

| Option                              | LOC  | New runtime deps | Cross-platform | Verdict |
| ----------------------------------- | ---- | ---------------- | -------------- | ------- |
| Hand-roll per-OS FFI                | ~1500 | none           | ❌ mac only first | Rejected |
| `tauri::tray` icon module           | ~100  | `wry`, `tao`    | ✅ (full stack) | Rejected (too heavy) |
| `tray-icon 0.24`                    | ~600  | `objc2-app-kit` (mac), `windows-sys` (win), `libappindicator` (linux) | ✅ | **Adopted** |
| `ksni` (Linux-only)                 | ~300  | none            | ❌ Linux only   | Rejected |
| `notify-rust` + `appindicator-rs`   | ~500  | two crates      | partial        | Rejected (overlap) |

### 19.3 The `!Sync` problem

`tray-icon 0.24`'s `TrayIcon` holds an `NSStatusItem` on macOS, which is
backed by an Objective-C `id` that is `!Send + !Sync`. The whole
cross-platform abstraction inherits that.

We need `Arc<dyn Tray>` to be `Send` (so the daemon's HTTP task can hold a
handle and the notifier task can mutate it). We do **not** need `Sync`
(no one is reading the tray concurrently from multiple threads at once).

Solution: **owning-thread + channel bridge**.

```
   notifier task ───Arc<dyn Tray>: Send────┐
                                            ▼
                                  ┌──────────────────────────┐
                                  │ tray thread (owns        │
                                  │   TrayIcon for life)     │
                                  └──────────┬───────────────┘
                                             │ crossbeam_channel
                                             ▼
                                  poll_menu_action(timeout)
```

The `Tray` trait is therefore `Send`-only (`pub trait Tray: Send`).
The producer side holds an `Arc<dyn Tray>` and calls `update_badge` /
`update_tooltip` / `shutdown`. Those methods forward via channel to the
tray thread, which mutates the real `TrayIcon`. The consumer side does
`poll_menu_action(timeout)` which does a non-blocking `try_recv` on the
incoming menu-event channel that the tray thread also feeds.

This is the same pattern `notify-rust`, `tokio::process`, and `wry` use
for owning OS handles — it's not novel, but the `tray-icon` crate
deliberately doesn't expose one, so we provide it here.

### 19.4 Feature flag and compile-time impact

`tray-native` is **off by default** for two reasons:

1. `objc2-app-kit` adds ~30s of cold compile time. CI runners without
   `sccache` would slow down noticeably.
2. Linux's `libappindicator` feature links against a shared library
   that's not always installed in CI containers.

So `cargo build -p phinbox` stays portable and ships a `NoopTray`
everywhere. `cargo build -p phinbox --features tray-native` produces
the real macOS / Windows / Linux tray icon.

Both configurations pass all 115 tests — the `tray::tests` exercise
`NoopTray` and the public `build_tray` factory.

### 19.5 Menu actions and the quiet state

| Menu item           | Action                                               | State changed |
| ------------------- | ---------------------------------------------------- | ------------- |
| Open inbox          | Open the inbox index URL in the default browser     | none          |
| Open latest         | Open the most-recent pending request's URL          | none          |
| Toggle quiet        | Flip `Arc<AtomicBool> quiet`                        | yes           |
| Quit                | Trigger daemon graceful shutdown (call `shutdown()`) | yes           |

When `quiet` is on, the notifier loop suppresses both tray toasts and
notify-channel fanout. The badge still updates so the operator can see
the queue depth. The "Quit" menu item is the recommended way to stop the
daemon — it calls `DaemonConfig::shutdown_handle().signal()` and the
HTTP server returns from `serve()` cleanly.

### 19.6 Verification

| Command                                                              | Result |
| -------------------------------------------------------------------- | ------ |
| `cargo build -p phinbox`                                            | clean, 0 warnings |
| `cargo build -p phinbox --features tray-native`                    | clean, 0 warnings |
| `cargo test -p phinbox --no-fail-fast`                              | 115 / 115 |
| `cargo test -p phinbox --features tray-native --no-fail-fast`       | 115 / 115 |
| Manual: `phinbox daemon --port 0 --inbox-dir /tmp/x` on macOS      | menu-bar item appears, badge updates |

### 19.7 What remains for v0.5+

The next batch of work moves off the v0.4 list:

- Re-bridge `set_title` for macOS so the menu-bar text updates
  live (currently requires a `!Sync` workaround that's deferred).
- `notify-rust` cross-platform fallback for Linux tray events.
- Tray icon theme: real PNG instead of the default `tray-icon`
  placeholder.
- Auto-launch the daemon on login on macOS via
  `~/Library/LaunchAgents/com.phenotype.phinbox.plist`.

---

## 20. v0.5.0 addendum — terminal inbox viewer (`ratatui`-based TUI)

### 20.1 Motivation

After v0.4 the daemon has a tray icon, the inbox is durable on disk,
and `ask --async` works without a TTY. The remaining gap: how does a
user actually *see and answer* pending requests when they are
*already at a terminal*? Right now they would have to open the browser
to the daemon URL, or pipe `inbox --list` and then `answer` per
request. Both are friction. The TUI is the local-terminal counterpart
to the tray icon: when you're at the keyboard, you want to see the
list, pick one, and answer it from one place.

### 20.2 Why `ratatui` (and not `curses`, `termion`, `tui-rs`)

We surveyed four candidates:

| Crate              | Status      | Verdict                                                                  |
| ------------------ | ----------- | ------------------------------------------------------------------------ |
| `ratatui` 0.30     | active      | **Adopt.** Community successor to `tui-rs`; `crossterm` 0.29 backend; clean `ratatui::run()` closure API. |
| `crossterm` 0.29   | active      | **Adopt** as backend. Same team as ratatui; consistent version pinning. |
| `tui-rs` 0.19      | archived     | Reject. Last release 2021; no `no_std` story.                            |
| `cursive` 0.16     | low-maint   | Reject. Different paradigm (immediate-mode alt-screen) — fine for dialogs but heavy for split-pane inbox. |
| Direct CSI escapes | n/a         | Reject. 200 LOC of key handling alone. No value over ratatui.            |

The cost is ~700 KB of compiled deps; we accept it because every
`phinbox` install gets a TUI as the canonical local UX, and the
workspace already pulls in similar-sized deps for the tray (`objc2`
+ `tray-icon` on macOS, `windows-sys` on Windows). We do **not** gate
the TUI behind a feature flag because the user's instinct on a fresh
install is `phinbox inbox --tui`, not "rebuild with `--features
tui`."

### 20.3 Architecture

```
┌────────────────────────────────────────────────────────────┐
│ ratatui::run(|terminal| { ... })                           │
│   ├─ loop:                                                │
│   │   1. terminal.draw(|frame| render_panes(frame, state)) │
│   │   2. event::poll(Duration::from_millis(poll_ms))       │
│   │   3. dispatch key → KeyAction                          │
│   │   4. apply action (move, focus, refresh, quit, ...)    │
│   │   5. if poll_ms elapsed: snapshot_inbox(inbox_root)    │
│   └─ ratatui::restore() on drop / error                    │
└────────────────────────────────────────────────────────────┘
```

The TUI is **stateful** (`ViewerState`) but reads **statelessly** from
disk via `snapshot_inbox(root)` — there is no in-memory cache that
could go stale. The poll interval defaults to 1 s and is configurable
via `--poll-ms`.

The TUI does **not** spawn the daemon. It is a thin client over the
shared `<inbox>/inbox/*.json` directory. If a daemon is running, the
TUI sees its writes. If no daemon is running, the TUI still works for
ad-hoc review and answer.

### 20.4 Graceful fallback (the contract)

When `TERM=dumb`, when stdin is not a TTY, or when
`ratatui::init()` fails (no `DISPLAY` on Linux + missing `WAYLAND_DISPLAY`
+ `tray-icon`'s GTK backend also failing), the TUI must:

1. **not** enter raw mode,
2. **not** seize the terminal,
3. **emit** the same plain-text output as `--list`,
4. **exit 0**.

This is verified by the manual test in §20.7. The fallback is the
contract because CI / detached sessions / `ssh` without TTY
allocation must not need extra flags.

### 20.5 Keybinding design

Defaults follow vim conventions for navigation (j/k, g/G) because they
are keyboard-only friendly and don't fight the user's muscle memory:

| Key            | Action                          | Rationale                                          |
|----------------|---------------------------------|----------------------------------------------------|
| `j` / `↓`      | move selection down             | vim + arrow convention; works on any keyboard      |
| `k` / `↑`      | move selection up               | same                                                |
| `g` / `G`      | jump first / last               | vim convention for top/bottom                       |
| `Tab`          | switch focus list ↔ detail      | standard tab navigation                              |
| `Enter` / `o`  | open form in browser            | "open" — matches file-managers                      |
| `r` / `F5`     | force refresh                   | `r` for "refresh"; F5 is browser-style              |
| `d`            | dismiss                         | `d` for "delete" / "dismiss"                        |
| `?`            | toggle help                     | standard                                            |
| `q` / `Esc`    | quit                            | vim convention + universal Esc                       |

All keybindings are rebindable via `PHINBOX_TUI_KEYMAP_<KEY>=<action>`
env vars. We deliberately do not ship a config file in v0.5 — env vars
are enough for a 9-action keymap and avoid the YAML/TOML config-debate.

### 20.6 Verification matrix (v0.5)

| Gate                                                              | Result                       |
|-------------------------------------------------------------------|------------------------------|
| `cargo build -p phinbox`                                        | clean, 0 warnings            |
| `cargo build -p phinbox --features tray-native`                 | clean, 0 warnings            |
| `cargo test -p phinbox --no-fail-fast`                          | **129 / 129**                |
| 14 new TUI unit tests (sort, age labels, key handling, render)    | all pass                     |
| Live: `phinbox inbox --tui --inbox-dir <dir>` on real TTY       | split pane renders, `q` quits |
| Live: `TERM=dumb phinbox inbox --tui --inbox-dir <dir>`         | exits 0, plain-text output   |

### 20.7 What remains for v0.6+

- Mouse support (click to select, double-click to open).
- Config-file for keybindings (`config.toml` next to the inbox).
- Inline answer editor in the detail pane (right now detail pane
  shows the spec but you still have to `Enter` to answer in browser).
- Multi-select actions (`x` to mark + `X` to bulk-answer).
- TUI mode for the `answer` subcommand (readline-style multi-line
  text editor with secret-masking).