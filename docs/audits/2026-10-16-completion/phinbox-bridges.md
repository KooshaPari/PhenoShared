# Phinbox: preserved native implementation and bridge contract

Phinbox extends harness guardrails/permissions/hooks/HITL/escalation. It must preserve the originating harness's authority, rather than become an independent approval policy that bypasses it. This is the operator's intended outcome; complete end-to-end wiring is not established by source presence.

## Source map

| Surface | Owner/source | Actual source behavior |
|---|---|---|
| Inbox native app | Swift: [main.swift](../../../apps/phinbox-app/Sources/inbox-helper/main.swift), RootView, RowView, DetailView | Window, list, detail and form widgets; nine Swift files |
| Tray/application host | Rust: [bin_app/mod.rs](../../../crates/phinbox/src/bin_app/mod.rs), tray.rs | Daemon orchestration, NSStatusItem event loop, helper activation |
| Form widgets | Swift: [DetailViewFields.swift](../../../apps/phinbox-app/Sources/inbox-helper/DetailViewFields.swift) | Text/secret/long text/boolean/choice/integer/date-time |
| Core/schema | Rust: [spec/types.rs](../../../crates/phinbox/src/spec/types.rs), approval.rs | Typed request/response, rich approval details, defer affordance |
| Web/daemon | Rust: [HTTP handler](../../../crates/phinbox/src/inbox/daemon/http/mod.rs), views/html | Loopback inbox/forms and answer persistence |
| Popup | Rust macOS renderer -> system osascript | display dialog; README's linked NSPanel description is stale |
| Agent protocol | Rust mcp/router.rs | Single phinbox_mcp tool runs synchronous popup in blocking worker |

## Concrete gaps at frozen current main

| ID | Contract mismatch | Source evidence | Consequence / repair acceptance |
|---|---|---|---|
| P1 | Three queue conventions | bin_app/mod.rs:22-24,105-109; inbox/mod.rs:254-263; Swift InboxManager:19-21 | App defaults ~/.phinbox/Phinbox, CLI/Swift use Application Support. Resolve one daemon-discovered root; alternate root fixture must display same request |
| P2 | Query-only POST vs required body | Swift InboxManager:101-109; HTTP mod.rs:182-201; daemon/form/mod.rs:119-125 | Native submit lacks body confirm marker and fails. Send typed encoded body, prove accepted/invalid/duplicate outcomes |
| P3 | bool/default_value vs boolean/default | Swift Models.swift:32-64; Rust spec/types.rs:93-149 | Boolean unknown and defaults lost. Shared schema fixtures across native/web/MCP |
| P4 | Rich details and defer missing in Swift model | Models.swift:17-21,109-116; approval.rs:143-200 | Approval files/reason/effects/warnings cannot be relied on in native form. Render without information loss |
| P5 | Build lists stale after split | app build.sh:35-38; Sources/inbox-helper/build.sh:21-27 | Main script compiles main only; nested script omits two extensions. Compile all required sources, package exact outputs |
| P6 | Port hardcoded, passed URL ignored | InboxManager:103; bin_app/helper.rs:33-34; Swift main | Alternate live daemon port fails native submit. Pass endpoint through supported configuration contract |
| P7 | Cancel only clears selected | DetailView.swift:115-117 | No cancellation reaches agent. Distinguish dismiss/defer/decline and persist explicit outcome |
| P8 | Swift moves expired files separately | InboxManager:61-71; Rust inbox expiry/finalization | Two state writers can diverge. Daemon owns authoritative terminal transitions |
| P9 | Default artifacts omit tray | Cargo.toml:21-22,86-104 | Default MCP install is not native app installation. Explicit CLI/MCP/app distribution profiles and install proof |
| P10 | Installer/manifest drift | plugins/codex/install.sh:21-38; forgecode/install.sh:17-24 | Codex writes mcp.toml; Forge project .forgecode. Current global settings compatibility must be verified independently |

Native source arrived in local history at 33673213 (2026-09-15) and was not subsequently deleted in visible refs. Inherited model/build mismatches were already present. b215d543 (September 18) hardened HTTP body validation, exposing incompatibility with obsolete native query submissions; f0ad009d corrected Rust live URLs, leaving Swift unchanged. This is a compatibility-regression explanation supported by source; installed runtime reproduction remains required.

## Per-harness bridge status

| Harness | Confirmed in-repo extension | Not established / next contract |
|---|---|---|
| Codex | plugins/codex/{codex.toml,install.sh}, skill, generic MCP | Native permission approval interception/callback, config.toml registration, correlation and denial behavior |
| Forge | plugins/forgecode/{plugin.toml,install.sh}, skill, generic MCP | Current ~/.forge loader support and native hook/approval return path |
| Jcode | Generic CLI/MCP and ToolApproval data helpers | No dedicated Jcode plugin directory; current native hook lifecycle/permissions bridge UNKNOWN |
| KCode | Generic CLI/MCP API can be consumed | Separate profile/state and native decision callback UNKNOWN; never assume Jcode config propagates |
| Other supplied plugin profiles | Claude Code, Cursor, agent_cli, Droid, Kilo manifests/installers | Manifest existence is not installed compatibility or automatic permission interception |

Bounded search of hooks/dotfiles/config/scripts and engine/policy/plugin Rust sources found no direct Phinbox integration references outside its own crate; this does not prove absence in external harness repositories or user global configuration.

## Proposed request/decision lifecycle

    harness emits pending operation (policy remains in harness)
      -> adapter preserves request/session/operation identity
      -> daemon queues validated prompt and provenance
      -> native/web/popup renders the same material decision
      -> explicit answer/decline/defer/cancel/expiry
      -> atomic terminal transition or continued pending
      -> adapter delivers typed result to exact waiting harness
      -> harness revalidates scope and decides execution

Required fields: harness/profile/session/request ID, operation digest, scope/resource, reason, affected files/effects, urgency, policy source, expiry, supported decision choices, callback ownership and provenance. This is a proposal, not a newly implemented wire schema. Reuse current PromptSpec/DetailsSpec/ToolApproval and existing harness hook APIs before adding transport.

Negative controls: wrong session, changed operation, duplicate answer, expired request, denied/revoked permission, daemon restart, helper missing, port/root override, malformed form, disconnected callback, unsupported field, and two clients answering concurrently. No timeout/dismissal/defer can silently approve. Secret answers need actual storage/logging review; SecureField masking alone is not confidentiality proof. Harnesses stay independently configurable. Qualify supported profiles separately and preserve screenshots/recording prohibition.
