# UX — SOTA ({{PROJECT_NAME}})

## Use case

End-user experience for people who **use the product** (not developers maintaining the repo).

## Status

{{UX_STATUS — choose one:}}

**N/A — infrastructure / template repo with no end-user UI.**

End-user UX for products built *from* this scaffold is owned by each application repo's `docs/sota/ux.md`.

— **or** —

**Active — this repo ships user-facing surfaces.**

## Requirements (if active)

| Requirement | Weight |
|-------------|--------|
| {{UX_REQ_1 — e.g. task completion in N clicks}} | must |
| Accessibility baseline (WCAG 2.1 AA) | should |
| {{UX_REQ_2}} | should |

## Alternatives considered (if active)

| Alternative | Pros | Cons | Verdict |
|-------------|------|------|---------|
| {{UI_FRAMEWORK_A}} | … | … | rejected — {{REASON}} |
| {{UI_FRAMEWORK_B}} | … | … | **chosen** |

## Chosen strategy

{{DESCRIBE_UX_PATTERNS — information architecture, key flows, design system}}

## Evolution triggers

- User research contradicts current flow
- Platform accessibility requirement change
- Major UI framework LTS end

Update [../../../SOTA.md](../../../SOTA.md) UX row when status or choice changes.
