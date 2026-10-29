# promptscrape

A CLI tool to scrape full prompt timelines from JCode and Codex harness sessions.

## Features

- **Auto-detection**: Derives session ID from HTML files or falls back to current session
- **JCode support**: Merges `.json` (authoritative) + `.journal.jsonl` (appends) with deduplication
- **Codex support**: Uses `thread_history_1.sqlite` first (covers pruned threads), falls back to rollout files
- **Smart filtering**: Skips system reminders, tool results, environment context, and continuations
- **Output ready for curation**: Formatted for annotation and labeling

## Installation

### Via curl (recommended)
```bash
curl -fsSL https://raw.githubusercontent.com/phenotype/phenoShared/main/scripts/install-promptscrape.sh | sh
```

### Via go install
```bash
go install github.com/phenotype/phenoShared/cmd/promptscrape@latest
```

### Build from source
```bash
cd phenoShared/cmd/promptscrape
go build -o promptscrape .
./promptscrape install
```

## Usage

```bash
# Auto-detect from HTML file
promptscrape scrape path/to/lane-walkthrough.html

# Use current session
promptscrape scrape

# Explicit session ID (JCode or Codex)
promptscrape scrape --session session_pig_1234567890_abc123
promptscrape scrape --session 01a11ecd-9cb0-7003-acd4-2fa6e255169e

# Check version
promptscrape version

# Self-install/uninstall
promptscrape install
promptscrape uninstall
```

## Update

```bash
curl -fsSL https://raw.githubusercontent.com/phenotype/phenoShared/main/scripts/update-promptscrape.sh | sh
# or
promptscrape update  # if available
```

## Uninstall

```bash
curl -fsSL https://raw.githubusercontent.com/phenotype/phenoShared/main/scripts/uninstall-promptscrape.sh | sh
# or
promptscrape uninstall
```

## How it works

### Session resolution order
1. `--session` flag or `$JCODE_SESSION_ID` env var
2. Session ID found in HTML via regex (`session_*` or Codex UUID)
3. Match current working directory in `~/.jcode/sessions/*.json`
4. Most recent session as fallback

### JCode extraction
- Loads `~/.jcode/sessions/<id>.json` (authoritative)
- Merges `~/.jcode/sessions/<id>.journal.jsonl` appends (deduplicates by ID, sorts by timestamp)
- Filters: `role == "user"`, `display_role != "system"`, text not starting with `<system-reminder>`

### Codex extraction
- Tries `~/.codex/thread_history_1.sqlite` first (covers pruned threads)
- Falls back to rollout files in `~/.codex/sessions/YYYY/MM/DD/`
- Handles `.jsonl` and `.jsonl.zst` (uses klauspost/compress)
- Filters using `internal_chat_message_metadata_passthrough.content_item_kinds == ["user.text"]` discriminator
