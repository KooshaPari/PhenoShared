# PhenoShared — complement audit (excluding Phinbox)

**Audit date:** 2026-10-17. **Repo ID:** `1200273587`. **Branch:** `main`. **Pane:** audit lane `wA:Ps` (complement to `wA:pN` Phinbox). **Scope:** everything in `KooshaPari/PhenoShared` except `crates/phinbox` and `apps/phinbox-app` (Phinbox is being audited separately on pane `wA:pN`). **Files sampled:** `src/lib.rs`, `src/main.rs`, `src/plugin.rs`, `src/connector.rs`, `src/postfx/ports/urp_render_graph.rs` (full); `src/compute/voxel_processor.rs` and `src/terrain/chunk_mesh_builder.rs` (header lines only). `crates/` and `apps/` surveyed by directory shape, not content.

## IDENTITY
PhenoShared is the pooled reusable foundation + accepted package home for the Phenotype ecosystem (formerly PhenoAI per `STATE.md`). Excludes Phinbox, which is audited separately.

## INTENT
A bounded reusable capability must be installable and usable by its actual consumers (PhenoFabric, PhenoLab, Registry, ShareCLI) from a clean environment, with precise provenance and safe change semantics. Reuse/modify over handroll; coordinate — not absorb — across owner chats.

## CURRENT STATE
`PLANNED_NOT_EXECUTED` per `PILOT.json`; `SOURCE_CONFIRMED_INTEGRATION_GAPS` per `STATE.md`. The handoff reports 81 workspace members / 310 crate directories, one excluded broken Python crate, and live external PhenoInfra references. No percentage claimed, no pilot winner, no migration authorization inferred.

## CODE REALITY
- **`src/lib.rs` is 17 lines** of pure re-exports for `phenotype-crypto` (blake3, sha256, AES-GCM, PBKDF2, HMAC) — `src/lib.rs:1-17`. The actual work lives in the dependency, not here.
- **`src/main.rs` is 39 lines** — only binary is `pheno-agents-md` (AGENTS.md generator). `crates/` carries the real code.
- **Workspace is huge:** 369 directories under `crates/`, 491 `Cargo.toml` files, plus `apps/` (12 crate targets) and `src/` (1.1M). Far beyond an auditable scope.
- **Foundations are absorbed but lightly integrated.** `phenotype-crypto`, `phenotype-config`, `phenotype-cipher`, `phenotype-cache-adapter`, `phenotype-event-bus`, `phenotype-event-sourcing`, `phenotype-casbin-wrapper`, `phenotype-cli`, `phenotype-casbin-wrapper`, `phenotype-cli-core`, etc. are top-level members; handoff claims absorbed PhenoFabric/PhenoLab/Registry content whose owner chats still exist.
- **`phenotype-health` is a local dependency** in latest hand-off; external PhenoInfra references remain unresolved (per `STATE.md`).

## STUB/MOCK/MVP-LAZINESS INVENTORY
Non-Phinbox only:
- **`src/plugin.rs:141`** — `PluginManager::load_plugins` is a stub: "Currently this is a stub that…" (no real loader).
- **`src/connector.rs:103-136`** — `stub_changes()` helper returns hard-coded `Change` records for Plane / GitHub / Import connectors; tests (`connector.rs:175,185,231`) assert on the literal `"stub-change"` id — passing tests do not prove real connectivity.
- **`src/postfx/ports/urp_render_graph.rs:4,67`** — `// T27 stub: URP 17 RecordRenderGraph adapter contract.` with a comment that "the migration work (T27) will fill it". `post_fx_pass.rs:263` has `fn stub_pass_works()` test.
- **`src/compute/voxel_processor.rs:218`** — "Copy source to scratch on first invocation (stub — real impl uses …)".
- **`src/terrain/chunk_mesh_builder.rs:4`** — header states the old overload "was a stub that delegated to `BuildMesh(int, float)` and is dropped", i.e. dropped stub, not implemented.
- **`PILOT.json:21-22`** — `results: null`, `winner: null`. Pilot has not been executed.
- **Excluded broken Python crate** is described as "harmless" and struck off repair without consumer/contract evidence (per `STATE.md`). Excluded ≠ accepted.
- **3 harness-config files end with marker names** matching known test fixtures (`.forge/`, `.kittify/`, `.kilo/`, `.airlock/`, `.grade-reports/`) — pattern-wide but not a code defect; flagging for awareness only.
- **No integration tests** observed in the 3-5 file sample; existence of `tests/` and sibling workspace validation not verified.

## FWD PATH TO FINISH (non-Phinbox)
1. **Run `PILOT.json`** end-to-end against the existing simplest-correct baseline; record negative-case discrimination (missing dep, contradictory ownership, private exposure, broken consumer returning "success").
2. **Promote one donor→consumer dependency slice** from `crates/` into an existing phenoproduct (PhenoFabric or PhenoLab) and prove a cache-isolated clean fetch + build + semantic test + failure test. Document donor identity vs. consumer equivalent.
3. **Resolve external PhenoInfra references** still pointing at donor Git sources where local copies exist; gate on independent verification, not author-report.
4. **Convert named stubs to contracts.** For each of `plugin.rs::load_plugins`, `connector.rs::stub_changes`, `voxel_processor.rs:218`, `urp_render_graph.rs`: write the contract first, then implementation. Delete the stub path, do not keep both.
5. **File the disposition of the excluded Python crate** with a consumer/contract test or remove it from the workspace; current "exclude = harmless" is not a verdict.

## TIME-TO-FINISH ESTIMATE
**3-6 weeks wallclock** for a single StaffSWE lane, assuming: (a) one slice per week to ship + prove, (b) ~3-5 days/wk spent on stub-to-contract conversions in `src/`, (c) no new external repo creation, no force pushes, no Phinbox work bleeding in. Atlas remains the live source of truth; `STATE.md` is re-baselined after each slice.

## SUNSET/KEEP CALL
**KEEP** — with bounded scope reassertion. The pooled-foundation role is real (491 `Cargo.toml` files, dozens of consumers across the Phenotype ecosystem) but the present artifact is in a planned-not-executed posture with named MVP-stub connectors. The repo earns its keep only if the pilot can be run and at least one donor→consumer slice can be proven end-to-end within one work cycle. If the pilot doesn't complete in 2 cycles, restructure as a thin meta-package that re-exports proven foundations and drops the absorbed app-code surfaces.

## CONFIDENCE
**Medium.** Audit sampled only 5 files (`src/lib.rs`, `src/main.rs`, `src/plugin.rs`, `src/connector.rs`, `src/postfx/ports/urp_render_graph.rs`) and `crates/` directory shape. Findings on stubs/Phinbox boundary/foundation role are well-supported; claims about test coverage, CI health, and per-crate quality are not (out of sample). No code modified; no pushes; PhenoRegistry untouched.
