# helios-cli — Architecture

_Last updated: 2026-06-30 (v37 audit overhaul)_

## Repository identity

helios-cli is a **hard fork** of the OpenAI Codex CLI (upstream severed 2026-06-30).
The `codex-rs/` and `codex-cli/` trees are retained as **vendored reference material**
and are **excluded from the Cargo workspace** (`exclude = ["codex-rs", ...]` in the
root `Cargo.toml`). They are not built, tested, or linted by CI. Do not add them back
to the workspace without an explicit decision record.

## Cargo workspace layout

```
helios-cli/                  Workspace root (resolver = "2")
├── crates/
│   ├── helios_config        Centralised workspace config (types, defaults)
│   ├── harness_interfaces   Core trait definitions shared across harness crates
│   ├── harness_schema       Zod-equivalent: serde types for run manifests
│   ├── harness_spec         FR/spec tracing and assertion helpers
│   ├── harness_utils        Shared utilities (IO, error, path helpers)
│   ├── harness_queue        Bounded async task queue
│   ├── harness_runner       Task executor — drives a single harness run
│   ├── harness_orchestrator Multi-agent orchestration layer
│   ├── harness_scaling      Concurrency / parallelism controls
│   ├── harness_cache        Result caching (on-disk + in-memory)
│   ├── harness_checkpoint   Mid-run state snapshots and resume
│   ├── harness_rollback     Checkpoint-based rollback primitives
│   ├── harness_discoverer   Spec / test discovery (file-system walker)
│   ├── harness_normalizer   Input normalisation before dispatch
│   ├── harness_elicitation  Interactive elicitation stubs (A2A / MCP)
│   ├── harness_teammates    Agent team registry and comms
│   ├── harness_verify       Post-run result verification
│   ├── harness_recorder     KLA — CLI recording / screenshot tool (binary: kla)
│   ├── forge3_client        HTTP client for the forge3 multi-agent daemon
│   ├── pheno-plugin         Plugin trait and lifecycle manager
│   ├── plugin-arch          Architectural plug-in registry
│   └── arch_test            Architecture rule tests (dependency constraints)
│
├── codex-rs/                EXCLUDED — vendored Codex Rust workspace (read-only ref)
├── codex-cli/               EXCLUDED — vendored Codex Node CLI (read-only ref)
└── helios-rs/               EXCLUDED — vendored helios-rs workspace (read-only ref)
```

## Crate dependency rules

1. `harness_interfaces` has **no** internal deps — it is the leaf all other crates may import.
2. `helios_config` may import `harness_interfaces` only.
3. Utility crates (`harness_utils`, `harness_schema`, `harness_spec`) may import
   `harness_interfaces` and `helios_config`.
4. Feature crates import utility crates; **never** import peer feature crates directly —
   use `harness_interfaces` traits.
5. `harness_orchestrator` is the only crate that may depend on multiple feature crates.
6. `arch_test` enforces these rules via `cargo_metadata` + cycle checks; CI runs it.

## Public re-export policy

Each crate exposes a single `pub use` prelude block in `src/lib.rs`. External crates
import from the crate root, never from internal modules. Internal modules use
`pub(crate)` or `pub(super)` unless the item is part of the crate's public contract.

## Persistence and state strategy

helios-cli is **intentionally stateless between runs** at the library level. Checkpoint
and rollback state is written to `$HELIOS_DATA_DIR` (default `~/.helios/`) as
newline-delimited JSON files, one per run ID. No SQL migrations or embedded database.
If a daemon-style persistence model is needed in future, the decision belongs in an ADR.

## Async and concurrency

- Async runtime: `tokio` (`full` feature), one runtime per process.
- Cross-task communication: `tokio::sync::mpsc` and `Semaphore`. Hand-rolled bounded
  queues (`harness_queue`) exist but must be migrated to `tokio::sync::mpsc` (audit
  finding L4 — tracked in `docs/adrs/`).
- Cancellation: `tokio_util::CancellationToken` is the standard (not ad-hoc `AtomicBool`).
- Lock ordering: document in code with `// Lock order: A < B` comments when two mutexes
  are held simultaneously. No transitive lock cycles allowed.

## Observability

Structured logging uses `tracing` + `tracing-subscriber` with `EnvFilter` (controlled
by `RUST_LOG`). The `log` bridge (`tracing-log`) forwards legacy `log::` macros into the
same subscriber. OTel export and Prometheus metrics are not yet wired (audit finding L5).

## codex-rs exclusion rationale

The upstream `codex-rs/` Cargo workspace is a separate root with its own lockfile.
Including it as a workspace member caused:

- Phantom dependency surface inflating audit scores.
- CI build failures when expected source crates were absent.
- Confusing `cargo test --workspace` output mixing upstream and helios tests.

Decision (2026-06-30): exclude and treat as non-buildable vendored reference material
until a deliberate decision to fork specific crates is made and documented in an ADR.
