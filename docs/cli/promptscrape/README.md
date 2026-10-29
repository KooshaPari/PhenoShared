# promptscrape

Extract the full **human prompt timeline** from JCode and Codex harness sessions.

`promptscrape` exists so an agent working from a state HTML (a walkthrough, a
lane report, a session audit) can get the prompts behind it without having to
derive session ids by hand or read raw harness artifacts. It reads only JCode
and Codex session data, and returns only the prompts a human actually typed.

## Why it exists

State HTMLs *visualize* session timelines; they do not contain them. The
prompt bodies live in the harness session store. `promptscrape` bridges the two:

1. derive the session id from the HTML (or from the current environment),
2. read the session from the authoritative harness store,
3. return the real user prompts, numbered, timestamped, and id-tagged.

The output is shaped for curation: annotate it, label it, slice it, diff it.

## Install

### curl (recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/KooshaPari/PhenoShared/main/scripts/install-promptscrape.sh | sh
```

Installs to `~/.local/bin` by default. Override with `--dir`:

```bash
curl -fsSL https://raw.githubusercontent.com/KooshaPari/PhenoShared/main/scripts/install-promptscrape.sh | sh -s -- --dir /usr/local/bin
```

### go install

```bash
go install github.com/KooshaPari/PhenoShared/cmd/promptscrape@latest
```

### From source

```bash
git clone https://github.com/KooshaPari/PhenoShared.git
cd PhenoShared/cmd/promptscrape
go build -o promptscrape .
./promptscrape install
```

The binary is pure Go (no cgo), so it cross-compiles for macOS and Linux on
amd64 and arm64.

## Usage

```bash
# Current session (cwd match, then most recent)
promptscrape scrape

# A state HTML: the session id is derived from the file
promptscrape scrape ~/Exports/session-b-walkthrough.html

# An explicit session
promptscrape scrape --session session_pig_1792638703385_34d0c212ece1d6b9
promptscrape scrape --session 019dd872-83de-76b1-a635-7bce3b0f3a54

# Machine-readable output for a curation pipeline
promptscrape scrape --format json > prompts.json

# Metadata
promptscrape version
```

### Output

Text format:

```
=== PROMPT 1 | 2026-10-28T23:59:25.887854Z | message_1793231965887_2523084014132851572 ===
quickly, need a solu for agents building state htmls like this: ...
```

JSON format:

```json
{
  "session_id": "session_hamster_1793231882338_6acad471b77d6cf7",
  "source": "jcode",
  "prompts": [
    {
      "id": "message_1793231965887_2523084014132851572",
      "timestamp": "2026-10-28T23:59:25.887854Z",
      "text": "quickly, need a solu for agents building state htmls like this: ..."
    }
  ]
}
```

`source` is one of `jcode`, `codex-sqlite`, or `codex-rollout`.

## Update

```bash
promptscrape update
```

Or without the binary:

```bash
curl -fsSL https://raw.githubusercontent.com/KooshaPari/PhenoShared/main/scripts/update-promptscrape.sh | sh
```

Pin a specific release:

```bash
promptscrape update --version promptscrape-v0.2.0
```

## Uninstall

```bash
promptscrape uninstall
```

Or:

```bash
curl -fsSL https://raw.githubusercontent.com/KooshaPari/PhenoShared/main/scripts/uninstall-promptscrape.sh | sh
```

## How session resolution works

Session ids are never guessed. They are derived in this order:

1. `--session` flag
2. the `JCODE_SESSION_ID` environment variable
3. ids embedded in the given HTML file
   - every distinct candidate is tried, and the first that actually yields
     prompts wins, so a file naming both a JCode lane and the Codex thread it
     audited resolves to whichever still has data
4. the session whose `working_dir` matches the current directory
5. the most recently updated session

## How extraction works

### JCode

- Reads `~/.jcode/sessions/<id>.json` (the harness snapshot)
- Merges `~/.jcode/sessions/<id>.journal.jsonl` (the append-only log written
  after the snapshot), deduplicating by message id
- Orders by timestamp, with the message id as a stable tiebreaker
- Keeps `role == "user"` messages whose first `text` block is human input
- Drops `display_role` of `system` and `background_task`

### Codex

- Reads `~/.codex/thread_history_1.sqlite` first. This is authoritative: it
  survives rollout-file pruning and carries both the stable item id and the
  creation timestamp
- Falls back to the rollout transcript under `~/.codex/sessions/` when the
  database has no rows for the thread, reading `.jsonl` and `.jsonl.zst`
- Uses the `internal_chat_message_metadata_passthrough.content_item_kinds ==
  ["user.text"]` discriminator to tell a typed prompt from injected context

### Filtering

These never reach the output:

| Filtered | Why |
|---|---|
| `<environment_context>` | harness-injected context |
| `<permissions instructions>` | harness-injected context |
| `<user_instructions>` | harness-injected context |
| `<system-reminder>` | harness-injected context |
| `# AGENTS.md` | injected project context |
| `<\|...` | harness continuation marker |
| tool results | not human input |
| rendered agent transcripts | agent output, not human input |

Codex resumes a session by replaying the whole rendered turn -- the agent's
bullets, its tool transcripts, and the human's own input -- into a single
stored "user" message. When that happens `promptscrape` recovers only the
human's own lines (those prefixed with the TUI prompt marker `›`) and emits
each as its own prompt, with a `#N` suffix on the id so every prompt stays
traceable back to its source item.

## Development

```bash
cd cmd/promptscrape
go build ./...
go test ./...
go vet ./...
```

Build with version metadata:

```bash
PKG="github.com/KooshaPari/PhenoShared/cmd/promptscrape/cmd"
go build -ldflags "-s -w -X ${PKG}.version=1.2.3 -X ${PKG}.commit=$(git rev-parse --short HEAD)" -o promptscrape .
```

Releases are published by `.github/workflows/release-promptscrape.yml` on a
`promptscrape-v*` tag. Artifacts are named `promptscrape-<os>-<arch>`.
