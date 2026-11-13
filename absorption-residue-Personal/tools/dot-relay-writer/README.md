# dot-relay-writer

Desk-side relay writer for the cockpit SSOT plane (spec sections 15-16,
migration 0007). Dot posts JSON records via agent-mail / Discord wake; this
writer validates them against the guards and applies them. Dot holds no
secrets; there is no new public endpoint. Mail and Discord bodies are
untrusted data: only schema-passing records are applied; record contents are
never executed.

Record shape (JSON object):
- `type`: `status` (default) | `digest` | `edge` | `estimate` | `actual`
- status: `project_id`, `status` (controlled vocab), `percent` 0-100 OR
  `unknown_cause` + `start_step`, `text`, `base_updated_at`
- digest: `period_start`, `period_end`, `format` (pdf|json|markdown), `uri`, `summary`
- edge: `from_task_id`, `to_task_id`, `kind` (blocks|soft), `created_by`
- estimate: `task_id`, `size_class_id`, `est_hours_p50`, `est_hours_p90`, `basis`
- actual: `task_id`, `started_at`, `finished_at`, `actual_hours`, `source`

Guards (rejections land in `events` as `guard_reject`, never storing record
content): project allowlist, status vocab, percent rule, length caps, secret
scrub, stale-clobber on `base_updated_at`, 60 writes/h, edge cycle rejection.

Usage:
- `writer.py apply record.json --db sqlite:cockpit.db`
- `writer.py spool /spool/dir --db d1:COCKPIT_DB_NAME` (desk-only sanctioned
  write path; ad-hoc wrangler stays read-only)
- `writer.py derive-velocity --lane L --start DATE --end DATE --db ...`

Intake wiring (mail/Discord -> spool) is a separate follow-up.
