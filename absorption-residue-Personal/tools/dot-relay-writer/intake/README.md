# Dot intake (spool poller)

Feeds Dot's status records into the relay writer (spec 17.1). Desk-side, no new public endpoint, no secrets in the repo.

Flow: source adapter -> spool/pending -> writer.apply_record -> spool/done or spool/rejected. Non-allowlisted senders go to quarantine (a content-free guard_reject event). A (source, message-id) dedupe table drops replays. Poll every 5 minutes with backoff; an hourly `intake_heartbeat` events row makes silence visible.

Only fenced ```json blocks are read; all other body text is dropped. Dot may only post record types status, digest, edge, estimate, actual. confirm / flag_stale / note are lane actions and are rejected from these sources, so Dot cannot forge a lane confirmation.

Config is env-only (see poller.py docstring): INTAKE_DB, INTAKE_SPOOL, INTAKE_MAIL_ALLOW + INTAKE_MAIL_CMD, INTAKE_DISCORD_ALLOW + INTAKE_DISCORD_CMD. The *_CMD commands print one JSON object per line: {"id","sender","body"}. Unit: dot-intake.service (EnvironmentFile=/root/dot-intake.env).

Tests: python3 -m unittest test_intake

## Security rules (runbook)

- Lane actions (confirm, flag_stale, note) run only from desk-side lane code via the writer CLI, never through any spool, mail or Discord path. Intake rejects them.
- Dot may not post `actual`: actuals feed velocity/ETA, which only lane-confirmed data may drive. Dot may post status, digest, edge, estimate.
- recorded_by / estimated_by / created_by are forced to `dot` on every intake record; the field in the message is ignored.
- guard_reject rows are capped at 20 per source per hour; past the cap only a counter (`reject_suppressed` in the heartbeat) grows.
- The dedupe row is written after a message is fully handled, so a crash mid-apply retries rather than drops.
- Mail fetcher (`mail_fetch.py`) emits only messages whose Authentication-Results show spf=pass, dkim=pass and dmarc=pass. The mail leg is off unless `INTAKE_MAIL_ENABLED=1`; keep it off until the first real Dot mail lands.
- Discord fetcher (`discord_fetch.py`) is GET-only. The bot token comes from Infisical at process start (`infisical run`), never from a file or env file. Allowlist entry is `<channel_id>:<author_id>`.
