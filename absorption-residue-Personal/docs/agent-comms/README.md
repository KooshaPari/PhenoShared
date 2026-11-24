# Agent communications

Two pieces live here:

- [`EMAIL-ROUTES-PROPOSAL.md`](EMAIL-ROUTES-PROPOSAL.md) — a **proposal** about per-pane
  email routing for active Herdr panes. It provisions nothing.
- [`agent-comms/`](../../agent-comms/) — the **runtime** that consumes a
  recipient/persona-to-pane mapping and wakes the mapped pane when a message arrives.

## Status

The runtime is real, tested, and **exercised live** (2026-10-21): a real receiver
process, a real Herdr path walk, a real producer-shaped receipt, and the producer's own
acceptance rule applied to the reply — verdict `delivered`.

The proposal is still a proposal.

**Nothing was provisioned.** Adding the runtime created no email address, DNS record,
provider route, alias, or credential. No existing route is altered. The runtime does not
create mail routing; it only maps a message that has already arrived to a Herdr pane.

## The producer, and the contract it demands

The only real producer of wake requests is **PhenoBot's agent bridge**. It POSTs a full
**Receipt** and accepts the wake **only** when the reply is HTTP 200 with a body of
exactly `{ "status": "awakened", "receiptId": "<the receipt id it sent>" }`. A 202 is
explicitly *not* a wake, and anything else makes the producer retain the receipt for
replay. The contract lives in one place,
[`agent-comms/receiver/src/receipt.js`](../../agent-comms/receiver/src/receipt.js), so the
receiver cannot drift from the producer.

## What the runtime does

`agent-comms/` (zero runtime dependencies, Node 20+) contains:

- a **mapping layer** (`agent-comms/config/recipient-map.json`, editable) from either a
  recipient local part (before `@`, case-insensitive) **or** a PhenoBot persona name to a
  Herdr pane ID. The two namespaces cannot collide, so one table serves both legs.
- a **loopback receiver** (`POST /wake`, `127.0.0.1` only) gated on a bearer token that is
  read from the environment and never logged, never written to disk, and never placed in a
  URL.
- a **per-minute rate limit** on accepted wake attempts, matching the facade's shape.
- a **Herdr waker** that reaches a pane by a path walk (there is no absolute "focus pane"
  verb) and claims focus only when `herdr pane get` and `herdr pane list` agree.
- **durable receipts** in append-only JSONL.
- a **crash-safe replay index** with three states: `delivered` (acknowledged, never
  re-woken), `failed` (retried), `pending` (outcome unknown, e.g. an interrupted attempt). A
  `pending` record is written *before* the pane is walked and is answered on replay with
  `409 {status:"uncertain"}`: the receiver neither claims delivery nor re-wakes. A success is
  only acknowledged after the outcome is fsynced, and a write failure is reported as
  `500 {code:"outcome-not-durable"}` instead of a false wake. Scope is honestly per-process:
  at-most-once wake with at-least-once producer retries, not exactly-once delivery. See
  `agent-comms/README.md` ("Idempotent replay", "Scope and guarantees").
- a **dry-run** mode that proves transport without ever moving a pane.
- an honest failure path: a persona with no pane binding never reports a fabricated wake.
  It answers `503 {status:"failed"}` — never `202`, never a fake `awakened` — so the
  producer keeps the receipt and replays it.
- a **launchd supervisor** (`agent-comms/launchd/`) so the receiver is actually running,
  not just present in the tree.

## What still needs the operator

The code is complete and proven; three steps need an operator credential and were
deliberately not performed here:

1. Write the bearer token to `~/.config/agent-comms/wake-receiver.env` (mode 0600).
2. `agent-comms/launchd/install.sh install` to load the supervisor.
3. Set `BRIDGE_WAKE_URL_<PERSONA>` / `BRIDGE_TOKEN_<PERSONA>` in the **PhenoBot** launchd
   environment and restart `studio.pheno.discord-bridge`. That is a separate repository.

Until step 3, the receiver runs but no producer reaches it.

See [`agent-comms/README.md`](../../agent-comms/README.md) for configuration and run
instructions, `agent-comms/receiver/test/` for the test suite, and
[`docs/sessions/20261021-bridge-runtime/`](../../docs/sessions/20261021-bridge-runtime/00_SESSION_OVERVIEW.md)
for the full gap analysis and evidence.
