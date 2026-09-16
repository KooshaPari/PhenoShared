# agent-forecast

Reads `~/.claude/agent-history.jsonl` and computes p50/p90 token priors per category.

Categories: `sweep audit refactor dependabot scaffold extract merge docs test eval fork cleanup`

## Usage

```bash
agent-forecast categorize "refactor the auth module"
# → refactor

agent-forecast budget refactor
# → {"category":"refactor","p50_tokens":0,"p90_tokens":0,"sample_count":0}
```

History JSONL fields: `timestamp`, `prompt_hash_category`, `tool_uses`, `duration_ms`, `total_tokens`, `outcome`.
