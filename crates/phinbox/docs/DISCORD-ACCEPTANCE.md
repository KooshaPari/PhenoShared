# Discord management slice: implementation and acceptance receipt

Base source: `1448514e5692d8de6e40be8c7b67c6b5168f9fe2` on KooshaPari/PhenoShared main. Candidate branch: `feat/phinbox-discord-management-20261016`. This is a bounded management feature, not completion of the entire Phinbox product.

## Implemented user outcome

One canonical management item produces a correlated forum thread using the existing Instinct identity and authorized forum. The starter retains full original UTF-8 content plus complete workflow metadata attachments, updates status in place, and exposes acknowledgement/assignment/defer/close/status controls. Authenticated Gateway interactions validate configured actors and item revision before committing through the same SQLite ledger as native CLI/web readers. Terminal starter status/disabled controls precede thread archive/lock. Management actions never provide an elicitation answer or harness permission.

Local authority is `<inbox-root>/management.sqlite`, with transactional CAS revisions, immutable thread mapping, receipts/events/outbox and expiring elected workers. Protected projection writes verify the still-held owner inside the write transaction; per-operation renewal never silently reacquires a replaced token. Ambiguous external creation has a durable pre-POST marker and reconciles exact owned correlation before retry; no blind duplicate POST. The existing daemon observes durable inbox changes across processes and publishes a read-only management view/API. Native CLI and Discord use the same Store.

Secret-field/secret-urgency requests receive a visible blocked restricted pointer, not a silently omitted item. Authored secret content and all answer values are excluded. Ordinary prompts retain the complete authored PromptSpec including approval details. This restriction is explicit; not every original is publicly exported verbatim.

## Research and design decisions

- Existing Phinbox JSON outcomes remain authoritative for elicitation; six workflow lanes cannot be mapped onto permission answers.
- Process-local InboxChangeBus is insufficient for cross-process durability, so the observer scans durable native files; no broad rewrite of legacy answer persistence.
- Existing generic webhook is raw TCP and lacks Discord protocol/recovery; native reqwest HTTPS and Gateway WebSocket code implement the inspected desk payload contract instead of shelling out to Python.
- Existing desk listener has no demonstrated authenticated Phinbox callback. Activation requires explicit election/replacement/routing of that receiver, not two competing management consumers.
- Existing asks-board metadata and exact six tag IDs are validated. No new bot/forum/tag/persona roster is created. The complete external persona/bindings resolver remains unlocated; configuration is an explicit owner-supplied provenance/allowlist contract, not a claim that external identity services were integrated.
- Source is split into management and Discord modules under 500 lines; shared composition files have one integration owner. Existing dirty source and audit PR #447 are preserved.

## Actual focused checks

Worker-run, actual production source, SDKROOT MacOSX26, deployment target15.0 and CARGO_BUILD_JOBS=1. No real Discord network traffic or native application launch. Local HTTP/WebSocket fixtures are test infrastructure, not a substitute production adapter.

| Gate | Actual result |
|---|---|
| Actions/authentication/replay/denial tests | 3 passed |
| Authority/inbox observer/secret restrictions/full details tests | 6 passed |
| CAS/receipt/collision/concurrent Store tests | 6 passed |
| Durable outbox/thread map/lease/fencing/restart tests | 7 passed |
| Native HTTP/multipart/status ordering/failure/ambiguous creation tests | 6 passed |
| Native Gateway HELLO/IDENTIFY/heartbeat/interaction ACK/CAS/fatal close | 1 passed |
| Total new integration tests | 29 passed, none ignored |
| Actual production CLI `cargo check --bin phinbox` in isolated package harness | passed; reported elapsed18m37s |
| Final adapter source after strict atomic renewal, HTTP6 + Gateway1 | passed |
| Documentation/harness syntax and staged whitespace | checked during publication |

The focused harness references actual library/CLI/test source paths and reconstructs declared dependencies outside the unrelated249-member workspace. Repeat with `python3.13 crates/phinbox/scripts/test-discord-management.py`. This does not claim root-workspace Cargo.lock/CI convergence, MCP/tray feature builds, coverage floors, a release or installed runtime acceptance. No known-green unrelated suite rerun.

## Remaining acceptance and limitations

No installation, service replacement, live post, live interaction, credential migration, forum mutation or deployed verification occurred. Current effective bot permissions, actual persona authority, lifecycle of the old desk listener and real destination end-to-end acceptance remain external deployment gates. The safe example intentionally refuses activation until real authorized users/roles and provenance are supplied.

Legacy native Swift schema/root/port/build/submission defects documented in audit PR #447 remain open. The new web/JSON/CLI management view works through the same store; it does not repair Swift's elicitation UI or implement an external cockpit client. Existing permission JSON concurrency issues remain separate from the transactional management ledger. Above8MiB projection explicitly refuses and retains the original locally; remote attachment size/profile acceptance remains a live gate. Full-product completion and lifecycle decisions remain separate follow-up work.
