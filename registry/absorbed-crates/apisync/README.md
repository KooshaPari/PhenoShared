> [!WARNING]
> **SUPERSEDED 2026-06-19 — ARCHIVED**
> This repository has been superseded by the **`apikit` Rust crate lineage**, whose entire surface (REST, GraphQL, WebSocket adapters, application router, domain middleware, infrastructure logging, governance, ADRs, CI, tooling, and operational docs) has in turn been absorbed into [`KooshaPari/phenotype-tooling/docs/absorbed-from-apikit/`](https://github.com/KooshaPari/phenotype-tooling/tree/main/docs/absorbed-from-apikit).
>
> **Do not open new work, PRs, or clones here.** Read-only history is preserved; the canonical home of every artifact that ever lived in this repo is downstream of `apikit`.
> See [`UPSTREAM.md`](./UPSTREAM.md) for the full migration trail, and the [`CHANGELOG`](https://github.com/KooshaPari/phenotype-tooling/blob/main/docs/absorbed-from-apikit/CHANGELOG.md) of the absorbing collection for the dated absorption entry (2026-06-20).
>
> Per the Phenotype org-wide [GitHub archive policy](https://github.com/KooshaPari/phenotype-omlx/blob/main/docs/guides/GITHUB_ARCHIVE_POLICY.md), this remote is archived (read-only) and named in its original form (`Apisync`, not `zz-archive-Apisync`) only because the org-wide rename sweep is held until the central registry ticket closes; the repo is **not** an active development target.

# Apisync

![Status: superseded](https://img.shields.io/badge/status-superseded-red?style=flat-square)
![Migrated to: apikit → phenotype--tooling](https://img.shields.io/badge/migrated%20to-apikit%20%E2%86%92%20phenotype--tooling-blue?style=flat-square)
![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)

> **Universal API toolkit — REST, GraphQL, WebSocket adapters (Rust).**
>
> Original scaffold + governance for an async-first, hexagonal-architecture API
> toolkit. Source repo for the `apikit` crate lineage.

## Where the code lives now

The Apisync surface has migrated downstream along this chain:

```
KooshaPari/Apisync        ← you are here (archived, read-only)
        │
        │  extracted as v0.1.0 foundation → became `apikit`
        ▼
KooshaPari/apikit         (successor; also archived 2026-06-21)
        │
        │  governance + Rust source + CI + docs + ADRs absorbed
        ▼
KooshaPari/phenotype-tooling
  └─ docs/absorbed-from-apikit/
       ├─ README.md                                          (apikit entry point, "Migrated from Apisync")
       ├─ ABSORPTION.md                                      (deletion / absorption provenance)
       ├─ CHANGELOG.md                                       (dated absorption entry 2026-06-20)
       ├─ src/                                               (REST / GraphQL / WebSocket adapters)
       ├─ docs/governance/README.apisync.md                  (original Apisync README, preserved)
       ├─ docs/governance/{AGENTS,CLAUDE,ADR,STATUS,PLAN,
       │   PRD,SPEC,FUNCTIONAL_REQUIREMENTS,
       │   TEST_COVERAGE_MATRIX,CHANGELOG}.apisync.md
       ├─ docs/governance/adr/001..005-*.md                  (5 ADRs migrated verbatim)
       ├─ docs/sessions/{journeys,stories,traceability}/
       ├─ docs/research/SOTA.md
       └─ .github/workflows/*  +  repo-root tooling & governance files
```

If you came here looking for:

| You wanted | Go to |
| --- | --- |
| Live canonical source | [`phenotype-tooling/docs/absorbed-from-apikit/src/`](https://github.com/KooshaPari/phenotype-tooling/tree/main/docs/absorbed-from-apikit/src) |
| Original Apisync README (preserved verbatim) | [`phenotype-tooling/docs/absorbed-from-apikit/docs/governance/README.apisync.md`](https://github.com/KooshaPari/phenotype-tooling/blob/main/docs/absorbed-from-apikit/docs/governance/README.apisync.md) |
| Architecture decisions (ADRs 001–005) | [`phenotype-tooling/docs/absorbed-from-apikit/docs/governance/adr/`](https://github.com/KooshaPari/phenotype-tooling/tree/main/docs/absorbed-from-apikit/docs/governance/adr) |
| Spec / functional requirements / test matrix | `phenotype-tooling/docs/absorbed-from-apikit/docs/governance/{SPEC,FUNCTIONAL_REQUIREMENTS,TEST_COVERAGE_MATRIX}.apisync.md` |
| Plan / status / PRD / changelog | `phenotype-tooling/docs/absorbed-from-apikit/docs/governance/{PLAN,STATUS,PRD,CHANGELOG}.apisync.md` |
| SOTA research, journeys, stories | `phenotype-tooling/docs/absorbed-from-apikit/docs/{research,SOTA.md,sessions/{journeys,stories,traceability}}/` |
| HexaKit pattern lineage (uses Apisync ADRs as origin) | [`pheno/crates/hexa-kit/docs/adr/origin/`](https://github.com/KooshaPari/pheno/tree/main/crates/hexa-kit/docs/adr/origin) |
| Phenotype consumer (e.g. `phenotype-core` / `phenotype-gateway` workspaces) | pin to `KooshaPari/phenotype-types` main — see HexaKit #271 |

## Why this repo is archived

Apisync was a scaffold-stage API toolkit (35% complete at archive time; see the
preserved `STATUS.apisync.md`). During Wave 14 of the Phenotype registry
reconciliation (2026-06-17), the Apisync lineage was identified as a feeder
into the `apikit` crate, which was in turn a feeder into
`phenotype-tooling/docs/absorbed-from-apikit/`. Per the Phenotype **GITHUB_ARCHIVE_POLICY**:

1. All needed history/branches were mirrored into the canonical home.
2. The repo was archived (read-only) — *never* deleted (this org never
   `gh repo delete`s anything — see the policy doc).
3. Description set to `SUPERSEDED 2026-06-19 — migrated into apikit (absorbed into phenotype-tooling). Do not push here.`
4. This `README.md` was written to point at upstream.

A future org-wide rename will move this to `KooshaPari/zz-archive-Apisync`
to keep active-development repos sorted to the top of the org landing page;
until then, the remote URL stays unchanged for traceability with the
existing `phenotype-registry` introspections.

## Quick architectural snapshot (preserved)

Apisync used a hexagonal (`ports & adapters`) architecture with all
dependency arrows pointing inward:

```
adapters/  ──►  application/  ──►  domain/
   REST, GraphQL, WebSocket       transport-agnostic
   (hyper, async-graphql,         request/response types,
   tokio-tungstenite)              traits, business rules

infrastructure/  → injected, never imported by domain or application
   logging, configuration, telemetry
```

Crate feature surface at archive time:

- **REST router + handlers** (`hyper`-based)
- **GraphQL schema + resolvers** (`async-graphql`)
- **WebSocket connection management** (`tokio-tungstenite`)
- **Domain middleware** (auth, logging, CORS as `tower` layers)
- **Async-first runtime** (`tokio`)
- **Hexagonal separation** enforced by code review

The five ADRs that drove these choices are preserved verbatim in the
absorbing collection under `docs/governance/adr/001..005-*.md`:

| # | Decision |
| - | -------- |
| 001 | Hexagonal architecture (ports & adapters) |
| 002 | `hyper` over `axum` for the REST adapter |
| 003 | `async-graphql` for GraphQL server |
| 004 | `tokio-tungstenite` for WebSocket |
| 005 | `criterion` for benchmarking |

## Module layout (preserved)

```
src/
├── adapters/
│   ├── rest/         # hyper_server, mod.rs        → REST
│   ├── graphql/      # schema, server, mod.rs      → GraphQL
│   └── websocket/    # server, mod.rs              → WebSocket
├── application/      # handler, router, mod.rs
├── domain/           # middleware, mod.rs
├── infrastructure/   # logging, mod.rs
├── endpoints.rs
└── lib.rs            # crate root (apisync → apikit)
```

## Migrating off this repo

If your crate still pulls from `KooshaPari/Apisync` (e.g. as a `git`/`cargo`
dependency, or a `pheno` submodule — `pheno/.gitmodules` lists `Apisync`
alongside 80+ other KooshaPari submodules), repoint to:

- **Cargo**: `apikit = { git = "https://github.com/KooshaPari/phenotype-tooling" }`
  *(cargo sees the absorbed manifest; see `Cargo.toml.apisync-legacy` for the
  pre-absorption shape)*
- **Submodule**: replace `path = Apisync` / `url = https://github.com/KooshaPari/Apisync.git`
  with the consumer repo that should own the HTTP toolkit today (typically
  `phenotype-gateway` or a `pheno` workspace member; see Wave 14 task #1 of
  `docs/operations/wave14-gateway-ssot-2026-06-17.md` for the unblock that
  removed the Apisync submodule pin from `phenotype-core`).

If you need a CLI / quickstart that matches the **original** Apisync README,
the verbatim text is in
[`docs/governance/README.apisync.md`](https://github.com/KooshaPari/phenotype-tooling/blob/main/docs/absorbed-from-apikit/docs/governance/README.apisync.md).

## License

MIT — see [`LICENSE`](./LICENSE) (mirror-preserved).
