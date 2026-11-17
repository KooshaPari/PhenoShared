# Legacy discovery semantic port

Source ref: `fix/forge-reasoning-retry-20260908`, also fork `repair/pr238-conversation-record-lints-20260904`.
Source tip: `39c597afda0e43b90ebef6b2476320570eef67f9` (PR267).
Port base: main `999b5c5046c047b7041fdfe0104e1e0135d3adb2`.
Disposition: PARTIAL SEMANTIC PORT, not whole-branch integration.

Recovered behavior: discovery of attached legacy conversations whose table predates workspace_id. The TEMP VIEW emits a non-null decoding placeholder and a separate provenance flag. Only unscoped attached rows receive that flag; modern legacy and local workspace-zero rows retain normal workspace filtering. No persisted schema change.

Source deviations: intentionally exclude blanket DELETE/prune and local-only FTS widening. Sentinel zero alone conflates real workspace-zero rows with missing-schema placeholders. Preserve main's schema-qualified pragma lookup and required intent_state/is_compressed defaults. Source macro/export/SQL helper are unnecessary for this scoped implementation. Other unmatched commits in source branch remain separately unclassified; source ref preserved.

Evidence: new regression fails on base (expected legacy ID, received empty list). After port full `cargo test -p forge_repo --lib`:414 passed,1 ignored. `cargo clippy -p forge_repo --lib --tests -- -D warnings` passes. Regression covers absent-workspace legacy discovery, local workspace-zero invisibility/deletion protection, modern legacy workspace-zero invisibility, and legacy row preservation. Existing split_db tests pass.

This is source consolidation, not release/install completion. No user database or installed binary changed.
