# agent-comms runtime

Zero-dependency (Node 20+) runtime for the job-cockpit agent-comms bridge: a
**recipient/persona-to-pane mapping layer** and a **loopback receiver** that wakes a
Herdr pane when a message arrives for a mapped recipient.

This is the runtime half. It consumes a mapping; it does **not** create mail routing. No
DNS, email addresses, provider routes, aliases, or credentials are provisioned by this code.

## What exists

```
agent-comms/
  config/recipient-map.json         recipient local part / persona -> Herdr pane ID (operator editable)
  receiver/src/mapping.js           normalization + resolution of recipient/persona -> pane
  receiver/src/receipt.js           THE PhenoBot wire contract (personas, receipt id, ack shape)
  receiver/src/herdr.js             the pane "waker": path-walks to a pane, no absolute focus verb
  receiver/src/server.js            loopback HTTP receiver (POST /wake), bearer-token gated
  receiver/src/store.js             durable append-only JSONL receipts + seen-receipt idempotency index
  receiver/src/index.js             env-driven entrypoint (config, wiring, isEntrypoint guard)
  receiver/test/*.test.js           node:test suite, injected fake herdr runner (no process spawn)
  launchd/install.sh                install / uninstall / status / restart the supervisor
  launchd/com.example.agent-comms-wake.plist   supervisor template (no credential in it)
  scripts/live-bridge-check.mjs     LIVE end-to-end exercise against the real herdr CLI
```

## The producer, and the contract it demands

The only real producer of wake requests is **PhenoBot's agent bridge**. Its client
(`httpWakeAdapter`, PhenoBot `src/bridges/inbox.ts`) POSTs a full **Receipt** and accepts
the wake **only** when the reply is HTTP 200 with a body of exactly:

```json
{ "status": "awakened", "receiptId": "<the receipt id it sent>" }
```

A 202 means "accepted, protocol pending" and is explicitly **not** a wake. Any other
status or body is a failed wake, and PhenoBot **retains the receipt for replay**. The
contract is mirrored in `receiver/src/receipt.js`, which is the single place it is
defined, so the receiver cannot drift from the producer.

The wake is keyed by the receipt's **`agent`** (a PhenoBot persona: `jcode`, `Codex`,
`Instinct`, ...), not by an email address. The map carries both namespaces, so one table
serves both legs. The email-leg local part and the persona namespace cannot collide: a
persona name never contains `@`.

## How it works

1. PhenoBot `POST /wake` with `Authorization: Bearer $WAKE_RECEIVER_TOKEN`, an
   `idempotency-key` header, and a JSON Receipt body.
2. The receiver validates the receipt against the same invariants PhenoBot enforces
   (hex-64 id, known persona, required fields). A body PhenoBot could never have
   persisted is rejected before any pane is touched.
3. It looks the **persona** up in the map. No binding means an **honest failure** — a
   persona with no pane never fakes success, and the reply is NOT an `awakened` ack, so
   the producer keeps the receipt and replays it.
4. With a binding, the **waker** reaches the bound pane by a **path walk**, because herdr has
   no absolute "focus pane `<ID>`" verb: focus the workspace, focus the tab, then step to it.
5. Every "focused" claim is gated on per-pane sources only: `herdr pane get <target>`
   (authoritative for that pane) cross-checked against `herdr pane list` (authoritative
   machine-wide). The walk is seeded from the machine-wide focused pane, never from
   `pane edges --current` (which reports the attached UI tab, not programmatic focus).
6. The outcome is recorded as a durable JSONL receipt, and only a real wake is answered
   with `200 {status:"awakened", receiptId}`.

The older local-only shape (`{ "recipient": "civis@example.com" }` in,
`{ woke, detail }` out) is still accepted so a curl probe or a local script keeps
working. It is **not** what the bridge producer uses.

## Idempotent replay

PhenoBot retains a receipt it considers undelivered and re-POSTs it. Without a durable
record of what was already delivered, every replay would walk to the pane again and wake
it again, which duplicates the agent's activation instead of retrying a failed one.

The receiver keeps a durable index (`seen.jsonl`, next to `receipts.jsonl`) keyed by the
receipt id, with **three** states. The interesting one is `pending`, the state that makes a
crash safe.

