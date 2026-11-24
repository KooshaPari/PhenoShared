## Absorption history

PhenoShared (formerly **PhenoAI**) is a consolidation monorepo whose purpose is to be the durable home other Phenotype repos fold into — not a library, not a single app. HEAD `ad667428b`; 372 crate dirs, 283 unique declared workspace members, Rust + Go + JS/TS.

| Absorbed source | Date | Resulting path | Status |
|---|---|---|---|
| PhenoInfra | 2026-09-16 | `absorption/PhenoInfra/` (2537 files) | copied; source already archived |
| PhenoMLX-temp | 2026-09-16 | `absorption/PhenoMLX-temp/` (1349 files) | copied; **only** absorption tree wired into workspace (38 refs) |
| phenoDesign-visual-production-v2 | 2026-09-17 | `absorption/phenoDesign-visual-production-v2/` (180 files) | copied; source left **unarchived** pending operator confirmation |
| phenotype-canonicalization | 2026-09-17 | `absorption/phenotype-canonicalization/` (44 files) | copied whole; source unarchived |
| phenotype-cvp-audit-2026-09-14 | 2026-09-17 | `absorption/phenotype-cvp-audit-2026-09-14/` (7 files) | copied; source unarchived |
| PhenoCompose (PhenoTooling @ `2feccc2f`) | 2026-11-08 | `docs/absorbed-from-PhenoCompose/` (216 KB) | in-tree; `6fd2835e5` ported the 41 unabsorbed files |
| PhenoObservability (PhenoTooling) | 2026-11-08 | `docs/absorbed-from-PhenoObservability/` (1.1 MB, 140 files) | in-tree; `6e5fa283a` |
| PhenoTooling (bulk) | UNKNOWN | `docs/absorbed-from-PhenoTooling/` (**70 MB**) | largest absorbed payload outside `archives/` |
| PhenoGoKit (`go-sdk`) | UNKNOWN | `docs/absorbed-from-PhenoGoKit/` (1.5 MB) | GitHub repo **404**; recovered from a local clone whose origin is a local path |
| herdr plugins (jcode/forgecode/helioslite) | UNKNOWN | `absorption/herdr-{jcode,forgecode,helioslite}/` (8 files each) | in-tree, **0 workspace refs** |
| PhenoFabric | 2026-08-28 | `crates/fabric-*` (997 files, 118K lines) @ `365a3572` | absorbed into substrate |
| PhenoRegistry / PhenoInfra crates / PhenoGfx | UNKNOWN | `crates/phenotype-*` @ `f7ab4cdb` / `6c9b79ca` / `25c8dde1` | absorbed into substrate |

**Governance implication.** The manifest apparatus (`docs/absorbed-from/*/README*.md`, `docs/ABSORPTION_INDEX.md`, `docs/absorption/` with 33 per-project records) is the strongest artifact in the repo: every absorbed source carries repo, revision and date. But absorption is **staged, not landed**. The 2026-11-08 wrapup produced 18 remote `wrapup/*-20261108` branches (1–498 commits ahead) plus the consolidation branch `origin/integration/absorbed-20261109` (`45e7c8a6a`) — **all 19 UNMERGED** into `origin/HEAD` as of 2026-11-10. So the tree holds three archive generations (`_archived/`, `.archive/`, `archives/`) alongside `absorption/` (48 MB) and `docs/absorbed-from*` (~73 MB): ≈224 MB of forensic footprint with no single authoritative merge point. The "what is actually merged" answer is per-commit (`6e5fa283a`, `6fd2835e5`, `dee522c88`, `3b45203b0`), not per-branch. Two consequences for governance: (1) unarchived sources (phenoDesign, canonicalization, cvp-audit) are still-live upstreams and must not be deleted until the operator confirms; (2) the root manifest reaches into `absorption/PhenoMLX-temp/...`, so the build graph depends on content that is not on trunk.

## Ecosystem position

Registry id `pheno`, status `active`, tier `phenotype-framework`, architecture `layered` (`phenotype-registry/catalog/registry.yaml:635-640`). It is a first-class, actively tracked registry entry with a maintained commit ledger (`PhenoShared.story.md`, `PhenoShared.rollup.json`: 1965 commits, 285 merges, 29 active weeks, peak 2026-W42 = 429), not a passive inventory row.

