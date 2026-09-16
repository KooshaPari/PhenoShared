# anthropic-usage-poll

Daemon polling the Anthropic Admin API for organization token usage.

Writes `~/.claude/usage.json` with fields: `daily_remaining`, `monthly_remaining`,
`per_model_tokens_last_24h`, `updated_at`.

## Usage

```bash
ANTHROPIC_ADMIN_KEY=sk-... anthropic-usage-poll --once
anthropos-usage-poll --interval 300
```

Polls `GET /v1/organizations/usage_report/messages` every `--interval` seconds (default 600).
