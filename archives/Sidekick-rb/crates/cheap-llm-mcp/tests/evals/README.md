# Evals

Comparative eval scaffolding for cheap-llm-mcp vs Claude Haiku baseline.

**Status:** scaffold only. Not runnable in CI (needs real API keys).

## Planned tasks

- `summarize_doc`: 2000-token doc → 5-bullet summary
- `extract_json`: unstructured paragraph → structured JSON
- `classify_intent`: user utterance → one of {query, command, chitchat}
- `write_pytest`: function signature → 3 test cases
- `regex_translate`: English spec → regex pattern

## Judge model

Use Claude Sonnet as grader (not Haiku — we want a *better* judge than the competing models). Rubric-based scoring: correctness, concision, format adherence.

## Metrics

- Cost delta per 100 tasks (Haiku vs cheap-llm on Minimax/Kimi)
- p50/p95 latency
- Quality score (0-5 from Sonnet judge)
- Cost-quality frontier plot

## When to run

- Before rolling out `cheap-reasoner` subagent as default in any automated flow
- After provider changes (Minimax version bump, new Kimi release)
- When considering `routing = "cost_quality"` as the default in thegent-dispatch

## Out of scope for v0

- Live eval in CI (billing constraint)
- Reference corpus maintenance — start with 20 seed tasks
- Human labeling baseline — just use the Sonnet judge for v0
