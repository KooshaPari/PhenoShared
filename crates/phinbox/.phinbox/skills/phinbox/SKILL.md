---
name: phinbox
description: Pause the agent and ask the human user a structured question via a native OS popup. Use whenever the agent needs user input to disambiguate, confirm, collect a secret, or pick among options. Returns typed JSON (answered | cancelled | timed_out | failed).
version: 0.1.0
license: MIT
author: Phenotype Contributors
homepage: https://github.com/KooshaPari/phenotype-tooling/tree/main/crates/phinbox
---

# phinbox

Renders a **modal native OS dialog** (NSAlert on macOS, Win32 Form on
Windows, `zenity`/`kdialog`/Tk/`inquire` on Linux) and returns the user's
answer as typed JSON. The popup is **modal at the OS layer** — the user
cannot miss it and the agent cannot proceed without an answer or explicit
cancel.

## When to invoke

Use `phinbox_mcp` whenever:

- You face **two or more equally valid next steps** and guessing is worse than asking.
- The next tool requires a **secret or token** you don't have (API key, password, webhook URL).
- The user must **approve a destructive or external action** (push, deploy, publish, send, delete).
- You need to **confirm a generated artifact** (commit message, PR body, release notes, response email).
- You need to **collect a numeric value** (port number, retry count, threshold) without trial-and-error.

Do **not** use it for:

- Questions whose answers are **deterministic from the codebase** (read the file instead).
- Cosmetic choices (default to your judgment; offer to revise later).
- Multi-step workflows (break into multiple `phinbox_mcp` calls, one decision at a time).
- Anything that doesn't require **blocking on the user** — if a default is acceptable, proceed.

## The PromptSpec schema

The agent composes a `PromptSpec` to express exactly the UI it wants. Six
field kinds, plus an optional notes box:

```yaml
title: "Approve deployment?"         # required, ≤80 chars
question: |                           # required, ≤2000 chars, plain text
  The diff touches 14 files in the payments service.
  Continue with the rollout to staging?
field:
  kind: boolean                      # one of: text, long_text, integer, choice, boolean, datetime
  label: "Proceed?"
  default: true                      # optional
notes:                               # optional free-text box below the field
  label: "Why? (optional)"
  required: false
urgency: warning                     # one of: info, warning, error, secret
timeout_secs: 60                     # default: 600
request_id: "deploy-approval-1"      # optional; auto-UUID if omitted
```

### Field kinds

| Kind | GUI rendering | Extra fields |
|---|---|---|
| `text` | Single-line text box (or password if `secret: true`) | `default`, `placeholder`, `max_length`, `secret`, `pattern` |
| `long_text` | Multi-line text area | `default`, `max_length` |
| `integer` | Number stepper | `min`, `max`, `default` |
| `choice` | Radio buttons | `options: [{value, label, description?}]`, `default_index` |
| `boolean` | 2 buttons (OK / Cancel or custom) | `default` |
| `datetime` | Date/time picker | `default` (RFC3339), `kind: date \| time \| datetime` |

### Urgency hints

| Value | Icon | Sound | Use case |
|---|---|---|---|
| `info` | blue | none | Routine questions |
| `warning` | yellow | system | Confirmation before external side-effect |
| `error` | red | alert | Catastrophic actions (delete, force-push) |
| `secret` | yellow + masked input | system | Collecting API keys, tokens, passwords |

## The ElicitResponse schema

The popup returns one of:

```yaml
status: answered
value:                              # FieldValue — matches the field kind
  kind: boolean
  value: true
notes: "low risk"                   # optional
```

```yaml
status: cancelled
notes: null                         # user clicked Cancel; may have typed notes
```

```yaml
status: timed_out
elapsed_secs: 600.0
```

```yaml
status: failed
reason: "no display attached"
```

The agent should **pattern-match** on `status`:

```python
match response["status"]:
    case "answered":
        use(response["value"])
    case "cancelled":
        # graceful fallback — proceed with default or halt
    case "timed_out":
        # retry with longer timeout, or surface to the user
    case "failed":
        # fall back to inline question, or set --renderer=force-tty
```

## Examples

### Example 1 — simple yes/no

```json
{
  "title": "Continue with refactor?",
  "question": "I'll rename 23 identifiers across 8 files. Proceed?",
  "field": { "kind": "boolean", "label": "Proceed?", "default": true },
  "urgency": "info",
  "timeout_secs": 120
}
```

### Example 2 — collect a secret

```json
{
  "title": "Anthropic API key needed",
  "question": "The next request needs an Anthropic API key. Paste it below — input is masked.",
  "field": {
    "kind": "text",
    "label": "sk-ant-...",
    "secret": true,
    "pattern": "^sk-ant-[A-Za-z0-9_-]{20,}$"
  },
  "urgency": "secret",
  "timeout_secs": 300
}
```

### Example 3 — multi-choice with required notes

```json
{
  "title": "Pick a deployment target",
  "question": "Which environment should we deploy to? You must explain your choice.",
  "field": {
    "kind": "choice",
    "label": "Target",
    "options": [
      { "value": "staging", "label": "Staging", "description": "Internal preprod cluster" },
      { "value": "prod-canary", "label": "Prod (canary)", "description": "1% traffic" },
      { "value": "prod-full", "label": "Prod (full)", "description": "100% traffic" }
    ],
    "default_index": 0
  },
  "notes": {
    "label": "Why this target?",
    "required": true
  },
  "urgency": "warning",
  "timeout_secs": 600
}
```

### Example 4 — integer in a range

```json
{
  "title": "How many retries?",
  "question": "How many times should I retry the failing integration test?",
  "field": {
    "kind": "integer",
    "label": "Retries",
    "min": 1,
    "max": 10,
    "default": 3
  }
}
```

### Example 5 — long-form text

```json
{
  "title": "Refine the commit message",
  "question": "Edit the proposed commit message below.",
  "field": {
    "kind": "long_text",
    "label": "Commit message",
    "default": "feat(phinbox): initial scaffold\n\nImplements native OS popup elicitation.",
    "max_length": 500
  }
}
```

## Anti-patterns

- **Asking what's in the codebase.** Read the file. Don't ask the user.
- **Asking for a number you can count.** Count it.
- **Asking yes/no after a non-destructive read.** Don't ask.
- **Batching 5 decisions into one popup.** Break into 5 calls.
- **Skipping the question text.** The user needs context.
- **Using urgency=warning for routine questions.** Reserve warning for real warnings.
- **Setting timeout_secs to 0 outside CI.** The popup will block forever.

## Failure modes

The agent must handle every status:

| Status | Cause | Recovery |
|---|---|---|
| `answered` | Normal path | Use the value |
| `cancelled` | User clicked Cancel | Fall back to a default or halt and ask in chat |
| `timed_out` | 10 min default elapsed | Retry once with longer timeout, or surface |
| `failed` | Renderer crashed (no display, missing `osascript`, etc.) | Retry with `renderer=force-tty`, or inline-question fallback |

## Plugin installation

| Host | Install command |
|---|---|
| Forge | `./plugins/forgecode/install.sh [host-repo-path]` |
| Codex | `./plugins/codex/install.sh [host-repo-path]` |
| Cursor | `./plugins/cursor/install.sh [host-repo-path]` |

All three install scripts wire `phinbox-mcp` as an MCP server and
register the SKILL.md so the host agent activates the tool automatically.

## See also

- `crates/phinbox/docs/RESEARCH.md` — full design rationale
- `plans/2026-07-21-phinbox-EXECUTION-PLAN-v1.md` — implementation plan
- `crates/phinbox/README.md` — CLI reference