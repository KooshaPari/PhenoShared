# Assumptions log — {{PROJECT_NAME}}

Agents record beliefs about user intent here before acting on ambiguous asks. Each row links to prompt evidence where possible.

| Assumption | Evidence | Action taken | Validated? | Date |
|------------|----------|--------------|------------|------|
| {{ASSUMPTION}} | [prompt](prompts/cursor/{{PROMPT_FILE}}.md) | {{ACTION}} | pending | {{DATE}} |

## Validation states

| State | Meaning |
|-------|---------|
| `pending` | Agent acted; user has not confirmed |
| `yes` | User confirmed in session or follow-up prompt |
| `no` | User rejected — update [synthesis.md](synthesis.md) and [charter.md](../../../charter.md) if scope impact |

## Rules

1. Append a row when implementing an **inferred** goal from [synthesis.md](synthesis.md)
2. Mark `yes`/`no` when user clarifies in a new prompt (scrape to `prompts/`)
3. Do not delete rows — strike through superseded assumptions with date note

Refresh: after each major agent session affecting scope or architecture.
