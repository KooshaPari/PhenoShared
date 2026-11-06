# cheap-llm-mcp State of the Art (SOTA) Research

## Executive Summary

cheap-llm-mcp represents a pragmatic solution to the growing need for cost-effective LLM inference in development workflows. This document analyzes the current landscape of cheap LLM providers, MCP server architectures, and routing strategies that enable developers to leverage Haiku-class reasoning at a fraction of the cost. The project serves as a Haiku-replacement for Claude Code subagents, providing OpenAI-compatible endpoints backed by Minimax, Kimi, and Fireworks-hosted models.

## 1. Low-Cost LLM Provider Landscape

### 1.1 Market Evolution

The LLM inference market has undergone significant transformation since 2024, with the emergence of competitive alternatives to Anthropic's Haiku and OpenAI's GPT-4o-mini:

**2024 Q1-Q2: Initial Competition**
- Minimax launched M2 series with aggressive pricing
- Moonshot (Kimi) established presence with long-context models
- Fireworks.ai began offering hosted open-weight models at scale

**2024 Q3-Q4: Price Wars**
- Input token prices dropped 60-80%
- Context windows expanded significantly
- Model quality improved substantially

**2025-Present: Consolidation**
- Specialized inference providers emerged
- OpenAI-compatible APIs became standard
- MCP (Model Context Protocol) adoption accelerated

### 1.2 Provider Analysis

#### 1.2.1 Minimax

**Technical Profile:**
- Models: MiniMax-M2, M2.5, M2.7 (with highspeed variants)
- Context Window: 8K tokens (M2.7)
- Pricing: ~$0.30-1.20 per 1M tokens (input/output)
- API Compatibility: OpenAI-compatible `/v1/chat/completions`

**Strengths:**
- Strong code completion capabilities
- Fast inference with highspeed variants
- Competitive pricing for bulk reasoning
- Chinese-market optimization with global availability

**Limitations:**
- Smaller context window than competitors
- No dedicated codex variant (M2.7 covers code use cases)
- Regional latency variations

**Architecture Pattern:**
```python
# Minimax direct integration
class MinimaxProvider:
    def __init__(self, api_key: str):
        self.client = httpx.AsyncClient(
            base_url="https://api.minimaxi.com/v1",
            headers={"Authorization": f"Bearer {api_key}"}
        )

    async def complete(self, messages: list[dict]) -> Completion:
        response = await self.client.post("/chat/completions", json={
            "model": "MiniMax-M2.7-highspeed",
            "messages": messages,
            "max_tokens": 4096,
            "temperature": 0.2
        })
        return self._parse_response(response)
```

#### 1.2.2 Moonshot (Kimi)

**Technical Profile:**
- Models: kimi-k2-turbo-preview
- Context Window: 128K tokens (significant advantage)
- Pricing: ~$0.60-2.50 per 1M tokens
- API Compatibility: OpenAI-compatible

**Strengths:**
- Massive context window for document processing
- Strong Korean and Chinese language support
- Excellent for long-context summarization tasks
- Turbo variants optimize for speed

**Limitations:**
- Higher per-token cost than Minimax
- Some latency variance
- Rate limiting on lower tiers

**Architecture Pattern:**
```python
# Kimi/Kimi long-context optimization
class KimiProvider:
    async def complete(self, messages: list[dict], context_window: int = 128000):
        # Automatically chunk long contexts if needed
        total_tokens = self._estimate_tokens(messages)
        if total_tokens > context_window * 0.9:
            messages = self._compress_context(messages)
        return await self._direct_complete(messages)
```

#### 1.2.3 Fireworks.ai

**Technical Profile:**
- Models: Minimax M2P7 mirror, Kimi K2 instruct, mixtral, llama variants
- Context Window: Variable by model (8K-32K typical)
- Pricing: Varies by model ($0.10-3.00 per 1M tokens)
- API Compatibility: OpenAI-compatible with account prefixes

**Strengths:**
- Model variety (hosted open-weight models)
- Competitive pricing on specific models
- Good fallback reliability
- Enterprise features available

**Limitations:**
- Model discovery required (no single default)
- Inconsistent pricing across models
- Some models require specific prefixes