| Recorded state | Meaning | Answer to a replay |
|---|---|---|
| `delivered` | the pane was raised and that fact reached the disk | `200 {status:"awakened", receiptId}`, **no** pane walk, **no** second receipt line |
| `failed` | a known attempt did not raise the pane | **retried**, because that is exactly what the producer is asking for |
| `pending` | an intent was recorded, outcome unknown (in flight now, or the process died) | `409 {status:"uncertain", code:"uncertain-outcome"}`: **fail closed**, no wake, no delivery claim |
| absent | never attempted here | first attempt |

A **concurrent** duplicate in the same process (the first request is still walking) is
answered `503 {"status":"failed","detail":"duplicate in flight"}`, which the producer treats
as a failed wake and replays later. A duplicate of a delivered receipt does **not** consume
the rate-limit budget. Concurrent requests for *different* receipt ids proceed in parallel.

### Write ordering, and what a crash leaves behind

Every write in `store.js` is `open(O_APPEND)` + `write` + **`fsync`** + `close`, and every
write **throws** on failure. `appendFileSync` alone would return with the bytes still in the
page cache, so a power loss could erase a `pending` line and the next replay would wake the
pane a second time.

Two boundary rules go with that:

- **the file is created and the directory fsynced** on first use, and again after every
  compaction rename. Without it a power loss can leave the data on disk but the name gone,
  which reads as "no index at all" and re-opens every receipt for replay;
- **every record starts on its own line**. If the file does not end in a newline (hand edit,
  or a writer that died mid-line) the next append inserts one first. Otherwise the new,
  perfectly valid record would splice onto the damaged line and become unreadable too.

The protocol writes the index **twice**:

1. **durable intent** (`pending`) *before* the pane is walked. If this write fails the wake
   is refused with `500 {"code":"intent-not-durable"}` and no pane is touched.
2. **durable outcome** (`delivered` or `failed`) *before* the reply is sent, evidence
   (`receipts.jsonl`) first and index second. If either write fails the reply is
   `500 {"code":"outcome-not-durable"}` and **delivery is not claimed**, even though the
   waker returned success. The index is left at `pending`, so later replays fail closed
   instead of waking the pane again.

Crash windows, in order:

| Crash point | Durable state | Next replay |
|---|---|---|
| before the intent | nothing | treated as a first attempt (nothing happened) |
| between intent and outcome | `pending` | `409 uncertain`, no wake |
| after the outcome | `delivered` / `failed` | the normal rule for that state |

### Resolving an uncertain receipt

An uncertain receipt needs a human decision, because only a human can tell whether the pane
was actually raised. The last line for an id wins on load, so resolve it by appending the
outcome you have verified:

```bash
printf '{"id":"<receipt-id>","status":"delivered","ts":"%s"}\n' "$(date -u +%FT%TZ)" \
  >> "$WAKE_RECEIVER_STATE/seen.jsonl"      # or "failed" to allow a retry
```

Restart the receiver afterwards so the process reloads the index. Use `failed` only if you
are confident the pane was not raised; `delivered` acknowledges the producer without a
second wake.

### A corrupt index refuses to start

`seen.jsonl` is loaded **strictly**. An unparsable line, a non-object record, or a record
without a valid `id`/`status` makes startup fail with `seen-index-corrupt` naming the line
number, and the receiver exits non-zero before it can bind a port. It does not skip the line.

That is deliberate: a skipped line is a skipped transition. It could be the `delivered` of a
receipt that then wakes again, or the `pending` of an attempt whose outcome is unknown. A
receiver that refuses to start is strictly safer than one that wakes panes on a fabricated
clean slate. The error message carries no file content.

To recover, inspect the named line, then either truncate it or restore the record:

```bash
sed -n '3p' "$WAKE_RECEIVER_STATE/seen.jsonl"        # look at it before touching anything
sed -i '' '3d' "$WAKE_RECEIVER_STATE/seen.jsonl"     # macOS; drop only the damaged line
```

### The bound never discards an unknown outcome

The index is capped at 10,000 entries. Compaction keeps **every** `pending` entry regardless
of age, and gives the remaining slots to the newest settled (`delivered`/`failed`) entries.
Evicting a `pending` entry would convert an unknown outcome into "never attempted", which is
exactly the state that permits a second wake.

If unresolved receipts fill the whole budget, the receiver stops accepting new ids and
answers `503 {"code":"index-at-capacity"}` without waking anything. Transitions of ids that
are already recorded still work. Resolve the pendings (see above) to clear it.

### Receipt-id integrity

