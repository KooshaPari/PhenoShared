# Graduation Path → PhenoMCP

`cheap-llm-mcp` is currently a standalone repo because:
- It's temp-dev infra (per user's initial framing).
- It needs to stand alone as a discoverable skill/MCP for Claude Code subagents.

The long-term home is **PhenoMCP** — the polyglot MCP initiative at
`/Users/kooshapari/CodeProjects/Phenotype/repos/PhenoMCP`. PhenoMCP already
covers Rust + Python + Go + Mojo + TS clients + FFI bindings; adding a Python
MCP server as a peer is natural.

## Triggers for graduation

Graduate when **any** are true:
1. `cheap-llm-mcp` has >3 consumers beyond Claude Code subagents (other IDE plugins, other agents).
2. Additional provider backends are added (Groq, Together, DeepInfra, Cerebras) — the shared OpenAI-compat client becomes a reusable component across MCP servers.
3. The unified `thegent` skill is landed and wants to reuse cheap-llm's router.
4. Cost-ledger behavior is shared with other internal MCP servers.

## Graduation steps

1. Move `src/cheap_llm_mcp/` → `PhenoMCP/python/cheap_llm_mcp/`.
2. Re-parent `pyproject.toml` to PhenoMCP's Python workspace (uv workspace or poetry path-dep).
3. Extract the OpenAI-compat client (`providers/openai_compat.py`) + retry + cache into a `phenomcp.providers.openai_compat` shared package so other Python MCP servers under PhenoMCP reuse it.
4. Keep `~/.claude/skills/cheap-llm/SKILL.md` pointing at the PhenoMCP-packaged binary (`cheap-llm-mcp` entry point on PATH unchanged).
5. Leave a 1-line `README.md` stub in the old location pointing at the new home.

## Non-graduation signals

Stay standalone if:
- `cheap-llm-mcp` turns out to be single-consumer (only Claude Code subagents) and no other callers emerge.
- The cheap-LLM routing story is subsumed by `thegent-dispatch` entirely — at which point this repo collapses into `thegent-dispatch` and we delete it.

## Related

- PhenoMCP: `/Users/kooshapari/CodeProjects/Phenotype/repos/PhenoMCP`
- McpKit (alternative polyglot MCP): `/Users/kooshapari/CodeProjects/Phenotype/repos/McpKit` — currently "under construction"; less ambitious than PhenoMCP.
- AgentMCP/SmartCP (production MCP frontend): different layer — for user-facing MCP orchestration, not library-style utility servers.
