## Delivery surfaces

| Surface | Form | Evidence |
|---|---|---|
| Rust library crates | 283 unique declared workspace paths; 372 `crates/` dirs; 26 nested workspaces | `Cargo.toml`; `ls crates` |
| Rust binaries | 154 `[[bin]]` declarations across tracked manifests; 85 crates under `crates/` with a top-level `src/main.rs` | `git ls-files` counts; `README.md:17` |
| CLI | binary `substrate` — `dispatch`, `plan`, `argv`, `cloud-dispatch`, `serve` | `README.md:70` |
| HTTP / A2A | `substrate-http` (REST dispatch/plan/route + A2A mailbox); `dispatch-bridge` (HTTP+SSE+Unix socket) | `README.md:71,115-117` |
| MCP tools | `driver-mcp` (stdio JSON-RPC bridging EnginePort/RoutingPort/ToolPort); `phenotype-mcp` | `README.md:72,118` |
| SDKs | `substrate` facade (features `app`/`spec`/`a2a`), `substrate-core`, `substrate-app`, `engine-spec`, `arch-test` | `README.md:59-70` |
| TUIs / GUI / tray | `substrate-tui`, `fabric-tui`, `orchestrator`, `fabric-gui` (Tauri v2), `fabric-tray` | `README.md:113,157-161` |
| Web | `fabric-web` (Leptos WASM SPA) | `README.md:161` |
| Services / ports | `fabric-daemon` :9400 · phinbox :7117 · focalpoint-mcp :8473 · brokerd :8787 · gateway-tools :8081; `phenotype-daemon` 9456-vs-8953 conflict | crate port bindings and service entry points |
| CI as a product | 84 reusable workflows + 5 composite actions, consumed as `KooshaPari/PhenoShared/.github/workflows/ci.yml@main` | `README.md:23-24,405-409` |

## Risk register

| Risk | Evidence | Impact | Mitigation |
|---|---|---|---|
| R-01 stale README metrics (76 members / 329 manifests vs 283 / 372) | `README.md:16-22` vs `Cargo.toml` + `ls crates` | High — repo sizing off ~3.8x | regenerate "At a glance" from `cargo metadata` |
| R-02 no canonical crate inventory (3 incompatible groupings) | `README.md:194-215` vs the `members` list | High — "how many crates" is unanswerable | publish one generated inventory |
| R-03 build health unverified since 2026-09-16 (PASS, 47 warnings) | `docs/dossiers/HANDOFF-PHENOSHARED.md` | High — no current build truth | CI the root workspace; publish a green baseline |
| R-04 ADR numbering collides across 3 trees (4x `0001`, 2x ECO-001) | `docs/adr/` 82, `docs/adrs/` 25, root `adrs/` 10 | High — breaks ledger traceability | renumber into one tree with a status field |
| R-05 root docs carry other products' identity; 128 root `.md` | `README.md:358-375` | High — agent-facing poisoning vector | replace with owner-repo pointers |
| R-06 three conflicting "what is this repo" statements | `README.md:3` vs `PRD.md:3` vs HANDOFF | Med-High — supported dependency model unclear | adopt one canonical statement |
| R-07 CI entry point broken (`Taskfile.yml` `ci` -> missing `scripts/ci-local.sh`) | `README.md:379-381` | Med — broken default path | repair the taskfile or delete it |
| R-08 `[workspace.package] repository` points at a stale origin | `README.md:382-383` | Med — wrong crate homepage | update to `KooshaPari/PhenoShared` |
| R-09 platform code excluded from the workspace (`fabric-gui/src-tauri`, fuzz, `forge_daemon`) | `Cargo.toml` `exclude` | Med — GUI shell escapes the CI gate | add targeted CI jobs |
| R-10 absorption/decomposition tension (5 repos copied pending confirmation; ADR-ECO-014 argues against it) | `docs/ABSORPTION_INDEX.md`; `docs/adrs/ADR-ECO-014` | Med — unclear ownership + disk cost | decide archive-vs-absorb per repo |