**Architecture Pattern:**
```python
# Fireworks multi-model routing
class FireworksProvider:
    MODEL_VARIANTS = {
        "minimax": "accounts/fireworks/models/minimax-m2p7",
        "kimi": "accounts/fireworks/models/kimi-k2-instruct",
        "mixtral": "accounts/fireworks/models/mixtral-8x7b-instruct",
    }

    async def complete(self, messages: list[dict], model_type: str = "minimax"):
        model = self.MODEL_VARIANTS.get(model_type, self.MODEL_VARIANTS["minimax"])
        return await self._post("/chat/completions", {"model": model, "messages": messages})
```

### 1.3 Pricing Comparison Matrix

| Provider | Model | Input $/1M | Output $/1M | Context | Latency | Best For |
|----------|-------|------------|-------------|---------|---------|----------|
| Minimax | M2.7-highspeed | $0.30 | $1.20 | 8K | ~500-800ms | Code, bulk reasoning |
| Kimi | k2-turbo | $0.60 | $2.50 | 128K | ~300-500ms | Long documents |
| Fireworks | minimax-m2p7 | $0.50 | $1.50 | 8K | ~200-400ms | Fallback, variety |
| Anthropic | Haiku | $0.80 | $4.00 | 200K | ~200-400ms | Claude integration |
| OpenAI | gpt-4o-mini | $0.15 | $0.60 | 128K | ~200-300ms | General purpose |

**Cost Analysis:**
- cheap-llm-mcp achieves 3-5x savings vs. Haiku for bulk reasoning tasks
- Trade-off: slightly higher latency, less Claude-native integration
- Context window differences matter for specific use cases

## 2. MCP Server Architecture Patterns

### 2.1 MCP Protocol Overview

The Model Context Protocol (MCP) enables standardized tool exposure for AI models:

**Core Concepts:**
- Tools: Callable functions exposed to AI models
- Resources: Data sources AI can read
- Prompts: Templated interactions

**Implementation Frameworks:**

1. **FastMCP (Python)**
   - Used by cheap-llm-mcp
   - Simple decorator-based tool definition
   - stdio transport for Claude Code integration

```python
from fastmcp import FastMCP

mcp = FastMCP("cheap-llm")

@mcp.tool(description="Complete a prompt using cheap LLM providers")
async def complete(prompt: str, provider: str = "auto") -> dict:
    # Implementation
    return {"text": result, "cost_usd": cost}
```

2. **MCP SDK (TypeScript/Node)**
   - Official SDK from Anthropic
   - Better for TypeScript-first projects
   - SSE + HTTP transport options

3. **Custom Implementation**
   - Direct protocol implementation
   - Maximum flexibility
   - Higher development overhead

### 2.2 MCP Tool Design Patterns

#### 2.2.1 Tool Naming Conventions

```python
# Good tool design
@mcp.tool(description="Complete a prompt using a cheap LLM...")
async def complete(
    prompt: str,
    system: str | None = None,  # Optional context
    provider: Literal["auto", "minimax", "kimi", "fireworks"] = "auto",
    variant: str = "highspeed",
    model: str | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.2,
) -> dict:
    """Single, well-documented entry point."""
    pass
```

#### 2.2.2 Response Structure

```python
# Standardized response format
@dataclass
class CompletionResponse:
    text: str                    # Primary output
    model: str                   # Model used
    provider: str                # Provider name
    usage: UsageInfo             # Token counts
    cost_usd: float              # Calculated cost
    finish_reason: str | None    # stop, length, etc.
    request_id: str              # Traceability

@dataclass
class UsageInfo:
    input_tokens: int
    output_tokens: int
    # Avoid: total_tokens (can be computed)
```

#### 2.2.3 Error Handling

```python
async def complete(prompt: str, ...) -> dict:
    try:
        result = await router.complete(prompt, ...)
        return {"text": result.text, "status": "success", ...}
    except ProviderError as e:
        # Provider-specific errors
        return {"error": str(e), "code": "PROVIDER_ERROR", ...}
    except CostCapExceeded as e:
        return {"error": "Monthly cap exceeded", "code": "CAP_EXCEEDED", ...}
    except Exception as e:
        # Unexpected errors - don't leak internals
        log.exception("Unexpected error in complete")
        return {"error": "Internal error", "code": "INTERNAL_ERROR", ...}
```

### 2.3 Transport Patterns

#### 2.3.1 stdio Transport (Claude Code)

```json
// Claude Code MCP configuration
{
  "mcpServers": {
    "cheap-llm": {
      "command": "cheap-llm-mcp",
      "args": []
    }
  }
}
```

**Characteristics:**
- Process spawn by Claude Code
- JSON-RPC over stdin/stdout
- No network exposure
- Fast for local execution