PhenoBot derives the id as `sha256("<agent>:<messageId>:sha256(content)")` (a content-bound
id). The receiver re-derives it:

- an id that does not match its own `agent`/`messageId`/`content` is refused `400
  {"code":"receipt-id-mismatch"}`;
- the same mismatched id for a receipt **already on record** is refused `409
  {"code":"receipt-id-collision"}`, because two different receipts would otherwise share one
  idempotency record.

Content is folded in so an amended message gets its own receipt: the producer can send the
same `messageId` with corrected content, and the receiver will not answer with the outcome
recorded for the old body. A replay of unchanged content still resolves to the same id.
PhenoBot's older `sha256(agent:messageId)` ids no longer match and are refused.

Duplicate ids under identical fields are not collisions: they are replays.

### Scope and guarantees (read this before relying on it)

This is **at-most-once-wake with at-least-once producer retries**, not exactly-once delivery.
Concretely:

- Dedupe is **per process**. The in-memory map and the in-flight set serialise duplicates
  inside ONE receiver. There is no lock file and no cross-process coordination: two receiver
  processes sharing `WAKE_RECEIVER_STATE` would each keep their own view and could both walk
  the same pane. Run one.
- The index is load-once and append-only. A change made to the file by another process while
  this one is running is not observed until restart.
- A wake whose outcome cannot be recorded is reported as a failure, not as delivery. The
  producer may then replay, and the replay will be refused as uncertain. That is deliberate:
  refusing is safe, claiming delivery is not.
- Resolution is manual (see above). There is no automatic reconciliation and the receiver
  never retries an uncertain receipt on its own.
- The index constructor is strict. Any corrupt line stops the process, so a damaged file
  needs an operator before the bridge can wake anything again.
- `createReceiver` requires a seen index. There is no idempotency bypass: a receiver that
  cannot dedupe refuses to be constructed rather than silently waking every replay.
- `fsync` is not free: measured ~370 ms per append on the macOS dev host (APFS). A wake costs
  two or three appends, so an individual wake can take ~1 s. That is the price of the
  crash-safety above, and it is far below the rate of real bridge messages.
- The index is size-bounded at 10,000 entries; the oldest *settled* entries are compacted
  away, so a settled receipt older than that is no longer deduped. `receipts.jsonl` remains
  the append-only evidence of every actual wake attempt.
- Directory fsync is best effort: some platforms refuse to fsync a directory, and that
  refusal is swallowed rather than failing a write that already succeeded.

The index stores `{ id, status, ts, attempted_at, attempts, exhausted }` (lease metadata
for the pending state). It never stores message `content`, the bearer token, or any other body.
`attempted_at`/`attempts`/`exhausted` track lease-based attempts (30s lease, 3-attempt budget).

## Configuration (env only)

| Env var | Required | Default | Meaning |
|---|---|---|---|
| `WAKE_RECEIVER_TOKEN` | yes | — | Bearer token the sender must present. Never logged, never written, never in a URL. |
| `WAKE_RECEIVER_PORT` | no | `3211` | Loopback port (1-65535). The host is always `127.0.0.1`. |
| `WAKE_RECEIVER_STATE` | no | `receiver/state/receipts` | Durable receipt root. |
| `WAKE_RECEIVER_DRY_RUN` | no | unset | Set to `"1"` to prove transport without ever moving a pane. |
| `WAKE_RECEIVER_MAX_PER_MINUTE` | no | `30` | Accepted wake attempts per minute (`0` disables), matching the facade's rate-limit shape. |
| `WAKE_RECEIVER_MAP_JSON` | no | unset | Inline `recipient/persona -> pane` JSON, overriding the file. |
| `WAKE_RECEIVER_MAP_FILE` | no | `config/recipient-map.json` | Path to the editable mapping file. |

## The mapping

`config/recipient-map.json` maps either a recipient **local part** (before `@`,
case-insensitive) or a **PhenoBot persona name** to a Herdr pane ID, or to
`{ "paneId": "...", "label": "...", "agent": "..." }` for a binding with fallback match
hints. The email-leg default is derived from `docs/agent-comms/EMAIL-ROUTES-PROPOSAL.md`;
the persona leg is derived from the live `herdr agent list`. The domain is never used
for routing.

Only personas with a **live, evidenced** pane are bound. A persona whose pane does not
exist right now is deliberately left unbound, because a wrong binding would wake the
wrong agent.

