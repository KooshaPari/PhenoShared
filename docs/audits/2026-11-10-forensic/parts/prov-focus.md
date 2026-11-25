# Provenance: the `focus-*` crate family

**Measured: 43 dirs, not 31** (`ls -d crates/focus-* | wc -l`). `M` = explicitly in root `Cargo.toml`
`members` (**25 of 43**); the other 18 are unlisted but largely implicit as path-deps of members.
**UNKNOWN:** `cargo metadata --no-deps` would confirm implicit membership.

| Crate | M | Purpose (read from source where marked, else inferred from crate name) |
|---|---|---|
| focus-domain | M | Canonical domain entities/IDs/aggregates, no I/O (read) |
| focus-lang / focus-ir / focus-transpilers | - | "FocalPoint Language (FPL) - Starlark->IR Compiler" (read), IR types, transpilers |
| focus-rules / focus-rule-suggester / focus-eval | M/-/- | Rule DSL + eval + priority/cooldowns/explanations (read), suggester |
| focus-planning / focus-scheduler / focus-time | M/M/M | Task planning, scheduling, time primitives |
| focus-rituals / focus-coaching / focus-templates | M/M/M | Ritual + coaching behaviours, scaffolding templates |
| focus-rewards / focus-penalties / focus-policy / focus-audit | M/M/M/M | Reinforcement mechanics, enforcement policy, audit queries |
| focus-mascot / focus-ui / focus-cli / focus-mcp-server / focus-ffi / focus-webhook-server | M/M/- | Presentation (mascot, UI) + product entrypoints, all `[[bin]]` |
| focus-connectors / focus-connectors-mock-familycontrols | - | Connector trait layer + mock family |
| focus-events / focus-sync / focus-sync-store / focus-storage / focus-replay | M/M/-/-/- | Event bus, sync engine, persistence, replay |
| focus-crypto / focus-entitlements / focus-telemetry / focus-observability | M/M/-/M | Keychain crypto, licensing, telemetry/observability adapters |
| focus-always-on / focus-asset-fetcher / focus-backup / focus-demo-seed | M/-/-/- | Keep-alive runtime, asset fetch, backup, demo data |
| focus-icon-gen / focus-ci-watcher / focus-release-bot / focus-plugin-sdk | M/M/M/- | Build/release tooling, plugin SDK |

## Provenance
`git log --diff-filter=A -- 'crates/focus-*'` returns **exactly one commit**: `19f8e0ebe 2026-09-16
chore: extract 53 crates from FocalPoint (focus platform + connectors + infra)` - one bulk extraction
from a separate product. `README.md:202` corroborates (`| focus-* | 43 | FocalPoint productivity
platform |`). **No absorption manifest**: `docs/` has `absorbed-from-{dagrun,PhenoCompose,PhenoGoKit,
PhenoObservability,PhenoTooling}` but **no `absorbed-from-FocalPoint`**, and `docs/ABSORPTION_INDEX.md`
has no `focalpoint`/`focus-` entry.

## Consumers
9 outside crates depend on it and **all 9 are `connector-*`** from the same extraction:
`connector-{canvas,fitbit,gcal,github,linear,notion,readwise,strava,testkit}` -> `focus-connectors`,
`focus-events`, `focus-crypto`. **No** `phenotype-*`/`substrate-*`/`fabric-*` core crate depends on any
`focus-*`. Reverse: only 4 focus crates use a phenotype crate, all `phenotype-observably-macros`.

## Size
**43,601 Rust LOC** (`find crates/focus-*/src -name '*.rs' | cat | wc -l`). Largest: focus-ffi 3,437;
focus-cli 3,093; focus-ir 2,491; focus-eval 2,434; focus-lang 2,337. 7 crates declare `[[bin]]`: a runnable product, not a library-only pile.

## Verdict
**quarantine** - a real, self-consistent 43.6k-LOC productivity product with its own CLI/MCP/webhook
binaries, but an unreviewed bulk import with no absorption manifest, zero inbound dependency from any
Phenotype core crate, and wiring only to its own `connector-*` island. Strongest evidence: the single
bulk-extract commit `19f8e0ebe` plus the total absence of `docs/absorbed-from-FocalPoint` and of any
`focus-` reference in `docs/ABSORPTION_INDEX.md`. Quarantine (declare, fence, then decide
keep-as-product vs evict); `evict` is not yet justified (consumers exist, nothing is broken).