| Consumer | Evidence | Verdict |
|---|---|---|
| Sibling Phenotype repos (`repos/*/Cargo.toml`) | bounded `rg` for `PhenoShared` and `KooshaPari/PhenoShared` matched only PhenoShared's own manifest | **No sibling repo declares PhenoShared as a Cargo dependency** (path or git) |
| Internal workspace crates | 372 crate dirs / 283 members consume each other | Intra-repo, not ecosystem consumption |
| External crates.io consumers | crates.io API returned HTTP 403 to the probe | UNKNOWN |
| npm/pypi/binary/MCP consumers | not probed | UNKNOWN |
| Release surface | only `promptscrape` v0.1.0–v0.1.2; 72 crate manifests set `publish = false` | No observable library-consumer surface |

**Dependencies (outbound).** Root `Cargo.toml` declares **no** `git =` source deps (`rg 'git = '` → 0 matches); per-member-crate outbound git deps were not exhaustively enumerated → UNKNOWN. The root manifest is 1028 lines and lists 372 member directories, including paths into `absorption/PhenoMLX-temp/...`.

**Org layer.** Tier `phenotype-framework` places PhenoShared in the shared substrate layer *beneath* product repos: `substrate-*` (dispatch spine, browser broker/CDP/MCP), `fabric-*` (execution/IO), `agileplus-*` (planning/sync), `connector-*`, plus `engine-spec` / `acceptance-contract` / `arch-test` / `phenotype-config-core`. It is a shared kernel **and** a consolidation hub, explicitly not a leaf library and not a user-facing product. Two competing self-descriptions coexist — `README.md:3` "container repository, not a single-purpose project" vs `PRD.md:3` "domain-agnostic, reusable infrastructure primitives … no inter-crate dependencies" — and the PRD claim contradicts the substrate spine's real dependency direction. ~60% of commits are agent/automation authored. GitHub: public, created 2026-04-03, last push 2026-11-10, ~256 MB, Rust, 0 stars, PR sequence up to **#828**, but only 4 releases (all `promptscrape`) — high churn, no release cadence.

## Contract and decision record

Three mutually unaware ADR stores: `docs/adr/` (90 files, singular), `docs/adrs/` (25, plural), `adrs/` at repo root (10, a third numbering series); copies also nested under `docs/atlas/adr`, `docs/phenotype-docset-v1.1/adr`, `docs/specs/pheno-specs/adrs`. No machine-readable index; only ~28 of the 90 expose a parseable `Status:` field, and prefix `0001` is used **4×** inside `docs/adr` (0002/0003/0004/0005/0006 3× each), so a bare id is unresolvable — always cite the slug. Rows below are verified titles/statuses/decision lines; the ADR id is reproduced as it appears on disk.

