# Phinbox harness extension contracts

This packet extends supported harness interfaces while keeping native policy authoritative. Acknowledgment, assignment, defer, workflow close, missing input, timeout or failure never grants a permission. It changes no canonical harness configuration, server or hook chain.

## Actual discovery and current contracts

| Harness/profile | Verified interface and source | Supported integration in this change | Qualification boundary |
|---|---|---|---|
| Codex CLI0.163.0 | Installed native mcp add/get/remove; current config.toml; existing PermissionRequest hooks route Moshi/Xirp | Native MCP registration through explicit CODEX_HOME; typed documented PermissionRequest adapter | Actual isolated native registration/removal tested. Full agent hook execution/aggregation against this version remains unqualified. |
| Jcode installed | Native mcp list/test, existing ~/.jcode/mcp.json servers map | Isolated MCP profile with same explicit PHINBOX_INBOX_DIR | Actual native list and mcp test initialize the isolated server, enumerate phinbox_mcp and disconnect cleanly. No tool invocation or native permission callback was performed. |
| KCode installed | Current installed build has no mcp CLI subcommand. Actual reference source in local repos/jcode is KooshaPari/KCode, not the installed Jcode source | Independent KCode mcp.json servers map, separate receipt/profile; no assumed propagation | Source/config lifecycle qualification only; installed runtime MCP discovery remains UNKNOWN. |
| Forge/HeliosLite lineage | Source forge_domain::Env resolves project .mcp.json and user base .mcp.json; McpConfig uses mcpServers | Explicit isolated PROJECT file; preserves other servers/hook files | JSON lifecycle tested. Actual isolated CLI show returned a missing default provider/model diagnostic despite exit0; this is NOT a runtime pass. |

Reference-source facts are tied to the inspected source, not automatically to every installed binary. Jcode/KCode pre-tool gate source explicitly fails open on startup errors and timeout. It is unsuitable for an unattended human-wait permission gate without a stronger native contract. This change does not install such a gate or replace the existing tool-safety hook. Forge native permission callbacks were not established; generic MCP availability is the bounded supported extension.

## Native Codex permission adapter

The official generated input/output schemas define pending PermissionRequest input and a native hookSpecificOutput decision. The implemented source is src/harness/codex.rs. It validates the documented event, session/turn identity, supported mode and required fields; unknown fields fail closed. It persists the normal typed Boolean ToolApproval prompt to the same durable Phinbox queue, waits within a1-120second bound, then returns:

```json
{"hookSpecificOutput":{"hookEventName":"PermissionRequest","decision":{"behavior":"deny","message":"bounded reason"}}}
```

Only state Answered with a correlated, unchanged request/origin/spec and FieldValue::Boolean(true) can return allow. Text "true", false, cancellation, defer, expiry, management state or mismatched operation all return deny. Plan/dontAsk/bypassPermissions modes are refused. No transcript path is opened. Reserved native rewrite/interrupt fields are not emitted. The adapter receives a pending permission event; it does not create a policy exception or interpret an existing native denial as permission to retry.

    native pending PermissionRequest -> validated origin/session/turn
      -> ordinary Phinbox queue -> explicit typed answer
      -> correlated native allow/deny output -> harness policy/execution authority

The native CLI integration is registered by the shared composition owner; see its actual --help and execution receipt. Hook-process wait limits must exceed the chosen bound while preserving existing native denial/aggregation semantics. No auto-install writes hooks.json. Existing Moshi/Xirp chains are untouched; composing this opt-in bridge with them still requires a native acceptance witness. This source/protocol qualification does not imply such a witness occurred.

Primary references inspected 2026-10-17 (upstream main, not an asserted binary-version pin): [official input schema](https://github.com/openai/codex/blob/main/codex-rs/hooks/schema/generated/permission-request.command.input.schema.json), [official output schema](https://github.com/openai/codex/blob/main/codex-rs/hooks/schema/generated/permission-request.command.output.schema.json). Installed local CLI help and actual config registration were checked first. The schema bridge contains no copied implementation from another harness.

## Isolated registration and removal

All four wrappers use plugins/profile_install.py. Required --profile-dir and --inbox-dir are absolute. Dry-run is default and creates no files. --apply touches only that explicit isolated profile; canonical harness profiles, symlink escapes, unowned collisions, altered owned entries and cross-harness receipt reuse are rejected. Uninstall removes only the unchanged receipt-owned registration and preserves unrelated servers/hooks. Installer receipts contain only the managed Phinbox entry, not copies of unrelated credentials/configuration.

| Profile | Native configuration | Server launch |
|---|---|---|
| Codex | config.toml, edited by native codex mcp command with CODEX_HOME | phinbox-mcp; args[] |
| Jcode | mcp.json / servers | phinbox-mcp; args[] |
| KCode | independent mcp.json / servers | phinbox-mcp; args[] |
| Forge project | .mcp.json / mcpServers | phinbox-mcp; args[] |

Each managed entry passes PHINBOX_INBOX_DIR explicitly. MCP registration is not permission interception. Jcode and KCode keep independent profiles, receipts, state and executable bindings.

## Evidence and remaining obligations

`python3 crates/phinbox/tests/harness_profiles.py -v` executed seven meaningful installer tests, including the actual installed Codex CLI. All seven passed. Actual installed Jcode mcp list recognized the isolated entry; a separate mcp test connected to the installed Phinbox0.9.0 server, enumerated its one tool and disconnected cleanly. tests/harness_jcode_receipt.json records its binary hash and exact output; it is installed-artifact transport proof, not a claim that the moving candidate MCP binary was tested. The Forge diagnostic is preserved as an unqualified runtime path, not ignored because of exit0.

Rust tests/harness_codex.rs executed six passing tests against the actual bridge source against durable queue/finalize operations: explicit Boolean true, false/text/defer/cancel, changed request, malformed/unknown/native bypass-mode inputs, and proof that management close does not answer the permission. The sixth test starts the real isolated local daemon on an ephemeral loopback port and submits an explicit form body; the bridge returns native allow for that exact request. The initial fixture incorrectly expected303 rather than the actual successful302 redirect; the corrected fixture passed. The bridge source was directly included by the test because shared CLI/lib registration remained pending at this receipt. Native CLI dispatch and an actual Codex agent hook invocation are not claimed.

| Remaining accepted-intent obligation | Current disposition |
|---|---|
| Actual Codex agent pending event -> hook -> user -> final native execution | UNKNOWN; protocol/source checks are insufficient |
| Jcode safe native authority callback and timeout denial | Unestablished; inspected pre-tool failures are fail-open, so no human gate installed |
| KCode installed MCP tool discovery/use and isolated permission callback | UNKNOWN; source/file schema and fork separation only |
| Forge native runtime/provider initialization + MCP use | UNKNOWN; isolated diagnostic was not a success |
| Forge native permission callbacks | Unestablished; do not fabricate support |
| End-to-end native/web human acceptance and restart/recovery across harnesses | Separate full-product acceptance gates |

The complete original request remains locally durable; confidential real tool inputs require the actual supported privacy policy before mirroring to external management surfaces. All current tests use synthetic benign operations and isolated roots. No live tool permission, real LLM action, screenshot, recording, canonical config write or global process kill occurred.
