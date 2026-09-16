# temporal-grounding

Three binaries for temporal grounding in Claude Code sessions.

- **agent-start-stamp** `[id] [label]` — appends to `~/.claude/active-agents.json`, prints the agent ID
- **agent-elapsed** `<id>` — prints seconds elapsed since that agent started
- **now-iso** — prints current UTC time in ISO 8601 (seconds precision)

## Usage

```bash
ID=$(agent-start-stamp "" sweep)
# ... run work ...
agent-elapsed "$ID"   # → 42s
now-iso               # → 2024-01-01T12:00:00Z
```
