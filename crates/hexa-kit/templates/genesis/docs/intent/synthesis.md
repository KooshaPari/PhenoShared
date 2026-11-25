# Intent synthesis — {{PROJECT_NAME}}

> Generated from prompt provenance in `prompts/`. Last updated: {{DATE}}.

## Themes (from prompts)

### Theme: {{THEME_NAME}}

**Prompts:** [cursor/...](prompts/cursor/), [forge/...](prompts/forge/)

**User language (paraphrase with citations):**

- "{{QUOTE}}" — [source](prompts/cursor/{{FILE}}.md)

## Confirmed goals

Goals explicitly stated by the user:

1. **{{GOAL}}** — cited from [prompt](prompts/{{PATH}})

## Inferred goals

Agent interpretation — **requires user validation**:

| Inferred goal | Evidence prompts | Agent action taken | Validate? |
|---------------|------------------|--------------------|-----------|
| HexaKit = genesis not lib warehouse | archive audit thread | genesis STANDARD.md | pending |

## Conflicts / tensions

| Tension | Prompts | Resolution |
|---------|---------|------------|
| RATIONALIZATION_PLAN vs genesis-only HexaKit | multiple | Charter + SOTA update; rust-sdk planned |

## Rejected / deferred

- {{ITEM}} — reason

## Recommended next actions (for agents)

1. {{ACTION}} — aligns with [charter.md](../../../charter.md)
2. {{ACTION}} — update [SOTA.md](../../../SOTA.md) when done

## LLM grounding notes

When acting on this repo, agents should:

1. Read `charter.md` before expanding scope
2. Prefer `docs/sota/` choices over ad-hoc alternatives
3. Append new user prompts to `prompts/` before large pivots
