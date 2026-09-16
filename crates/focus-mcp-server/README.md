# focus-mcp-server

MCP (Model Context Protocol) server for FocalPoint. Exports tools and resources for Claude to read/write rules, audit logs, query wallet state, run manual syncs, and inspect scheduler decisions. Supports both stdio and SSE transports.

## Purpose

Enables AI agents (Claude and other MCP clients) to interact with FocalPoint core logic for autonomous rule authoring, state inspection, and diagnostics. Used for research, testing, and future AI-assisted rule generation workflows.

## Key Types

- `FocalPointToolsImpl` — implements MCP tools trait
- Tool definitions: `read_rule`, `write_rule`, `query_audit`, `run_sync`, `inspect_scheduler`
- Resource types: `rule://`, `audit://` URI schemes
- Stdio + SSE transport adapters

## Entry Points

- `run_stdio()` — start MCP server over stdin/stdout
- `run_sse()` — start MCP server over SSE HTTP
- Tool handlers accept structured inputs, return JSON responses

## Functional Requirements

- MCP tool and resource protocol compliance
- Deterministic state inspection (read-only for audit, queries)
- Write tools with validation (rule upsert, sync trigger)

## Consumers

- Claude and other AI agents via MCP
- CI/CD integration testing
- Admin tooling and diagnostics
