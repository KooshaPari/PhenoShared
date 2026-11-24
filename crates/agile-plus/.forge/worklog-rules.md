# AI-DD Crutch: Worklog Task-ID Guard

## Rule: `worklog_needs_task_id`

### Severity
FAIL (blocks commit)

### Trigger
WORKLOG.md (or any `worklog*.json` / `worklog*.md` file) is staged, but the
diff does not contain a `V*-*` task ID pattern (e.g., `V3-042`, `V2-007`).

### Task ID format

- Pattern: `V[0-9]+-[0-9]+`
- Examples: `V3-042`, `V2-007`, `V1-001`
- The task ID must appear in the diff itself (not just in the commit message).

### Exemptions

- Pure formatting fixes (whitespace-only changes)
- Merge-conflict resolution markers
- Auto-generated worklog entries from CI

### Verification

```bash
pheno-vibecoding-guard run --check worklog_needs_task_id
```
