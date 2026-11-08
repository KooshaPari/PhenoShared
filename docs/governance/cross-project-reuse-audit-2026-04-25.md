# Cross-Project Reuse Audit — 2026-04-25

**Scope:** Phenotype-org shared crate inventory, adoption rates, and next extraction targets.
**Method:** GitHub API (`gh api`, `gh search code`) — no clones, no edits.
**Protocol:** Phenotype Org Cross-Project Reuse Protocol (see `~/.claude/CLAUDE.md`).

---

## 1. Current Shared Crate Inventory

### `phenotype-shared` (<REDACTED>/phenotype-shared, Cargo workspace, 12 crates)

| Crate | Status |
|-------|--------|
| `ffi_utils` | published |
| `phenotype-application` | published |
| `phenotype-cache-adapter` | published (also in infrakit — drift risk) |
| `phenotype-domain` | published |
| `phenotype-event-sourcing` | published (also in infrakit — drift risk) |
| `phenotype-http-adapter` | published |
| `phenotype-nanovms-client` | published |
| `phenotype-policy-engine` | published |
| `phenotype-port-interfaces` | published |
| `phenotype-postgres-adapter` | published |
| `phenotype-redis-adapter` | published |
| `phenotype-state-machine` | published (also in infrakit — drift risk) |

### `phenotype-infrakit` (<REDACTED>/phenotype-infrakit, Cargo workspace, 15 crates)

15 crates including the Phase 1 LOC-reduction outputs: `phenotype-error-core`, `phenotype-errors`, `phenotype-config-core`, `phenotype-health`, plus duplicates of cache/event-sourcing/state-machine listed above.

### `phenoShared` (<REDACTED>/phenoShared)
Hosts a parallel `phenotype-state-machine` source — third copy of the same logical crate.

### Go shared
`phenotype-go-kit`, `phenotype-go-auth` referenced by cliproxyapi-plusplus via local `replace` paths that don't resolve in CI (per memory `cliproxyapi patterns`).

---

## 2. Adoption Rate

**Methodology:** `gh search code` for `<crate-name>` across `<REDACTED>` org, then count matches that are actual `Cargo.toml [dependencies]` lines vs. docs/audits/specs/READMEs.

| Shared Crate | Mentions | Real Cargo Consumers | Adoption |
|--------------|----------|---------------------|----------|
| phenotype-error-core | ~20 | 0 outside infrakit/PhenoProc | **none** |
| phenotype-config-core | ~20 | 0 outside infrakit/PhenoProc | **none** |
| phenotype-health | ~20 | 0 outside infrakit/PhenoProc/PhenoObservability | **near-zero** |
| phenotype-state-machine | ~20 | 0 outside infrakit/phenoShared/PhenoProc/ResilienceKit (each redefines locally) | **fragmented** |
| phenotype-event-sourcing | (similar pattern) | redefined in 2+ workspaces | **fragmented** |
| phenotype-cache-adapter | (similar pattern) | redefined in 2+ workspaces | **fragmented** |