#### 2.3.2 HTTP/SSE Transport

```python
# HTTP server for remote MCP
from fastapi import FastAPI
from sse_starlette.sse import EventSourceResponse

app = FastAPI()

@app.get("/mcp")
async def mcp_endpoint(request: Request):
    async def event_generator():
        async for event in mcp.handle(request):
            yield {"event": event.type, "data": event.data}
    return EventSourceResponse(event_generator())
```

**Characteristics:**
- Network-accessible
- Better for distributed setups
- Requires authentication
- Higher latency potential

## 3. Router & Failover Architecture

### 3.1 Provider Routing Strategies

#### 3.1.1 Static Routing

```python
class StaticRouter:
    def __init__(self, providers: list[Provider], default: str):
        self.providers = {p.name: p for p in providers}
        self.default = default

    async def complete(self, prompt: str, provider: str | None = None) -> Completion:
        name = provider or self.default
        return await self.providers[name].complete(prompt)
```

**Pros:** Simple, predictable
**Cons:** No automatic failover, no load balancing

#### 3.1.2 Priority Fallback Routing

```python
class PriorityRouter:
    def __init__(self, providers: list[Provider], order: list[str]):
        self.providers = {p.name: p for p in providers}
        self.order = order

    async def complete(self, prompt: str, provider: str | None = None) -> Completion:
        if provider and provider != "auto":
            return await self.providers[provider].complete(prompt)

        last_error = None
        for name in self.order:
            try:
                return await self.providers[name].complete(prompt)
            except Exception as e:
                log.warning(f"Provider {name} failed: {e}")
                last_error = e
        raise RuntimeError(f"All providers failed: {last_error}")
```

**Pros:** Automatic failover, simple implementation
**Cons:** Fixed order, no health-aware routing

#### 3.1.3 Health-Aware Routing

```python
class HealthAwareRouter:
    async def _select_provider(self) -> str:
        health_scores = {}
        for name, provider in self.providers.items():
            health = await provider.health()
            if health["status"] == "ok":
                # Lower latency = higher score
                latency_score = max(0, 1000 - health["latency_ms"]) / 1000
                health_scores[name] = latency_score

        if not health_scores:
            raise RuntimeError("No healthy providers")

        return max(health_scores, key=health_scores.get)
```

**Pros:** Adapts to provider health
**Cons:** Additional health check overhead

### 3.2 Retry Strategies

#### 3.2.1 Exponential Backoff with Jitter

```python
RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}

async def with_retry(fn, attempts: int = 4, base_delay: float = 0.5):
    for i in range(attempts):
        try:
            return await fn()
        except httpx.HTTPStatusError as e:
            if e.response.status_code not in RETRYABLE_STATUS:
                raise
            delay = min(10.0, base_delay * (2**i)) + random.uniform(0, 0.25)
            await asyncio.sleep(delay)
        except (httpx.ReadTimeout, httpx.ConnectError):
            delay = min(10.0, base_delay * (2**i)) + random.uniform(0, 0.25)
            await asyncio.sleep(delay)
    raise RuntimeError("Max retries exceeded")
```

**Key Considerations:**
- Jitter prevents thundering herd
- Max delay cap prevents excessive waits
- Distinguish retryable vs. non-retryable errors

#### 3.2.2 Circuit Breaker Pattern

```python
class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = 0

    async def call(self, fn):
        if self.failures >= self.failure_threshold:
            if time.time() - self.last_failure_time < self.timeout:
                raise CircuitOpenError("Circuit is open")
            self.failures = 0  # Half-open: try again

        try:
            result = await fn()
            self.failures = 0
            return result
        except Exception:
            self.failures += 1
            self.last_failure_time = time.time()
            raise
```

## 4. Caching & Cost Optimization

### 4.1 Cache Architecture

#### 4.1.1 TTL Cache Implementation

```python
class TTLCache:
    def __init__(self, ttl_seconds: float = 300.0, max_entries: int = 256):
        self.ttl = ttl_seconds
        self.max = max_entries
        self._store: dict[str, _Entry] = {}
        self._lock = Lock()

    @staticmethod
    def key(*parts: Any) -> str:
        h = hashlib.sha256()
        for p in parts:
            h.update(repr(p).encode())
            h.update(b"\x00")
        return h.hexdigest()

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None or time.monotonic() >= entry.expires_at:
                return None
            return entry.value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if len(self._store) >= self.max:
                oldest = min(self._store, key=lambda k: self._store[k].expires_at)
                self._store.pop(oldest, None)
            self._store[key] = _Entry(value=value, expires_at=time.monotonic() + self.ttl)
```

