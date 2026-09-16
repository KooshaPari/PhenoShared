# focus-coaching

LLM provider trait and OpenAI-compatible HTTP client. Shapes POST `/chat/completions` calls with Bearer token authentication and simple messages array. No streaming or custom retries (defers to reqwest defaults).

## Purpose

Abstracts LLM providers so `focus-mascot` and `focus-rules` never import reqwest directly. Kill switch `FOCALPOINT_DISABLE_COACHING=1` short-circuits all calls to `Ok(None)` at the trait boundary for offline mode and testing. Built-in token-bucket rate limiter (10 calls/60s) with silent fallback on excess.

## Key Types

- `CoachingProvider` — trait: `complete()` for text generation with context
- `OpenAiCompatibleClient` — implements provider for OpenAI API + compatible services
- `RateLimitedProvider` — wraps any provider with token-bucket throttling
- `StubProvider` — no-op for offline/testing mode

## Entry Points

- `CoachingProvider::complete()` — request LLM completion
- `RateLimitedProvider::wrap()` — add rate limiting to any provider
- Environment check `FOCALPOINT_DISABLE_COACHING` at call site, not in impl

## Functional Requirements

- No direct reqwest imports in rule/mascot logic
- Rate limiting and kill-switch for resilience
- Graceful degradation (return `Ok(None)` instead of panic)

## Consumers

- `focus-mascot::MascotMachine` (bubble text generation)
- `focus-rituals` (morning brief and evening shutdown copy)
- `focus-rules` (action explanation prompts)
