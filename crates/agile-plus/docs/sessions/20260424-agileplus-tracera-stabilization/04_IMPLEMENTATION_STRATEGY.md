# Implementation Strategy

## Stabilization Order

1. Keep AgilePlus green locally.
2. Make spec truth enforceable.
3. Prove projections.
4. Define Tracera import.
5. Decompose large modules.
6. Revisit microfrontends only after the runtime contract is stable.

## Runtime Strategy

Use `.agileplus/runtime/local-ports.env` as the local runtime port source.
`scripts/resolve-local-ports.sh` writes that file. `scripts/dev-up.sh` then
passes it into `process-compose.yml`.

The Plane vendored checkout lives at `.agileplus/plane`.

- API: `.agileplus/plane/apps/api`
- Web: `.agileplus/plane/apps/web`

## Frontend Strategy

The Rust dashboard is the live local UI. The React/Vite dashboard scaffold
should not be treated as runnable until it has a manifest, TS config, app
entrypoints, and build/test gates.

Tracera owns the cloud product frontend. AgilePlus should export methodology
state and local dashboard views, not duplicate the cloud tracker product.

`crates/agileplus-dashboard/web` is currently classified as an incomplete
scaffold. It has component source and historical Phase 2 documents, but it is
missing `package.json`, lockfile, `tsconfig.json`, `index.html`, and app
entrypoints. Do not advertise its npm commands as runnable until those files
exist and the package has passing build/test gates.

The topology gate is `agileplus frontend audit --strict`. It treats `docs/` as
the active docs frontend because it has a `package.json`, and it treats
`crates/agileplus-dashboard/web` as a preserved scaffold only because that
directory carries `FRONTEND_STATUS.md` with `Status: scaffold`.

## Governance Strategy

Add validators before broad migrations:

- spec root parity
- command-doc parity
- FR-to-test traceability
- projection mapping existence
- frontend runtime topology

State-transition commands should fail by default unless the operator uses an
explicit escape hatch. Allowed escape hatches must leave evidence in the report,
artifact metadata, or audit transition label. Silent skips are not acceptable for
governance gates.

Current command policy:

- `plan --force`: audited forced planning transition.
- `validate --force`: audited forced validation transition.
- `validate --skip-policies`: validation report and audit label record policy
  evaluation was skipped.
- custom validation policies: fail as unsupported until a real executor exists.
- unsupported evidence thresholds: fail closed.
- `EvidencePresent` policies: inspect stored FR evidence.
- `ship --skip-validate`: shipped metadata and audit label record validation
  was bypassed.
- ship branch merge errors: hard failure.
- ship cleanup warnings: non-blocking, but recorded in shipped metadata.

## Spec Migration Strategy

Use `.agileplus/specs` as the active spec root and keep legacy `kitty-specs`
content as preservation/source evidence. For DB-backed slugs missing from the
canonical root, copy the matching `kitty-specs/<slug>` directory into
`.agileplus/specs/<slug>`. For canonical directories not present in the local
AgilePlus DB, move them to `kitty-specs/<slug>` instead of deleting them.

The migration gate is:

```bash
cargo run -q -p agileplus-cli -- --db .agileplus/agileplus.db specs audit --strict
```

## Projection Strategy

Keep legacy `OutboundSync` methods as compatibility wrappers for callers that
only need Plane IDs. Use storage-aware free functions for production projection:

- `push_feature` writes `entity_type = "feature"`
- `push_work_package` writes `entity_type = "work_package"`
- module and cycle functions keep `entity_type = "module"` and `"cycle"`

CLI paths call environment-gated runtime helpers. If Plane env vars are absent,
the helpers no-op; if present, feature and work-package mappings are created
before module/cycle assignment links are pushed.

## SQLite Decomposition Strategy

Keep `crates/agileplus-sqlite/src/lib.rs` as the crate facade and route all
implementation through focused private modules:

- `src/lib/adapter.rs`: `SqliteStorageAdapter` construction and connection
  access helpers.
- `src/lib/storage_port.rs`: `StoragePort` implementation.
- `src/lib/content_storage.rs`: `ContentStoragePort` implementation.
- `src/event_store.rs`: `EventStore` implementation.
- `src/lib/tests/*`: split storage adapter tests by concern.

The public crate surface stays `agileplus_sqlite::SqliteStorageAdapter` plus
public `migrations`, `rebuild`, and `repository` modules for existing callers
and benchmarks.

## Dashboard Route Decomposition Strategy

Keep `crates/agileplus-dashboard/src/routes.rs` as the router facade and public
re-export surface. Route implementations live under `src/routes/` by concern:

- `agents.rs`: agent activity and agent JSON endpoints.
- `dashboard.rs`: dashboard page, kanban, health panel, project switcher.
- `feature.rs`: feature detail, work-package list, events, media.
- `evidence.rs`: evidence bundle loading, previews, generation, JSON.
- `pages.rs`: root/home/features/events/hub/time/static page handlers.
- `services.rs`: service restart/config/toggle routes.
- `settings.rs`: Plane, agent, service, and dashboard settings forms.
- `helpers.rs` and `types.rs`: shared view helpers, forms, and JSON/config
  types.

This keeps the active Rust dashboard as the local frontend while avoiding a
single oversized route module.
