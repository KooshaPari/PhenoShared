# Plan — <REDACTED> Oldest-First

## Objective

Codify the oldest-first ordering policy for <REDACTED> fleet remediation sweeps so that agents consistently target the most-neglected repos before recently active ones.

## Scope

- In: ordering policy for sweeps, top-N selection, worklog header contract.
- Out: actual remediation actions, PR content, CI fixes.

## Implementation Steps

1. Run `gh repo list <REDACTED> --limit 200 --json name,pushedAt,isArchived` and capture the JSON output with a UTC timestamp.
2. Filter out entries where `isArchived` is `true`.
3. Sort remaining entries by `pushedAt` ascending (ties: `name` ascending).
4. Take the top N as the sweep target set; embed `name` + `pushedAt` for each in the worklog header alongside the captured timestamp and the literal `gh` command.