## Strategic assessment
**Strengths.** The substrate spine enforces its own boundaries via `arch-test`; a genuinely org-wide reusable surface (crates + 84 workflows + handbook + `llms.txt`); a dated verified-good handoff snapshot; an outcome-based roadmap with explicit Proof conditions; a dense ADR + registry record (82+25 ADRs, 178 manifests).
**Liabilities.** No current build truth; three incompatible inventories; colliding ADRs; wrong-project root docs; a broken CI entry point; stale crate metadata; in-repo absorbed sprawl.
**5 highest-leverage next actions.**
1. Run `cargo check --workspace` + `cargo metadata --no-deps` at HEAD and regenerate the README "At a glance" from that output — closes R-01, R-02, R-03 at once.
2. Collapse the three ADR trees into one with unique IDs and a machine-readable `Status:` (also closes the 35/82 no-status gap).
3. Replace root `AGENTS.md`/`PRD.md`/`ARCHITECTURE.md` with owner-repo pointers; quarantine the other 128 root `.md` files.
4. Fix the CI entry point (repair or delete the `ci` task) and add a root build job that also covers the previously excluded platform crates.
5. Close the absorption loop: per-repo archive-vs-keep decision, `PROVENANCE.md` -> `ARCHIVED`, and trim `absorption/PhenoMLX-temp` (~646 MB).

## Honest unknowns
- Current build/test status — no build was run for this dossier; last evidence is PASS on 2026-09-16 with 47 warnings. **UNKNOWN**.
- True resolvable package count — 283 declared member paths were listed, but `cargo metadata --no-deps` was never run, so the resolved-package count is **UNKNOWN**.
- Real cross-family dependency direction (`cargo tree` between spine / Fabric / absorbed families). **UNKNOWN**.
- Contents of `apps/`, `platform/`, `servers/`, `serving/`, `agile-plus-*`, `teamcomm-*` — only directory names were listed. **UNKNOWN**. (`focus-*`, `connector-*` and `sharecli*` were subsequently inventoried: 43/9/12 crates respectively, with LOC, entrypoints and provenance measured — see the per-family entries above.)
- Schema/semantics of the 178 `projects/*.json` manifests. **UNKNOWN**.
- CI health of the 84 reusable workflows (no `gh` inspection performed). **UNKNOWN**.
- Whether the `governance/` happy-path scripts are wired into pre-commit or CI. **UNKNOWN**.
- Whether `architecture/openapi.yaml` matches the `substrate-http` contract. **UNKNOWN**.

## Evidence basis

| Evidence | Coverage |
|---|---|
| PhenoShared working tree, read-only | workspace manifests, `README.md`, `PRD.md`, `docs/`, ADR directories, `.github/workflows/`; no builds, no writes |
| `git log` / `git rev-parse` / `gh repo view`, read-only | commit titles and dates, branch SHAs, visibility, `createdAt`, `pushedAt` |
| `git ls-files` | all file and language counts quoted in this dossier |

## Corrections applied after re-measurement
Earlier drafts of this dossier carried several inflated or unreconciled counts. Each was re-measured
directly against the working tree; the corrected value is what appears in the body.

| Claim | Earlier value | Corrected value | How measured |
|---|---|---|---|
| Workspace members | 287, later 239 | **283 unique crate paths** | root `Cargo.toml` `members` holds 287 quoted strings: 1 is a comment (`"Do not register as a workspace member"`) and 3 are duplicates (`focus-ci-watcher`, `focus-icon-gen`, `focus-time`), leaving 283 distinct paths, all present on disk. Neither 287 nor 239 reproduces. |
| Tracked markdown files | 10,517 | **10,532** | `git ls-files '*.md'` |
| `docs/` contents | "11,721 markdown" | **11,721 files, of which 2,494 are `.md`** | `git ls-files docs`; `git ls-files 'docs/**/*.md'` |
| Python files | 4,341 | **5,709** | `git ls-files '*.py'` |
| TypeScript / TSX / JS files | 467 / 119 / 157 | **2,884 / 2,327 / 375** | `git ls-files` per extension |
| Rust files (not previously stated) | — | **7,209** | `git ls-files '*.rs'` |

Not re-measured and therefore still **UNKNOWN**: build health, test counts, coverage percentages,
ADR counts under `docs/adr` (directory-scoped counts differ by whether subdirectories and index files
are included), and every runtime port that was read from source rather than observed on a live socket.