**Verified by direct fetch** of `Cargo.toml` from FocalPoint, Tracely, AgilePlus, thegent: **zero** `phenotype-*` entries. Phase 1 LOC reduction shipped (PR #87), but downstream migration never followed. The crates are publishable but unconsumed.

**Headline finding:** the shared crate effort is supply-side complete and demand-side empty. We have three parallel canonical homes (`phenotype-shared`, `phenotype-infrakit`, `phenoShared`) for overlapping crates and zero real consumers outside the workspaces themselves.

---

## 3. Top-5 Extraction / Consolidation Candidates

Ranked by impact-per-risk. LOC estimates derived from PR diffs (where known) and reasoned extrapolation from typical adapter scope.

### #1 — Consolidate the three state-machine / event-sourcing / cache-adapter copies
- **Source repos:** phenotype-shared, phenotype-infrakit, phenoShared, ResilienceKit
- **Target:** single canonical crate in `phenotype-shared` (drop the duplicates in infrakit and phenoShared)
- **Estimated LOC saved:** ~2,000–3,000 (3× redundant implementations of the same logical crates)
- **Blast radius:** medium — touches 4 workspaces, but no external consumers depend on either copy
- **Risk:** low (no real adopters means no breakage). Pure pre-adoption hygiene.

### #2 — `urlguard` outbound-URL validator (Go) → `phenotype-go-net`
- **Source:** `cliproxyapi-plusplus/pkg/llmproxy/util/urlguard` (PR #955, +223/-17, just landed)
- **Target:** new shared package `phenotype-go-net/urlguard` under phenotype-go-kit
- **Estimated LOC saved:** 200–600 across consumers (every Go service doing outbound HTTP needs SSRF defense)
- **Blast radius:** low — Go repos with outbound HTTP: AgentMCP, agentapi-plusplus, pheno-cli, cliproxyapi-plusplus, thegent
- **Risk:** low — small surface, well-tested in PR #955

### #3 — `pathsafe` traversal guard (Go) → `phenotype-go-fs`
- **Source:** `cliproxyapi-plusplus/internal/pathsafe` (PR #954, +182/-2)
- **Target:** new shared package `phenotype-go-fs/pathsafe` under phenotype-go-kit
- **Estimated LOC saved:** 150–400 across consumers (any service handling user paths)
- **Blast radius:** low — same Go consumer set as #2
- **Risk:** low — small, tested

### #4 — Tracing/OTel bootstrap → `phenotype-telemetry-bootstrap`
- **Source:** duplicated across pheno (`phenotype-logging/otel.rs`), AgilePlus (`agileplus-telemetry`), Tracely (`tracely-core/tracing.rs`), FocalPoint (`focus-observability`), heliosCLI (`codex-rs/otel`), PhenoObservability (`tracely-core`), thegent (`harness-native/dispatcher`)
- **Target:** new crate (or absorb into existing `phenotype-shared`); single `init_tracing(service_name, otlp_endpoint)` API
- **Estimated LOC saved:** 600–1,200 (7+ near-identical bootstrap files)
- **Blast radius:** medium — 7 repos, but the call site is one function per binary
- **Risk:** medium — OTel feature gating + tracing-subscriber version pinning has historically caused conflicts; needs feature flags for axum/tonic layers

### #5 — `tailscale-keygen` + `oci-post-acquire` → `phenotype-cloud-acquire`
- **Source:** phenotype-infra (tailscale-keygen, oci-post-acquire chain — surfaced 2026-04-24 compute mesh work)
- **Target:** new crate `phenotype-cloud-acquire` covering tailnet enrollment + cloud-VM post-provision config
- **Estimated LOC saved:** 300–800 (currently bespoke; would prevent the next provider acquisition from re-rolling)
- **Blast radius:** small (only phenotype-infra today, but compute mesh expansion is in flight: OCI + CF DNS pending per memory `reference_compute_mesh_state`)
- **Risk:** medium — generalizing prematurely; only 1 consumer today. Defer until 2nd cloud (OCI) actually integrates.

---

## 4. Recommended Migration Order

Low-risk first, then volume:

1. **Hygiene pass (Week 0):** dedupe state-machine / event-sourcing / cache-adapter triplicates → keep `phenotype-shared` canonical, delete from `phenotype-infrakit` and `phenoShared`. Update workspace `members`, no consumers to break. (#1)
2. **Quick wins (Week 1):** extract `urlguard` and `pathsafe` to `phenotype-go-kit` → migrate the 4 Go consumers in one PR each. (#2, #3)
3. **High-value migration (Weeks 2–3):** OTel bootstrap consolidation. Author the crate; migrate Tracely + PhenoObservability first (most aligned), then AgilePlus, FocalPoint, heliosCLI, pheno, thegent. (#4)
4. **Forced adoption sweep (Weeks 3–4):** for each Phase 1 crate (`phenotype-error-core`, `phenotype-config-core`, `phenotype-health`), pick 2 consumer repos and land migration PRs. Without forced adoption these will stay zero-consumer indefinitely.
5. **Defer (Week 5+):** `phenotype-cloud-acquire` (#5) — wait for OCI integration to give a 2nd consumer before extracting.

---

## 5. Cross-Cutting Findings

- **Three-canonical-home problem:** state-machine/event-sourcing/cache-adapter exist in `phenotype-shared`, `phenotype-infrakit`, and `phenoShared`. Pick one and delete the others before adoption is even possible.
- **Phase 1 supply/demand gap:** `phenotype-error-core` / `-config-core` / `-health` shipped 2026-03-29 (PR #87) but no consumer Cargo.toml depends on them. The "consolidation" was definitional only.
- **Doc-as-adoption antipattern:** most search hits for shared crates are in `docs/adoption/`, `kitty-specs/`, audits, and worklogs — *talking* about adoption, not adopting. Future audits should grep `[dependencies]` blocks specifically.
- **Go shared libs in worse shape:** `phenotype-go-kit` and `phenotype-go-auth` are referenced via local `replace` paths that fail in CI (memory `cliproxyapi patterns`). Publish to a Go module proxy or vendor before treating as shared.

---

## 6. Output Constraints Met

- API-only, no clones.
- ~150 lines (under 200-line cap).
- Cap and time budget respected.