**Cache Key Design:**
```python
def cache_key(prompt: str, system: str | None, provider: str | None,
              variant: str | None, model: str | None, max_tokens: int,
              temperature: float) -> str:
    return TTLCache.key("complete", prompt, system, provider, variant,
                        model, max_tokens, temperature)
```

**When to Cache:**
- `temperature = 0`: Deterministic outputs, cache aggressively
- `temperature > 0`: Non-deterministic, cache rarely
- Repeated identical prompts in dev loops

### 4.2 Cost Tracking

#### 4.2.1 Ledger Design

```python
PRICING: dict[str, tuple[float, float]] = {
    "MiniMax-M2": (0.30, 1.20),
    "MiniMax-M2.7": (0.30, 1.20),
    "kimi-k2-turbo-preview": (0.60, 2.50),
    "_default": (1.00, 3.00),
}

def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    in_rate, out_rate = PRICING.get(model, PRICING["_default"])
    return (input_tokens * in_rate + output_tokens * out_rate) / 1_000_000
```

#### 4.2.2 JSONL Ledger with Monthly Aggregation

```python
class Ledger:
    """Append-only JSONL ledger with monthly cap enforcement."""

    def __init__(self, path: Path, cap_usd: float | None = None):
        self.path = path
        self.cap_usd = cap_usd
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, provider: str, model: str,
               input_tokens: int, output_tokens: int) -> LedgerEntry:
        entry = LedgerEntry(
            ts=datetime.now(UTC).isoformat(timespec="seconds"),
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=estimate_cost_usd(model, input_tokens, output_tokens),
        )
        with self._lock, self.path.open("a") as f:
            f.write(json.dumps(asdict(entry)) + "\n")
        return entry

    def month_total(self, month: str | None = None) -> MonthAggregate:
        # Read and aggregate entries for month
        ...

    def check_cap(self) -> None:
        if self.cap_usd is None:
            return
        agg = self.month_total()
        if agg.total_usd >= self.cap_usd:
            raise RuntimeError(f"Monthly cap ${self.cap_usd:.2f} exceeded")
```

### 4.3 Cost Optimization Strategies

| Strategy | Savings | Trade-off | Implementation |
|----------|---------|-----------|----------------|
| Temperature=0 caching | 30-50% | Less creative outputs | TTLCache with SHA256 keys |
| Provider selection | 20-40% | Latency variation | Auto-select cheapest available |
| Model variant | 10-30% | Quality variation | Use "highspeed" variants |
| Batch requests | 15-25% | Complexity | Queue and batch prompts |
| Context compression | 10-20% | Fidelity loss | Truncate/ summarize context |

## 5. Claude Code Integration Patterns

### 5.1 Subagent Architecture

```
Claude Code (main)
    │
    ├── [Agent: haiku-subagent] ──► cheap-llm.complete() ──► Minimax
    │
    ├── [Agent: summarizer] ──► cheap-llm.complete() ──► Kimi
    │
    └── [Agent: code-gen] ──► cheap-llm.complete() ──► Fireworks
```

**Agent Configuration Example:**
```markdown
<!-- ~/.claude/agents/cheap-reasoner.md -->

You are a cheap reasoning subagent. Use the `cheap_llm.complete` MCP tool
for all reasoning tasks instead of thinking inline.

When to use:
- Summarization tasks
- Simple code generation
- Test case creation
- Documentation formatting
- Extraction tasks

When NOT to use:
- Complex architectural decisions
- Multi-step reasoning requiring deep context
- Tasks requiring Claude's full capabilities

Cost awareness: Each call costs ~$0.001-0.005. Be efficient.
```

### 5.2 Traffic Separation

**Why Not Intercept Haiku OAuth?**
- Anthropic actively detects 3rd-party clients replaying tokens
- Account action risk is medium-high
- Violates Terms of Service

**The MCP Solution:**
- Claude Code uses own traffic to Anthropic (Haiku)
- Subagents route through cheap-llm-mcp
- Clean separation: Claude's intelligence + cheap inference
- No token replay risk

### 5.3 Prompt Engineering for Cheap Models

```python
# System prompt optimization for cost/quality balance
SYSTEM_PROMPT = """You are a concise coding assistant. Follow these rules:
1. Provide short, direct answers
2. Include only necessary code
3. Use bullet points over paragraphs
4. Example-focused explanations
5. No preamble or postamble
"""
```

