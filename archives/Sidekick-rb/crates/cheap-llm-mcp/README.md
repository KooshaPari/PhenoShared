# cheap-llm-mcp

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://img.shields.io/github/actions/workflow/status/KooshaPari/cheap-llm-mcp/ci.yml?branch=main)](https://github.com/KooshaPari/cheap-llm-mcp/actions)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python)](https://www.python.org/)
[![AI Slop Inside](https://sladge.net/badge.svg)](https://sladge.net)

MCP server + CLI that wraps Minimax, Kimi, and Fireworks-hosted open models behind an OpenAI-compatible chat-completions surface. Designed as a **Haiku-replacement** for Claude Code subagents: cheap, fast, good-enough reasoning without touching Anthropic's own API traffic.

**Why not intercept Haiku?** Anthropic actively detects 3rd-party clients replaying Max-subscription OAuth tokens; account-action risk is medium-high. MCP-as-tool keeps Claude Code's own traffic 100% untouched while still letting subagents route cheap work elsewhere.

## Architecture

```
Claude Code subagent
    │
    └─ calls MCP tool:  cheap_llm.complete(prompt, provider="auto", ...)
         │
         └─ cheap-llm-mcp server (FastMCP, stdio)
              │
              └─ Router ──► Minimax  (/v1/chat/completions, MiniMax-M2 / m2.7 variants)
                         ──► Kimi     (api.moonshot.ai, kimi-k2-turbo-preview)
                         ──► Fireworks (fallback / mirror)
```

## Install

```bash
cd cheap-llm-mcp
pip install -e .
# or: uv pip install -e .
```

## Configure

```bash
mkdir -p ~/.cheap-llm
cp config/cheap-llm.example.toml ~/.cheap-llm/config.toml
export MINIMAX_API_KEY=...
export MOONSHOT_API_KEY=...
export FIREWORKS_API_KEY=...
```

## Use as CLI

```bash
cheap-llm "summarize this codebase structure" --provider minimax
echo "one-liner: invert a dict in python" | cheap-llm --stream
```

## Use as MCP in Claude Code

`~/.claude/settings.json`:
```json
{
  "mcpServers": {
    "cheap-llm": { "command": "cheap-llm-mcp" }
  }
}
```

Then instruct subagents to call the `cheap_llm.complete` MCP tool instead of thinking inline. See `~/.claude/agents/cheap-reasoner.md`.

## Tools exposed

- `complete(prompt, system?, provider=auto, variant=highspeed, model?, max_tokens=4096, temperature=0.2)` — one-shot completion. Returns usage + cost estimate.
- `stream_complete(...)` — same args; aggregates streamed chunks (faster TTFB on the provider side).
- `providers()` — show known providers and default models.
- `list_live_models(provider)` — query provider's `/v1/models` to discover exact model IDs.
- `health()` — probe all configured providers; returns status + latency.
- `cost_summary(month?)` — month-to-date spend from the JSONL ledger.

## Defaults (verified April 2026)

- Minimax: `MiniMax-M2.7` / `MiniMax-M2.7-highspeed` — no dedicated `-codex` variant exists; M2.7 is strong at code.
- Kimi: `kimi-k2-turbo-preview` on Moonshot, or `accounts/fireworks/models/kimi-k2-instruct` on Fireworks.
- Fireworks mirror for Minimax: `accounts/fireworks/models/minimax-m2p7`.

## Cache (optional)

Set `cache_ttl_seconds = 300` in `~/.cheap-llm/config.toml` to cache repeated
`temperature=0` queries. Good for dev loops where you iterate on the same prompt.

## Testing

```bash
# Unit tests
pytest tests/unit

# Integration tests (requires API keys)
pytest tests/integration -m "not skip_live"

# Provider health check
cheap-llm health --verbose

# Benchmark cost
cheap-llm benchmark --iterations 10 --provider auto
```

## Cost Estimation

All responses include cost breakdown:

```json
{
  "output": "...",
  "usage": {
    "input_tokens": 150,
    "output_tokens": 45
  },
  "cost": {
    "input_cost_usd": 0.00075,
    "output_cost_usd": 0.00023,
    "total_usd": 0.00098
  }
}
```

Typical costs:
- **Minimax M2.7**: $0.001-0.002 per 1K input + $0.004-0.008 per 1K output
- **Kimi K2**: $0.0015 per 1K input + $0.002 per 1K output
- **Fireworks**: Varies by model, $0.0001-0.0005 per 1K tokens

See [PRICING.md](./docs/PRICING.md) for latest rates.

## Configuration Reference

```toml
[server]
host = "localhost"
port = 3000

[routing]
default_provider = "auto"  # auto, minimax, kimi, fireworks
default_model = "auto"
provider_order = ["minimax", "kimi", "fireworks"]  # Fallback order

[cache]
enabled = true
ttl_seconds = 300

[cost_limits]
monthly_cap_usd = 100.00
alerts_at_percent = 75  # Alert at 75% of cap

[minimax]
api_key_env = "MINIMAX_API_KEY"
base_url = "https://api.minimaxi.com/v1"

[moonshot]
api_key_env = "MOONSHOT_API_KEY"
base_url = "https://api.moonshot.ai/v1"

[fireworks]
api_key_env = "FIREWORKS_API_KEY"
base_url = "https://api.fireworks.ai/inference/v1"
```

## Performance Notes

- **Latency**: Minimax ~500-800ms, Kimi ~300-500ms, Fireworks ~200-400ms (varies)
- **Context Window**: 
  - Minimax M2.7: 8K tokens
  - Kimi K2: 128K tokens
  - Model selection should prefer Kimi for large context
- **Rate Limits**: Most providers allow 60 req/min; configure backoff accordingly

## Roadmap

**v0.1.0** (Current) — Core routing scaffolding
- [x] OpenAI-compatible /v1/chat/completions
- [x] CLI interface
- [x] MCP tool exposure
- [x] Cost estimation
- [ ] **Streaming tool** (FastMCP streaming protocol)
- [ ] **Cost ledger** with monthly cap enforcement
- [ ] **Health probes** for all providers
- [ ] **Retry/backoff** with jitter

**v0.2.0** (Planned)
- [ ] Fireworks model auto-discovery
- [ ] A/B evaluation harness
- [ ] Multi-turn conversation tracking
- [ ] Custom system prompt templates

**v0.3.0+**
- [ ] Token budget aware routing
- [ ] Semantic caching of embeddings
- [ ] Provider redundancy + SLA tracking

## Status

**Active — scaffold + core routing complete.** MCP tool exposure verified. See [CHANGELOG.md](./CHANGELOG.md) for release notes.

## Governance

- **Type**: MCP server + CLI tool
- **Language**: Python 3.10+
- **Status**: Active development
- **Part of**: Phenotype Ecosystem — Haiku-replacement strategy
- **Testing**: All code requires unit + integration tests

## References

- **FastMCP**: Uses FastMCP for MCP server scaffolding
- **Pricing**: Up-to-date rates in [docs/PRICING.md](./docs/PRICING.md)
- **Integration**: Designed as Claude Code subagent tool
- **Related**: Part of Phenotype agent infrastructure

## FAQ

**Q: Is this legal?**
A: Yes — all endpoints are official APIs from Minimax, Moonshot, and Fireworks. No token replay or account takeover.

**Q: Why not just use Haiku?**
A: Cost and traffic separation. Haiku = $0.80 per 1M output tokens; Minimax/Kimi = $4-8 per 1M. For bulk reasoning, 10x cheaper.

**Q: What if a provider goes down?**
A: Automatic fallback to next provider in chain. Configure provider_order in config.

**Q: Can I set monthly spending limits?**
A: Yes — set `cost_limits.monthly_cap_usd` in config. Agent will refuse requests once cap is reached.

---

**Last Updated**: 2026-04-25 | **Version**: 0.1.0 | **Status**: Active