The map is also the **write scope**: a request can only ever wake a pane the operator
explicitly mapped, so there is no path to an arbitrary pane.

### Handle validation (no argument injection)

Every value the waker hands to `herdr` is checked against a narrow allowlist before it
becomes an argv token — see `receiver/src/cli-args.js`.

`execFile` is spawned **without a shell**, so a value here cannot start a shell command.
That class of bug is already closed by the spawn itself. What is *not* closed is
**argument injection**: herdr parses the raw argv we build, so a handle of `--json` or
`-h` is read as a **flag**, not a pane name. The command would silently change meaning
and the waker would walk toward whatever the flag selected.

So the rule is **refuse, never escape or repair**. Herdr ids are machine-generated handles
(`w7:p1Q`, `w8:pN`, `wA:p8`); no legitimate id needs a leading dash, a space, or a shell
metacharacter. An allowlist that must start alphanumeric makes flag injection
structurally impossible — `-` can never be the first character.

This applies to every handle the waker touches, from either untrusted-ish source: the
JSON herdr emits (`pane list`, `pane get`, `pane edges --current`, `pane neighbor`) and
the operator's recipient map, which is a plain editable JSON document.

A rejected value **fails the wake honestly** — `{ woke: false, detail }` — rather than
being passed through. That is the invariant the whole receiver is built around: never
report a wake that was not independently confirmed. A pane entry with a malformed
`pane_id` is *dropped* rather than repaired, so the waker reports "no pane matched" and
the operator can act on it, instead of navigating somewhere the handle may have pointed.

## Run (local, dry-run first)

```bash
WAKE_RECEIVER_TOKEN='<a placeholder, set your own>' \
WAKE_RECEIVER_DRY_RUN=1 \
node agent-comms/receiver/src/index.js
```

A failed bind (port in use, no permission) exits non-zero and prints the reason. It never
exits 0 silently.

## Run as a supervised service (the bridge actually running)

The receiver is only part of the bridge if something supervises it. The launcher lives
in `agent-comms/launchd/`.

```bash
# 1. One-time: the token lives OUTSIDE the repo, in a 0600 env file.
mkdir -p ~/.config/agent-comms && chmod 700 ~/.config/agent-comms
printf 'WAKE_RECEIVER_TOKEN=<generated>\n' > ~/.config/agent-comms/wake-receiver.env
chmod 600 ~/.config/agent-comms/wake-receiver.env

# 2. Install and load the launchd job.
agent-comms/launchd/install.sh install
agent-comms/launchd/install.sh status
```

The installer refuses to install a job whose entrypoint is missing, and refuses to load a
plist that does not parse — a job that silently never runs is the worst outcome.

### Point the producer at the receiver

PhenoBot reads the wake URL and token per persona from the environment:

```
BRIDGE_WAKE_URL_<PERSONA>=http://127.0.0.1:3211/wake
BRIDGE_TOKEN_<PERSONA>=<the same value as WAKE_RECEIVER_TOKEN>
```

`<PERSONA>` is the uppercased persona name (`JCODE`, `CODEX`, `INSTINCT`, ...). The
persona must also have a binding in `config/recipient-map.json`, or the wake is
refused honestly and the receipt is retained for replay.

The PhenoBot bridge daemon is a **separate** repository and is not configured by this
one. Until `BRIDGE_WAKE_URL_*` / `BRIDGE_TOKEN_*` are set in the PhenoBot launchd
environment, the receiver is running but no producer reaches it.

## Tests

```bash
node --test agent-comms/receiver/test/
```

The unit tests inject an in-memory fake herdr runner so they never spawn a `herdr`
process, bind no port, and touch no real pane.

`receiver/test/contract.test.js` is the one that decides whether the bridge is *wired*:
it applies **the producer's own acceptance rule** to the receiver's reply, so a reply the
producer would reject fails the test.

## Live end-to-end exercise

```bash
node agent-comms/scripts/live-bridge-check.mjs --port 3219 --persona jcode
```

This starts the **real** receiver process, drives the **real** herdr path walk, POSTs a
**real** PhenoBot-shaped receipt, and prints the producer's verdict. Add `--dry-run` to
prove the transport without moving any pane.

Verified 2026-10-21 on the live host: the receiver bound a loopback port, walked to the
target pane in 3 steps, answered `200 {"status":"awakened","receiptId":"317c13c0…"}`,
the producer's rule reported `delivered`, and one durable receipt line was written.