**Optimization Techniques:**
- Shorter prompts = lower input token cost
- Explicit length constraints (`max_tokens=500`)
- Structured outputs to reduce retry rates
- Temperature tuning for consistency

## 6. Alternative Solutions Analysis

### 6.1 Direct API Integration

**Pros:**
- No additional abstraction layer
- Full control over requests
- No dependency on routing logic

**Cons:**
- No automatic failover
- Manual provider switching
- Repeated connection setup

### 6.2 API Gateway Solutions

| Product | Pros | Cons | Cost |
|---------|------|------|------|
| Portkey | Observability, routing | Additional service | $100+/month |
| Helicone | Logging, analytics | No routing | $100+/month |
| Custom | Full control | Development cost | Variable |

### 6.3 Other MCP Servers

| Server | Focus | Provider Support | Cost Model |
|--------|-------|------------------|------------|
| cheap-llm-mcp | Cheap inference | Minimax, Kimi, Fireworks | Open source |
| nunchuck | Tool orchestration | Multiple | Free |
| gitmcp | Git operations | GitHub, GitLab | Free |
| brave-search | Web search | Brave API | API cost |

## 7. Future Directions

### 7.1 Emerging Providers

**Expected Additions:**
- Groq: Specialized inference hardware, potentially lower costs
- Perplexity: Real-time knowledge integration
- Replicate: Hosted open models variety

**Context Window Expansion:**
- Minimax expanding to 32K
- Competition driving longer contexts at lower prices

### 7.2 Protocol Evolution

**MCP Protocol Updates:**
- Streaming tool responses (SSE)
- Bidirectional communication
- Enhanced authentication flows

**Potential Enhancements:**
```python
# Future: Streaming tool response
@mcp.tool(streaming=True)
async def complete_streaming(prompt: str) -> AsyncIterator[dict]:
    async for chunk in router.stream(prompt):
        yield {"type": "content", "delta": chunk}
```

### 7.3 Advanced Routing

**Semantic Routing:**
```python
class SemanticRouter:
    async def route(self, prompt: str) -> str:
        embedding = await self.get_embedding(prompt)
        # Route based on prompt characteristics
        if self.is_code_heavy(prompt):
            return "minimax"  # Strong code performance
        elif self.is_long_context(prompt):
            return "kimi"     # 128K context
        return "auto"        # Default routing
```

**Cost-Aware Routing:**
```python
class CostAwareRouter:
    async def select_provider(self, requirements: Requirements) -> str:
        providers = await self.get_health_status()
        costs = self.estimate_costs(requirements)

        # Balance cost vs. latency vs. quality
        scores = {
            name: self.score(name, costs[name], providers[name], requirements)
            for name in providers
        }
        return max(scores, key=scores.get)
```

## 8. Architectural Decisions for cheap-llm-mcp

### 8.1 Current Implementation Summary

| Component | Implementation | Rationale |
|-----------|----------------|------------|
| Protocol | FastMCP | Python-native, stdio support |
| Transport | stdio | Claude Code compatibility |
| Routing | Priority fallback | Simple, predictable |
| Caching | TTL cache | Dev loop optimization |
| Cost tracking | JSONL ledger | Append-only, auditable |
| Retry | Exponential backoff + jitter | Standard pattern |

### 8.2 Design Principles

1. **OpenAI compatibility first**: Standard API shapes ease integration
2. **Failover by default**: No single point of failure
3. **Observable costs**: Every request logged with cost estimate
4. **Idempotent where possible**: Temperature=0 caching
5. **Simple configuration**: TOML-based, sensible defaults

### 8.3 Trade-offs Made

| Decision | Trade-off | Justification |
|----------|-----------|---------------|
| No persistent connection pool | Connection overhead | Simpler implementation, less state |
| Thread-safe cache | Some concurrency overhead | Safe for sync/async mixing |
| JSONL ledger | Query performance | Append-only simplicity |
| No streaming in MCP tools | Latency on long outputs | MCP protocol limitations |

## 9. References

1. Anthropic MCP Protocol Specification
2. Minimax API Documentation
3. Moonshot AI API Reference
4. Fireworks.ai Documentation
5. FastMCP Library Documentation
6. httpx Async HTTP Client
7. OpenAI Chat Completions API

---

*Document Version: 1.0*
*Last Updated: 2026-05-02*
*Project: cheap-llm-mcp*
*Authors: Phenotype Architecture Team*
