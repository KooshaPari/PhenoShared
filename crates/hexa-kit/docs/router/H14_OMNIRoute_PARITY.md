# H14 — OmniRoute Feature Parity Design

Status: draft (Wave H14)
Owner: HexaKit + OmniRoute liaison
Refs: ADR-ECO-014, phenotype-gateway#16, HexaKit#291

## Scope

`crates/phenotype-router` (H11) ships **6 auto-combo variants** (Auto, Coding,
Fast, Cheap, Offline, Smart). OmniRoute ([`<REDACTED>/OmniRoute`]) defines
**18** total routing behaviors. This doc is the gap analysis and roadmap for
reaching feature parity in HexaKit.

## Current state (H11/H12)

| Variant    | Delegate target               | HTTP path            | Status |
|------------|-------------------------------|----------------------|--------|
| `auto`     | cliproxy-delegate-default     | `/v1/chat/completions` | spike  |
| `auto/coding` | cliproxy-delegate-quality  | `/v1/chat/completions` | spike  |
| `auto/fast`   | cliproxy-delegate-throughput | `/v1/chat/completions` | spike  |
| `auto/cheap`  | cliproxy-delegate-budget    | `/v1/chat/completions` | spike  |
| `auto/offline`| cliproxy-delegate-local     | `/v1/chat/completions` | spike  |
| `auto/smart`  | cliproxy-delegate-reasoning  | `/v1/chat/completions` | spike  |

5/5 unit tests pass; HTTP binary (H12) wires these through axum.

## OmniRoute behaviors — gap analysis

### Tier 1: must-have (H14 target)

| OmniRoute feature | HexaKit status | Notes |
|---|---|---|
| Model alias resolution (`gpt-4` → provider X) | **gap** | Wave H15+; needs vendor config table |
| Provider fallback chain | **gap** | H12 binary has single delegate target; needs retry middleware |
| Streaming SSE passthrough | **gap** | H12 returns `Json` only; needs `Sse` response |
| Token usage accounting | **gap** | Headers only; needs counter middleware |
| Request cancellation on client disconnect | **partial** | axum default; needs explicit handling |

### Tier 2: nice-to-have (post-H14)

| OmniRoute feature | HexaKit status | Notes |
|---|---|---|
| Per-tenant rate limiting | **gap** | Needs tenant extraction + Redis or in-memory token bucket |
| Cost ceiling per request | **gap** | Needs model-cost table + abort hook |
| Prompt caching (provider-agnostic) | **gap** | Provider-specific; needs adapter per cliproxy++ target |
| Image/vision routing | **gap** | Multimodal not in H11 surface |
| Tool/function-call routing | **gap** | Handled by cliproxy; no router-side logic needed |

### Tier 3: long-tail (post-OmniRoute v1)

| OmniRoute feature | HexaKit status | Notes |
|---|---|---|
| Speculative decoding (multi-model) | **gap** | Needs provider API extension |
| Embedding routing (`/v1/embeddings`) | **gap** | New endpoint, new delegate target |
| Audio routing (`/v1/audio/*`) | **gap** | New endpoint |
| Fine-tune routing (`/v1/fine_tuning/*`) | **gap** | New endpoint |
| Admin/replay routing | **gap** | Internal only |
| WebSocket upgrade | **gap** | axum supports; needs endpoint wiring |
| Auth/JWT validation | **gap** | Needs provider-aware JWT verifier |

## Proposed roadmap (post-H14)

1. **H14.1** — Streaming SSE passthrough + token accounting middleware
   (PR to HexaKit; adds `axum::response::sse` + `tower::limit` middleware).
2. **H14.2** — Provider fallback chain (retry middleware; config table).
3. **H14.3** — Model alias resolver (YAML/JSON config; hot-reload).
4. **H14.4** — Per-tenant rate limiting (in-memory token bucket first;
   Redis later if multi-instance).
5. **H14.5** — Vision + tool-call routing (new endpoints; cliproxy passthrough).

## Non-goals (explicit deferrals)

- **Prompt caching at router level** — provider-managed; cliproxy owns this.
- **Speculative decoding** — needs provider API extension; defer to OmniRoute v2.
- **Multi-region active-active** — out of scope until HexaKit hits
  production scale.

## Open questions

1. Should the alias resolver live in `phenotype-router` or in a new
   `phenotype-routing-config` crate?
2. Do we need a cliproxy++ extension for `LastKnownGoodProvider` (LKGP)
   stickiness, or is that router-side state?
3. Auth model — JWT only, or also API keys per provider?

## Acceptance criteria for H14 closeout

- All Tier 1 items shipped with unit + integration tests
- Open questions answered in ADR-ECO-015 (or successor)
- PRs merged to HexaKit `main`
- CI green on all 3 platforms