| id | title | status | decision |
|---|---|---|---|
| ADR-0001 | Record Architecture Decisions | Accepted | Use Nygard-style ADRs: numbered markdown under `docs/adr/`. |
| ADR 0001 | Define Phenotype Fabric as the execution/data/I-O substrate | Accepted | Fabric owns discovery, placement, residency, transport, I/O, surfaces, RT QoS — not product intent or session history. |
| ADR 0001 | Hybrid Compute Mesh (7 nodes) | Accepted | 7-node mesh: always-on cloud free-tier nodes plus a home desktop over a Tailscale control plane. |
| ADR-0002 | Hexagonal ports/adapters architecture | Accepted | Binding layout: core holds contracts, adapters plug engines/transports/stores; core never depends on an adapter. |
| ADR 0002 | One packaged product shell over modular adapters | Accepted | One installer/UI/CLI/API identity; capabilities are replaceable adapters with independent health and versioning. |
| ADR 0002 | OCI Ampere as Primary Backbone | Accepted | Two Oracle Cloud Ampere A1 Flex VMs host Forgejo, Woodpecker and Vaultwarden. |
| ADR 0003 | Use a PipeWire/JACK-inspired typed node-port-link graph | Accepted | Devices/resources/surfaces are typed nodes; links express intent, compiled routes express implementation. |
| ADR 0003 | Home Desktop as Heavy Runner | Accepted | Attach the home Mac to the tailnet as `home-mac`, a Woodpecker agent labeled `[self-hosted, heavy, home]`. |
| ADR-0004 | Atomic claim/lease for the single-instance guard | Accepted | `substrate-serve-lock` claims via SQLite + WAL. |
| ADR-0005 | SQLite as the default store | Accepted | Use `rusqlite` with the `bundled` feature. |
| ADR-0006 | Structured tracing via a `TracePort` | Accepted | Adopt a two-tier observability model behind a pluggable trace port. |
| ADR-0007 | Do not introduce a universal database or ontology | Accepted | Share IDs, envelopes and schemas; each product keeps its own authoritative state. |
| ADR 0015 | Keep ShareCLI standalone | Accepted | Do not absorb ShareCLI; integrate it as a privileged runtime client via adapters. |
| ADR 0016 | Preserve AGSLAG, AgilePlus, thegent, Tracera and ledger authority | Accepted | AGSLAG=worth, AgilePlus=commitments, thegent=dispatch, Fabric=execution, Tracera=evidence, SessionLedger=history; exchange IDs/events only. |
| ADR 0017 | Agents may publish and request attention but not steal focus | Accepted | Capability-scoped publication/attention APIs; human focus takeover requires explicit policy or action. |
| ADR 0020 | Use Phenotype Fabric as a working name only | Accepted | Provisional name; no irreversible namespace or legal claims until boundary validation. |
| ADR-005 | AgilePlus Governance Boundary | Accepted | Fixes what AgilePlus owns and does not own (per-product governance boundary). |

Also present but not read here: `0030-route-failover-model.md` (failover accepted, impl landed 2026-09-06 in `crates/fabric-graph/src/failover.rs`), `0033-fabric-daemon-architecture.md`, `0035-gui-suite-architecture.md`, `ADR-012` Plugin Architecture for AgilePlus (Proposed), `ADR-016` (Accepted), and the `docs/adrs/ADR-ECO-001..023` ecosystem series.

## Knowledge base

**Corpus.** 10,532 tracked markdown files / 716,333 lines spread across **149** top-level directories. `docs/` (2,581 files, 105 subdirs) is the intended canonical corpus, but `crates/` (3,518 — per-crate AGENTS/CLAUDE/SPEC boilerplate), `audits/` (1,290), `absorption/` (1,102) and `docs/specs/pheno-specs/` (393, a nested vendored repo with its own LICENSE/CODEOWNERS/CHARTER) compete with it. Classification: ~400 canonical, ~1,600 session/dated, ~1,102 absorbed/vendored, ~2,500 boilerplate, 1,002 temporal (SUMMARY/STATUS/FINAL/PHASE). Three archive generations hold 329 files; three separate archive trees plus `absorption/` and `docs/absorbed-from*` duplicate each other's content with 58–95% basename overlap between supposedly distinct trees. 52 session dirs under `docs/sessions/` span 2026-02-26 → 2026-11-07 with two coexisting name conventions.

**Read first, in order.** 1. `README.md:3-6` (positioning) then `PRD.md:3` (the competing claim). 2. `docs/atlas/` — `PRD.md`, `HLD.md`, `LLD.md`, `ALD.md`, `DOMAIN_MODEL.md`, `qa/` (assurance contract, metrics, negative controls), `products/`, `codebase/FILES.md` (22,660-line generated index). 3. `docs/adr/` for decisions. 4. `docs/boundary/` (166 per-product boundary files) and `docs/intent/` (139). 5. `docs/ABSORPTION_INDEX.md` + `docs/absorbed-from/*` (33 per-project absorption records). 6. `docs/sessions/index.md`. 7. `docs/dossiers/HANDOFF-PHENOSHARED.md` (identity, absorption table, last verified build 2026-09-16).

**Do not read as canonical.** `docs/phenotype-docset-v1.1/` (146 files, near-copy of `docs/atlas/`), `docs/adrs/` (25-file second ADR store), `docs/intent/` (near-copy of `docs/boundary/`), `docs/worklogs/` (byte-duplicates of `crates/hexa-kit/docs/worklogs/`), `docs/specs/pheno-specs/` (vendored nested repo), `archives/` + `_archived/` + `.archive/` (three archive generations), the 128 loose root-level markdown files, and `docs/reference/` whose top entries are dated status docs.

