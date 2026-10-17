# Focused Discord management test receipts

Observed 2026-10-17 Pacific. Test lane owns only `tests/discord_*.rs` and this fixture directory. Production source fixes belong to their respective owners.

## Actual observed results

| Target | Result | Evidence boundary |
|---|---:|---|
| discord_actions | 3 passed | Native command authorization/correlation; not arbitrary JSON authentication |
| discord_authority | 6 passed | Permission JSON unchanged; real child test process observed; restricted secret pointer; complete safe authored spec |
| discord_ledger | 6 passed | Real SQLite CAS, full-command replay/collision, concurrent stores, terminal immutability |
| discord_recovery | 7 passed | Retry/checkpoint persistence, immutable mapping, lease exclusion/expiry/replaced-owner fenced writes |
| discord_http existing cases | 5 passed | Real loopback REST requests/multipart, exact large original + long lane/ETA attachments, in-place starter edits, terminal disable-before-lock, 500 leaves pending, redacted 403, bounded 429 |
| discord_http ambiguous create | 1 passed | Server checks checkpoint BEFORE POST; unusable success response -> owned marker reconciliation; exactly one create POST |
| Actual phinbox CLI | cargo check passed, exit 0 | Absolute production `src/cli/mod.rs`, default/MCP/tray features disabled in focused harness; Finished dev profile in 18m37s |
| discord_gateway | 1 passed, exit 0 | Real loopback WS HELLO/IDENTIFY/heartbeat/interaction -> native HTTP type-6 ACK -> Store CAS -> permanent-close stop; adapter-owned final retry finished in 0.09s |

Final total: **29 unique tests passed**, no ignored assertions (actions 3 + authority 6 + ledger 6 + recovery 7 + HTTP 6 + Gateway 1). The adapter owner refreshed HTTP 6/6 after atomic renewal and ran the single Gateway retry; those repeated receipts are not counted twice. Original HTTP fixture required a macOS accepted-socket blocking-mode fix; Gateway fixture required lexical MutexGuard scope for Send. These were fixture corrections, not production assertion exemptions.

## Invocation and provenance

Temporary focused harness `/tmp/phinbox-discord-focused/Cargo.toml` resolved nonoptional dependency versions/features from the actual root and Phinbox manifests. It referenced the absolute SAME production library and actual test files, with optional MCP/tray/observability disabled. It did not replace production modules with stubs. The actual CLI binary was added explicitly for its check.

Environment: `SDKROOT=/Library/Developer/CommandLineTools/SDKs/MacOSX26.sdk`, `MACOSX_DEPLOYMENT_TARGET=15.0`, `CARGO_BUILD_JOBS=1`.

- Initial compile exposed nine production SQL u64 trait errors; checked signed-boundary conversions fixed them.
- Next compile exposed three production timestamp i64/u64 mismatches; adapter owner corrected them.
- First successful test run: actions 3/3, authority 6/6. HTTP fixture initially failed WouldBlock on macOS; accepted sockets now explicitly blocking.
- Focused retry: HTTP 5/5, ledger 6/6, recovery 7/7. Existing green actions/authority suites were not redundantly rerun.
- Ambiguous-create exact binary test: `1 passed; 0 failed; 5 filtered out; finished in 5.78s`.
- Actual CLI: `cargo check --manifest-path /tmp/phinbox-discord-focused/Cargo.toml --bin phinbox`, exit 0.

A project-tracked reproducer now exists at `scripts/test-discord-management.py`; production source versions may advance after a given receipt. Later atomic-renewal/fencing changes received independent source review; do not retroactively label an older test binary a new exact-source full-suite pass. Current Gateway/CLI compilation is a separate receipt.

## Independent findings and addressed boundaries

The review found real defects before source-owner fixes: invalid colon-containing canonical item IDs, clipped/absent verbatim payload, SQL integer incompatibility, timestamp mismatches, unfenced transport writes, and Gateway starvation by inline projection. Owners added reversible correlation, full safe spec/original/workflow attachments, signed SQL conversion, fenced durable writes and atomic renewal, and independently spawned Gateway/projector tasks.

Normal inbox daemon auto-observes source into management SQLite. Native Discord service is explicitly opt-in through `phinbox --inbox-dir ROOT manage discord --config CONFIG [--once]`; live receiver ownership/configuration must be resolved before activation. This audit did not start a live bot, change production bindings, read real credentials, publish Discord messages, launch UI, capture screens, or run the huge workspace suite. Native tray/app and real Discord authorization/device acceptance remain outside these local fake-network results.

## Final bounded gate

Adapter-owner final direct receipts: HTTP `6 passed; 0 failed`, Gateway `1 passed; 0 failed; finished in 0.09s`, both exit 0 after atomic-renewal source fixes. Same-source isolated actual CLI check previously exited 0. Source review confirms fenced checkpoint/bind/ack writes, atomic owner/expiry renewal and independently supervised Gateway/projector. Feature publication is owned by the core lane; this test lane stops writes after this receipt.
