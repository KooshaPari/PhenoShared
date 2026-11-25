# Authoritative workflow management

Phinbox management state lives in `<inbox-root>/management.sqlite`. The inbox daemon observes durable `inbox/` and `answered/` files every two seconds, including changes from other processes. It never writes permission responses. Management status is independent from `RequestState` and `ElicitResponse`.

`phinbox --inbox-dir ROOT manage list` and `manage get ITEM_ID` read that same store. `manage create --from-file item.json` accepts the public management Item shape; `manage apply --from-file command.json` accepts a Command containing stable event_id, item_id, expected_revision, trusted local actor and action. Creation preserves the exact original text. Conflicting IDs/revisions and mutated event replays fail. Exactly repeated commands return their original receipt. `manage events --after SEQUENCE` exports ordered canonical events for cockpit/ledger consumers. No external cockpit integration is implied by providing this contract.

Example command (a management acknowledgement, never a permission answer):

```json
{
  "event_id": "native:ack:42",
  "item_id": "inbox:request-42",
  "expected_revision": 1,
  "actor": "local-operator",
  "action": {"kind": "ack"}
}
```

Supported actions: ack, assign (value=principal), defer, close, set_status, set_lane and set_eta. Status values: open, running, waiting, deferred, partial, blocked and closed. Closed items are immutable. Ack records receipt; assign sets assignee/running; defer changes scheduling; close ends the management item. None authorizes, answers, cancels or resumes the source permission request. An explicit answer remains in the existing harness/elicitation decision path.

The existing inbox page links `/management`, a read-only HTML view of status/lane/ETA/assignee/revision. Local `GET /api/management` reads the same store as JSON. Mutations are not exposed on this unauthenticated HTTP surface. Native Swift management widgets and external cockpit binding are not implemented by this view. Their supported contract is the shared ledger reader/command API, not another copied state file.

## Safe inbox bootstrap

`manage observe` performs one reconciliation pass. The daemon repeats it. Requests become stable `inbox:REQUEST_ID` items and retain their full authored PromptSpec JSON, including approval command/files/effects. All elicitation response values and notes are excluded. Secret-urgency and secret-field prompts receive a visible blocked/restricted pointer item with a generic safe title; their authored content is not exported. This explicit restriction preserves discoverability without claiming verbatim publication of secret content. Authored prompt content itself must be suitable for the management channel; a non-secret label cannot automatically detect arbitrary sensitive prose. Native direct-created management items are explicit user inputs.

Observed answered/cancelled/expired source requests close their management items. Closing a management item does not close or answer its source request. The observer never revives a manually closed item. Missing/corrupt source entries are not interpreted as completed requests.

## Transactions, recovery and source authority

SQLite IMMEDIATE transactions atomically commit revision changes, canonical events, command receipts and outbox effects across processes. Every effect has item/revision correlation. Thread binding is immutable and unique; a conflicting remap fails. A durable projection checkpoint records externally ambiguous operations. A SQLite expiring lease elects a projection worker; transport must acquire/renew it before effects and use bounded requests. Completion is not acknowledged in the outbox until required remote status edits and thread archive/lock succeed.

Management JSON files are not an additional write authority. Discord is a projection plus authenticated command input; native/CLI actions and Discord interactions converge through the same CAS reducer. Remote edits/tags alone are not canonical commands. Existing ledger/cockpit users can consume ordered `manage events` or the Store Rust API; an adapter must preserve sequence/revision and deduplicate, rather than independently patching copies.

The original pending/answered JSON store predates this ledger and retains its own transition behavior. This feature observes it read-only; it does not claim to fix unrelated concurrent permission-answer races. No management command calls inbox finalization.

## Discord integration boundary

The user-authorized destination is guild `1558641659778961432`, forum `1560878303286534164`, using the existing Instinct application/bot `1558640911297028147`. Resolve existing open/running/waiting/deferred/partial/blocked forum tag IDs, validate identity/permissions, and reuse the existing persona/bindings authority. Missing authority configuration fails closed; never infer a persona from display names or create a competing persona registry.

A native adapter must implement the desk helper's Discord payload protocol through authenticated HTTPS/Gateway, not shell out to `/root/discord-wake/dsend.py`. No live installation/posting is performed by this source change. Run `phinbox --inbox-dir ROOT manage discord --config CONFIG.json --once` for one explicit projection pass, or omit `--once` for the elected Gateway plus durable projection service. The Gateway owns its distinct receiver lease; projection owns a separate lease. Only start this service after replacing/routing the existing desk listener as the designated receiver. Credentials are read only at the adapter boundary and never copied into management items, receipts, errors or outbox bodies. A bot acknowledgement does not grant operator authority.

The complete original item must survive in the starter message or its complete UTF-8 attachment; title limits may shorten only the title. Status is edited in place. Before terminal archive/lock, final status must be committed and projected. Unknown create outcomes require correlation reconciliation rather than blind thread creation retries. Discord action ingress must validate application/guild/thread/message/persona/actor, reject replay/stale revision, and retain explicit permission noninterference.


## Configuration, verification and handoff

Copy `examples/discord-management.json` to an operator-owned private configuration path. This sample is intentionally NOT activation-ready: empty user/role allowlists fail closed, persona_reference must point to the accepted existing persona/binding authority, and receiver_owner remains unconfigured. Fill approved actor IDs, reference the actual existing binding artifact, preserve existing bot identity/credential path, validate board metadata, and explicitly elect receiver_owner=phinbox only after coordinating replacement/routing of the old desk listener. No credential is embedded in the sample. The inspected relay mail identity map is NOT Discord persona authorization; the complete existing persona schema remains unlocated and must not be invented as implemented.

The six sample tag IDs were observed read-only on the exact authorized forum; startup checks their current names/IDs and destination before projecting. No tags/forums/bots are created by configuration. Already existing human-seeded desk asks are not silently rebound to arbitrary native item IDs; bootstrap needs a real item correlation, otherwise create recovery uses only the adapter's exact owned correlation marker and refuses ambiguity.

Run `python3.13 crates/phinbox/scripts/test-discord-management.py` from this repository. It reconstructs a standalone package manifest from current declared dependencies, compiles the actual production library and CLI, and runs ONLY tests/discord_*.rs against local fixtures/loopback HTTP/WebSocket services. It does not launch the real bot, change global config or resolve/build all unrelated workspace members. The isolated dependency cone is a focused acceptance witness, not a full root-workspace CI result. Source/CLI paths are referenced directly, not patched copies.

Deployment/live profile remains separate: existing Instinct bot permissions, actual persona authority, receiver replacement, live create/update/interaction/close and installed daemon configuration have not been accepted by offline tests. No permission approval behavior is enabled by this adapter. Native Swift's management rendering and any external cockpit require their own consumer integration; the shipped local web/JSON/CLI views expose the actual shared ledger today.
