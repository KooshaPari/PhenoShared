Authored by Instinct.

# Cockpit state API

Cockpit project state lives in Cloudflare D1 (`cockpit-state`, binding `COCKPIT_DB` on the `job-cockpit` Pages project) and is changed by API calls, not PRs.

- Read: `GET /api/v1/projects`, `/api/v1/projects/:id`, `/api/v1/export.json`, `/api/v1/events`
- Write (bearer token only): `POST /api/v1/projects`, `PATCH /api/v1/projects/:id`, `DELETE /api/v1/projects/:id` (archive, never hard delete)
- Every write appends a row to `events` (actor, action, before, after).
- Tokens: one per agent, stored as sha256 in the `tokens` table. Raw tokens are never committed or sent in chat. Mint: `openssl rand -hex 32`, insert `sha256` for the actor, store the raw value in the agent's own secret store.
- Access: the UI stays behind Cloudflare Access. Bearer-token API access from agents needs a path rule for `/api/v1/*` (security change, owner decision, not applied by this PR).
- Seed: `node db/seed.mjs web/src/data/projects.json > db/seed.sql`, run against D1. `web/src/data/projects.json` stays as seed and fallback.
- CLI: `node tools/cockpit/cockpit.mjs list|get|set|add|archive|events`. MCP (stdio): `node tools/cockpit/mcp.mjs`.
