# Functional Requirements — cheap-llm-mcp

## Routing & Provider Management

| FR-ID | Title | Status | Tests |
|-------|-------|--------|-------|
| FR-LLM-001 | Route completion requests to specified provider | Implemented | 1 |
| FR-LLM-002 | Use default provider when none specified | Implemented | 1 |
| FR-LLM-003 | Automatically fallback to next provider on failure | Implemented | 1 |
| FR-LLM-004 | Raise error when all providers fail | Implemented | 1 |
| FR-LLM-005 | List available providers and defaults | Implemented | 1 |

## Configuration & Initialization

| FR-ID | Title | Status | Tests |
|-------|-------|--------|-------|
| FR-LLM-010 | Load config from TOML file | Implemented | 1 |
| FR-LLM-011 | Use sensible defaults when no config file exists | Implemented | 1 |
| FR-LLM-012 | Validate required keys in provider config | Implemented | 1 |
| FR-LLM-013 | Reject unknown config keys | Implemented | 1 |
| FR-LLM-014 | Validate that providers is a TOML table | Implemented | 1 |

## Caching Layer

| FR-ID | Title | Status | Tests |
|-------|-------|--------|-------|
| FR-LLM-020 | Cache completion results with TTL | Implemented | 1 |
| FR-LLM-021 | Return None on cache miss after TTL expiry | Implemented | 1 |
| FR-LLM-022 | Evict oldest entry when cache reaches max size | Implemented | 1 |
| FR-LLM-023 | Generate stable cache keys from inputs | Implemented | 1 |
| FR-LLM-024 | Cache keys differ for different arguments | Implemented | 1 |

## Cost Tracking & Billing

| FR-ID | Title | Status | Tests |
|-------|-------|--------|-------|
| FR-LLM-030 | Estimate cost for known models | Implemented | 1 |
| FR-LLM-031 | Fall back to default cost for unknown models | Implemented | 1 |
| FR-LLM-032 | Record completion calls to ledger | Implemented | 1 |
| FR-LLM-033 | Aggregate monthly costs by provider | Implemented | 1 |
| FR-LLM-034 | Enforce monthly cost cap | Implemented | 1 |
| FR-LLM-035 | Allow no cost cap (None) | Implemented | 1 |

## Streaming & Request Handling

| FR-ID | Title | Status | Tests |
|-------|-------|--------|-------|
| FR-LLM-040 | Complete requests to OpenAI-compatible API | Implemented | 1 |
| FR-LLM-041 | Support model variant resolution | Implemented | 1 |
| FR-LLM-042 | Stream completion chunks via SSE | Implemented | 1 |
| FR-LLM-043 | Handle non-JSON lines in SSE streams | Implemented | 1 |
| FR-LLM-044 | Check provider health | Implemented | 1 |

## Retry & Resilience

| FR-ID | Title | Status | Tests |
|-------|-------|--------|-------|
| FR-LLM-050 | Retry on transient errors (5xx status) | Implemented | 1 |
| FR-LLM-051 | Not retry on client errors (4xx status) | Implemented | 1 |
| FR-LLM-052 | Eventually give up on persistent errors | Implemented | 1 |

## Logging & Observability

| FR-ID | Title | Status | Tests |
|-------|-------|--------|-------|
| FR-LLM-060 | Format logs as JSON | Implemented | 1 |
| FR-LLM-061 | Include request ID in logs | Implemented | 1 |
| FR-LLM-062 | Auto-generate request ID if not provided | Implemented | 1 |
| FR-LLM-063 | Restore outer request scope on exit | Implemented | 1 |

## Server & MCP Tools

| FR-ID | Title | Status | Tests |
|-------|-------|--------|-------|
| FR-LLM-070 | Expose providers tool listing defaults | Implemented | 1 |
| FR-LLM-071 | List all MCP tools (complete, stream, health, etc) | Implemented | 1 |
| FR-LLM-072 | Return cost summary from ledger | Implemented | 1 |

## Smoke Test

| FR-ID | Title | Status | Tests |
|-------|-------|--------|-------|
| FR-LLM-080 | Basic functionality sanity check | Implemented | 1 |
